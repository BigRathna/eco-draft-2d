"""
NLP/LLM service for parsing natural language engineering requests using Google Gemini API.
"""
import os
import requests
import re
from typing import Dict, Any
import json

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

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
    "PARAMETERS to extract/modify:\n"
    "- Dimensions: width, height, length, diameter, thickness\n"
    "- Features: hole_diameter, hole_spacing, corner_radius\n"
    "- Material: steel, aluminum, brass, titanium\n"
    "- Shape: triangle, L, T, rectangle, circle\n"
    "\n\n"
    "Reply ONLY with a valid JSON object:\n"
    "{\n"
    "  \"part_type\": \"[keep_same_for_modifications]\",\n"
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


def parse_engineering_request(user_message: str) -> Dict[str, Any]:
    """Call Gemini API to parse user message into structured parameters using structured output or fallback to Markdown code block parsing."""
    print(f"🤖 NLP: Processing user message: '{user_message}'")
    
    # Import settings here to ensure .env is loaded
    from app.core.config import settings
    
    if not settings.gemini_api_key:
        raise RuntimeError(
            "GEMINI_API_KEY environment variable not set. See https://ai.google.dev/gemini-api/docs/get-started-cloud for instructions.")

    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": SYSTEM_PROMPT + "\n" + user_message}
                ]
            }
        ],
        "tools": [
            {
                "function_declarations": [
                    {
                        "name": "engineering_part",
                        "description": "Extracted engineering part request",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "part_type": {"type": "string"},
                                "parameters": {"type": "object"},
                                "export_formats": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                }
                            },
                            "required": ["part_type", "parameters"]
                        }
                    }
                ]
            }
        ]
    }
    url = f"{GEMINI_API_URL}?key={settings.gemini_api_key}"
    response = requests.post(url, headers=headers, json=data, timeout=20)
    response.raise_for_status()
    result = response.json()
    print("Gemini API response:", result)
    # Try to extract structured function call result
    for candidate in result.get("candidates", []):
        function_call = candidate.get("content", {}).get("functionCall")
        if function_call:
            return function_call.get("args", {})
        # Fallback: parse JSON from Markdown code block in parts
        parts = candidate.get("content", {}).get("parts", [])
        for part in parts:
            text = part.get("text", "")
            # Remove code block markers and extra text
            if text.startswith("```json"):
                text = text.replace("```json", "").replace("```", "").strip()
            elif text.startswith("```"):
                text = text.replace("```", "").strip()
            # Try to find the first JSON object in the text
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1 and end > start:
                json_str = text[start:end+1]
                try:
                    return json.loads(json_str)
                except Exception:
                    continue
            # Or just try to parse any JSON in the text
            try:
                return json.loads(text)
            except Exception:
                continue
    raise ValueError("No structured output or valid JSON returned by Gemini.")


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
