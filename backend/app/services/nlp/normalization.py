from typing import Dict, Any, Optional, Union
import re
from app.schemas.cad import CadAction, PartType, AnyPartParameters, CadIntent

# Alias mapping for messy LLM keys
ALIAS_MAP = {
    "dia": "diameter",
    "hole_dia": "hole_diameter",
    "thk": "thickness",
    "len": "width", # Ambiguous, but often width in 2D
    "outer_dia": "outer_diameter",
    "inner_dia": "inner_diameter",
    "rad": "radius",
    "fillet": "corner_radius"
}

# Unit conversion factors to mm
UNIT_FACTORS = {
    "inch": 25.4,
    "in": 25.4,
    "ft": 304.8,
    "foot": 304.8,
    "cm": 10.0,
    "m": 1000.0,
    "meter": 1000.0,
    "mm": 1.0
}

def normalize_value(val: Any) -> float:
    """Normalizes a value string (e.g., '10 inch') to mm float."""
    if isinstance(val, (int, float)):
        return float(val)
    
    if not isinstance(val, str):
        return 0.0
    
    # Try to extract number and unit
    match = re.match(r"([\d.]+)\s*([a-zA-Z]*)", val.strip().lower())
    if match:
        num = float(match.group(1))
        unit = match.group(2)
        if unit in UNIT_FACTORS:
            return num * UNIT_FACTORS[unit]
        return num
    
    try:
        return float(val)
    except ValueError:
        return 0.0

def normalize_parameters(raw_params: Dict[str, Any]) -> Dict[str, Any]:
    """Normalizes keys and values from raw LLM output."""
    normalized = {}
    
    for key, val in raw_params.items():
        # 1. Normalize Key
        canonical_key = ALIAS_MAP.get(key.lower(), key.lower())
        
        # 2. Normalize Value (if it's a measurement)
        # We assume keys containing 'width', 'height', 'diameter', 'radius', 'thickness', 'spacing', 'length', 'distance' are measurements
        measurement_keywords = ['width', 'height', 'diameter', 'radius', 'thickness', 'spacing', 'length', 'distance', 'diameter']
        if any(kw in canonical_key for kw in measurement_keywords):
            normalized[canonical_key] = normalize_value(val)
        else:
            normalized[canonical_key] = val
            
    return normalized

def build_validated_intent(raw_intent: Dict[str, Any]) -> CadIntent:
    """
    Takes raw dict from LLM and produces a validated CadIntent.
    Separates raw data from validated parameters.
    """
    # 1. Extract basic fields
    action_str = raw_intent.get("action", "create").lower()
    part_type_str = raw_intent.get("part_type", "plate").lower()
    raw_params = raw_intent.get("parameters", {})
    
    # 2. Normalize parameters
    norm_params = normalize_parameters(raw_params)
    norm_params["type"] = part_type_str # Ensure discriminator is set
    
    # 3. Build Intent object
    intent = CadIntent(
        action=CadAction(action_str),
        target_id=raw_intent.get("target_id"),
        parameters=raw_params, # Keep raw for logging
        rationale=raw_intent.get("rationale")
    )
    
    # 4. Attempt validation
    from pydantic import ValidationError
    from app.schemas.cad import (
        PlateParameters, GussetParameters, BracketParameters, 
        WasherParameters, FlangeParameters
    )
    
    # Mapping for validation
    param_models = {
        PartType.PLATE: PlateParameters,
        PartType.GUSSET: GussetParameters,
        PartType.BRACKET: BracketParameters,
        PartType.L_BRACKET: BracketParameters,
        PartType.T_BRACKET: BracketParameters,
        PartType.ANGLE: BracketParameters,
        PartType.WASHER: WasherParameters,
        PartType.SPACER: WasherParameters,
        PartType.FLANGE: FlangeParameters
    }
    
    model_cls = param_models.get(PartType(part_type_str))
    if model_cls:
        try:
            intent.validated_parameters = model_cls(**norm_params)
        except ValidationError as e:
            print(f"Validation failed for {part_type_str}: {e}")
            # Fallback or partial recovery logic could go here
            
    return intent
