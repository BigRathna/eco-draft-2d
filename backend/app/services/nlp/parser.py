"""
NLP/LLM service for parsing natural language engineering requests using Google Gemini API.
"""
import os
import requests
import re
import time
import threading
from typing import Dict, Any, List, Optional
import json
from app.core.config import settings
from app.schemas.cad import CadIntent, CadParameters
from app.services.nlp.prompt_builder import create_prompt_builder
from app.services.nlp.adapters import get_adapter

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

# ---------------------------------------------------------------------------
# Rate limiter – stays within the free-tier 15 RPM limit.
# Enforces a 5-second minimum gap between consecutive API calls and
# retries up to 3 times with exponential backoff on 429 responses.
# ---------------------------------------------------------------------------
_rate_lock = threading.Lock()
_last_call_time: float = 0.0
_MIN_INTERVAL_SECONDS = 5.0   # 12 RPM max (leaving headroom under 15 RPM)
_MAX_RETRIES = 3
_BASE_BACKOFF_SECONDS = 10.0  # wait 10s, 20s, 40s on successive 429s


def _rate_limit() -> None:
    """Block until it is safe to send the next Gemini API request."""
    global _last_call_time
    with _rate_lock:
        now = time.monotonic()
        wait = _MIN_INTERVAL_SECONDS - (now - _last_call_time)
        if wait > 0:
            print(f"⏳ NLP: Rate limiting – waiting {wait:.1f}s before next API call")
            time.sleep(wait)
        _last_call_time = time.monotonic()


def _call_gemini(system_prompt: str, user_message: str) -> Dict[str, Any]:
    if not getattr(settings, "gemini_api_key", None):
        raise RuntimeError("GEMINI_API_KEY environment variable not set.")
    
    headers = {"Content-Type": "application/json"}
    # Gemini tool use works best with the system prompt followed by user message
    combined_content = system_prompt + "\n\n" + user_message
    
    data = {
        "contents": [{"role": "user", "parts": [{"text": combined_content}]}],
        "tools": [{"function_declarations": [{
            "name": "engineering_part",
            "description": "Extracted engineering part request",
            "parameters": {
                "type": "object",
                "properties": {
                    "part_type": {"type": "string"},
                    "parameters": {"type": "object"},
                    "export_formats": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["part_type", "parameters"]
            }
        }]}]
    }
    url = f"{GEMINI_API_URL}?key={settings.gemini_api_key}"
    
    for attempt in range(_MAX_RETRIES + 1):
        _rate_limit()
        resp = requests.post(url, headers=headers, json=data, timeout=20)
        if resp.status_code != 429: break
        time.sleep(_BASE_BACKOFF_SECONDS * (2 ** attempt))
    
    resp.raise_for_status()
    result = resp.json()
    
    for candidate in result.get("candidates", []):
        parts = candidate.get("content", {}).get("parts", [])
        for part in parts:
            fn_call = part.get("function_call") or part.get("functionCall")
            if fn_call: return fn_call.get("args", {})
        
        for part in parts:
            text = part.get("text", "")
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "{" in text and "}" in text:
                text = text[text.find("{"):text.rfind("}")+1]
            try: return json.loads(text)
            except: pass
            
    raise ValueError("Gemini failed to return valid JSON.")

def _call_openai_compatible(payload: Any, provider: str) -> Dict[str, Any]:
    if provider == "ollama":
        url = "http://localhost:11434/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        model = "llama3"
    else:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {getattr(settings, 'openrouter_api_key', '')}",
            "HTTP-Referer": "http://localhost:3000",
            "Content-Type": "application/json"
        }
        model = "meta-llama/llama-3-8b-instruct"

    data = {
        "model": model,
        "messages": payload,
        "response_format": {"type": "json_object"}
    }
    
    resp = requests.post(url, headers=headers, json=data, timeout=30)
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    return json.loads(content)

def parse_engineering_request(user_message: str, provider: str = "gemini") -> CadIntent:
    from app.services.session.store import tracker
    print(f"🤖 NLP: Processing user message via {provider.upper()}: '{user_message}'")
    
    # Identify if this is a modification (check history)
    session_history = tracker.get_context_summary()
    is_mod = "[Current part:" in user_message or (session_history is not None and "Created" in session_history)
    
    # 1. Build the canonical bundle
    builder = create_prompt_builder(
        is_modification=is_mod,
        session_history=session_history
    )
    bundle = builder.build_bundle()
    
    # 2. Log version for future traceability
    print(f"🔍 NLP: Prompt Version Hash: {bundle.version_hash}")
    
    # 3. Transform via Adapter and Call Provider
    adapter = get_adapter(provider)
    payload = adapter.transform(bundle, user_message)
    
    if provider in ["ollama", "openrouter"]:
        parsed = _call_openai_compatible(payload, provider)
    else:
        parsed = _call_gemini(payload, user_message)
        
    # 4. Extract intent from provider result
    raw_intent = adapter.extract_intent(parsed)
    
    # 5. Normalize and Validate (Phase 2 hardening)
    from .normalization import build_validated_intent
    intent = build_validated_intent(raw_intent)
    
    return intent


def apply_parameter_defaults(parsed_data: Dict[str, Any]) -> Dict[str, Any]:
    """Apply sensible defaults to parsed parameters based on part type."""
    part_type = parsed_data.get("part_type", "plate").lower()
    parameters = parsed_data.get("parameters", {})
    
    print(f"🔧 NLP: Applying defaults for part_type='{part_type}'")
    
    # Get part-specific defaults
    defaults = _get_part_type_defaults(part_type)
    
    # Apply defaults for missing parameters
    for key, default_value in defaults.items():
        if key not in parameters:
            parameters[key] = default_value
            print(f"   ➕ Added default {key}={default_value}")
    
    # Ensure export_formats is set
    if "export_formats" not in parsed_data:
        parsed_data["export_formats"] = ["svg", "dxf"]
    
    parsed_data["parameters"] = parameters
    return parsed_data


def _get_part_type_defaults(part_type: str) -> Dict[str, Any]:
    """Get default parameters for any part type."""
    
    # Common defaults for all parts
    common_defaults = {
        "material": "steel",
        "thickness": 5.0,
    }
    
    # Part-specific defaults - matches UniversalPartGenerator
    part_specific_defaults = {
        "gusset": {
            "shape": "triangle",
            "width": 100.0,
            "height": 80.0,
            "corner_radius": 5.0,
        },
        "bracket": {
            "shape": "L",
            "width": 120.0,
            "height": 100.0,
            "leg_length": 80.0,
            "hole_diameter": 8.0,
            "hole_spacing": 40.0,
        },
        "angle": {
            "shape": "L", 
            "width": 100.0,
            "height": 100.0,
            "leg_width": 20.0,
            "thickness": 8.0,
        },
        "plate": {
            "shape": "rectangle",
            "length": 200.0,
            "width": 150.0,
            "hole_diameter": 8.0,
            "hole_spacing_x": 50.0,
            "hole_spacing_y": 50.0,
        },
        "washer": {
            "shape": "circle",
            "outer_diameter": 20.0,
            "inner_diameter": 8.0,
        },
        "flange": {
            "shape": "circle",
            "outer_diameter": 200.0,
            "inner_diameter": 100.0,
            "bolt_circle_diameter": 160.0,
            "bolt_holes": 8,
            "bolt_diameter": 12.0,
        },
        "base_plate": {
            "shape": "rectangle",
            "length": 200.0,
            "width": 150.0,
            "hole_pattern": "rectangular",
            "hole_diameter": 8.0,
            "hole_spacing_x": 50.0,
            "hole_spacing_y": 50.0,
            "edge_distance": 25.0,
        },
        "mounting_plate": {
            "shape": "rectangle",
            "width": 150.0,
            "height": 100.0,
            "hole_diameter": 6.0,
            "hole_spacing_x": 40.0,
            "hole_spacing_y": 40.0,
        },
        "cover_plate": {
            "shape": "rectangle",
            "width": 120.0,
            "height": 80.0,
            "thickness": 3.0,
        },
        "spacer": {
            "shape": "circle",
            "outer_diameter": 15.0,
            "inner_diameter": 6.0,
            "thickness": 2.0,
        },
        "rib": {
            "shape": "triangle",
            "width": 80.0,
            "height": 60.0,
            "thickness": 4.0,
        },
        "tab": {
            "shape": "rectangle",
            "width": 30.0,
            "height": 10.0,
            "thickness": 3.0,
        }
    }
    
    # Get specific defaults for this part type, or generic rectangle defaults
    specific = part_specific_defaults.get(part_type, {
        "shape": "rectangle",
        "width": 100.0,
        "height": 100.0,
    })
    
    # Combine common and specific defaults
    return {**common_defaults, **specific}

# Instructions:
# 1. Get a Google Gemini API key from https://ai.google.dev/gemini-api/docs/get-started-cloud
# 2. Set the environment variable GEMINI_API_KEY in your backend environment.
