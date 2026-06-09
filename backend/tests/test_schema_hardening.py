import pytest
import sys
import os
from pydantic import ValidationError

# Ensure backend/ is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.schemas.cad import (
    PlateParameters, WasherParameters, FlangeParameters, 
    PartType, CadAction, CadIntent
)
from app.services.nlp.normalization import normalize_value, normalize_parameters, build_validated_intent

def test_unit_normalization():
    assert normalize_value("10 inch") == 254.0
    assert normalize_value("5 cm") == 50.0
    assert normalize_value("1 meter") == 1000.0
    assert normalize_value("100") == 100.0
    assert normalize_value(50.5) == 50.5

def test_alias_normalization():
    raw = {"dia": 10, "thk": 5, "len": 100}
    norm = normalize_parameters(raw)
    assert norm["diameter"] == 10.0
    assert norm["thickness"] == 5.0
    assert norm["width"] == 100.0

def test_schema_validation_valid():
    # Valid plate
    p = PlateParameters(width=100, height=50, material="aluminum")
    assert p.width == 100
    assert p.type == PartType.PLATE
    
    # Valid washer
    w = WasherParameters(outer_diameter=20, inner_diameter=10)
    assert w.outer_diameter == 20

def test_schema_validation_invalid():
    # Invalid width
    with pytest.raises(ValidationError):
        PlateParameters(width=-10, height=50)
        
    # Invalid material
    # (Note: material validation currently allows but we can make it strict)
    
    # Invalid washer (inner >= outer)
    with pytest.raises(ValidationError):
        WasherParameters(outer_diameter=10, inner_diameter=15)

def test_build_validated_intent():
    raw_intent = {
        "action": "create",
        "part_type": "washer",
        "parameters": {
            "outer_dia": "1 inch",
            "inner_dia": "10 mm"
        }
    }
    intent = build_validated_intent(raw_intent)
    assert intent.action == CadAction.CREATE
    assert intent.validated_parameters is not None
    assert intent.validated_parameters.type == PartType.WASHER
    assert intent.validated_parameters.outer_diameter == 25.4
    assert intent.validated_parameters.inner_diameter == 10.0

def test_end_to_end_generator_compatibility():
    """Verifies that validated parameters work with the UniversalPartGenerator."""
    from app.services.cad.universal import UniversalPartGenerator
    
    raw_intent = {
        "action": "create",
        "part_type": "plate",
        "parameters": {"width": "10 cm", "height": "5 cm", "thk": 5}
    }
    intent = build_validated_intent(raw_intent)
    
    # Emulate the generator call
    # The generator currently takes a dict. We should convert our model to dict.
    params_dict = intent.validated_parameters.dict()
    generator = UniversalPartGenerator(intent.validated_parameters.type, params_dict)
    
    geo, data, schema = generator.generate_geometry()
    assert data["width"] == 100.0
    assert data["height"] == 50.0

if __name__ == "__main__":
    pytest.main([__file__])
