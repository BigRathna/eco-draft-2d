"""
NLP/LLM service for parsing natural language engineering requests using Google Gemini API.
"""
import os
import requests
import re
import time
import threading
from typing import Dict, Any
import json
from app.core.config import settings
from app.schemas.cad import CadIntent, CadParameters

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

SYSTEM_PROMPT = (
    "You are an expert mechanical engineering assistant. "
    "Given a user's request, extract the part type and parameters. "
    "\n\n"
    "IMPORTANT: If the message contains context in brackets like [Current part: ...], this is a MODIFICATION request. "
    "For modifications:\n"
    "1. Keep the same part_type from the context\n"
    "2. Start with the current parameters from context\n"
    "3. Apply the requested changes\n"
    "4. Return the complete updated parameters\n"
    "\n\n"
    "Examples of modification requests:\n"
    "- 'make it bigger' -> increase width and height by 20-50%\n"
    "- 'make the sides even' -> set width = height\n"
    "- 'increase thickness to 10mm' -> set thickness = 10\n"
    "- 'add more holes' -> increase number of holes or adjust hole pattern\n"
    "- 'make it smaller' -> decrease dimensions by 20-30%\n"
    "\n\n"
    "SUPPORTED PART TYPES:\n"
    "- gusset (triangular reinforcement)\n"
    "- bracket (L-shaped or T-shaped support)\n"
    "- plate (rectangular base)\n"
    "- washer, flange, spacer, etc.\n"
    "\n\n"
    "PARAMETERS to extract/modify (use exact standard names): \n"
    "- Dimensions: width, height, length, diameter, thickness\n"
    "- Features: hole_diameter, hole_spacing, corner_radius, hole_count, number_of_holes\n"
    "- Material: steel, aluminum, brass, titanium\n"
    "- Shape: triangle, L, T, rectangle, circle\n"
    "\n\n"
    "Reply ONLY with a valid JSON object matching exactly this schema:\n"
    "{\n"
    "  \"action\": \"create\", // Use 'checkout' if the user wants to revert to an older historical state\n"
    "  \"target_event_id\": \"\", // Fill this ONLY if action is 'checkout', using the 8-char ID from history\n"
    "  \"part_type\": \"[derive from context or history]\",\n"
    "  \"parameters\": {\n"
    "    \"material\": \"steel\",\n"
    "    \"thickness\": 5,\n"
    "    \"width\": 100,\n"
    "    \"height\": 100,\n"
    "    \"shape\": \"triangle\"\n"
    "  },\n"
    "  \"export_formats\": [\"svg\", \"dxf\"]\n"
    "}\n"
)


def _call_gemini(system_prompt: str, user_message: str) -> Dict[str, Any]:
    from app.core.config import settings
    if not getattr(settings, "gemini_api_key", None):
        raise RuntimeError("GEMINI_API_KEY environment variable not set.")
    
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{"role": "user", "parts": [{"text": system_prompt + "\n" + user_message}]}],
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

def _call_openai_compatible(system_prompt: str, user_message: str, provider: str) -> Dict[str, Any]:
    if provider == "ollama":
        url = "http://localhost:11434/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        model = "llama3"
    else:
        url = "https://openrouter.ai/api/v1/chat/completions"
        from app.core.config import settings
        headers = {
            "Authorization": f"Bearer {getattr(settings, 'openrouter_api_key', '')}",
            "HTTP-Referer": "http://localhost:3000",
            "Content-Type": "application/json"
        }
        model = "meta-llama/llama-3-8b-instruct"

    system_prompt += "\n\nCRITICAL: Return ONLY raw JSON matching this schema: {\"action\": string, \"target_event_id\": string, \"part_type\": string, \"parameters\": {}, \"export_formats\": []}"
    
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
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
    
    session_history = tracker.get_context_summary()
    dynamic_prompt = SYSTEM_PROMPT + f"\n\n==== ACTIVE SESSION GRAPH HISTORY ====\n{session_history if session_history else 'No history yet. This is the first action.'}\n======================================\n\nAnalyze the user message. If they ask to 'go back' or 'return' to an older design, extract the matching ID from the history, set action='checkout', and populate the parameters exactly as they were in that historical node!"
    
    if provider in ["ollama", "openrouter"]:
        parsed = _call_openai_compatible(dynamic_prompt, user_message, provider)
    else:
        parsed = _call_gemini(dynamic_prompt, user_message)
        
    if "action" not in parsed or parsed["action"] == "generate":
        parsed["action"] = "create"
        
    part_type = parsed.get("part_type", "plate").lower()
    parameters = parsed.get("parameters", {})
    action = parsed.get("action", "create")
    target_id = parsed.get("target_event_id")
    rationale = parsed.get("rationale")
    
    defaults = _get_part_type_defaults(part_type)
    for key, val in defaults.items():
        if key not in parameters:
            parameters[key] = val
            
    return CadIntent(
        action=action,
        target_id=target_id,
        parameters=CadParameters(type=part_type, values=parameters),
        rationale=rationale
    )


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
