import pytest
import sys
import os
from unittest.mock import patch

# Ensure backend/ is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.services.nlp.parser import parse_engineering_request
from app.services.cad.universal import UniversalPartGenerator
from app.schemas.cad import PartType, CadAction

# Representative prompts that mimics real user input (messy, units, aliases)
REGRESSION_CASES = [
    {
        "prompt": "make a 100x100mm steel plate",
        "expected_type": PartType.PLATE,
        "expected_params": {"width": 100.0, "height": 100.0, "material": "steel"}
    },
    {
        "prompt": "bracket width 4 inch height 100mm",
        "expected_type": PartType.BRACKET,
        "expected_params": {"width": 101.6, "height": 100.0}
    },
    {
        "prompt": "washer dia 20 inner 8",
        "expected_type": PartType.WASHER,
        "expected_params": {"outer_diameter": 20.0, "inner_diameter": 8.0}
    },
    {
        "prompt": "gusset 50mm triangle",
        "expected_type": PartType.GUSSET,
        "expected_params": {"width": 50.0, "shape": "triangle"}
    },
    {
        "prompt": "l-bracket 100x100 leg 20",
        "expected_type": PartType.BRACKET,
        "expected_params": {"width": 100.0, "height": 100.0, "leg_width": 20.0}
    }
]

@pytest.mark.parametrize("case", REGRESSION_CASES)
def test_schema_regression_parsing(case):
    """Verifies that legacy-style prompts are correctly normalized and validated."""
    prompt = case["prompt"]
    
    # Mock the LLM to return the "messy" but correct parameters
    # This simulates what the adapter would extract from the raw LLM response
    messy_params = {}
    if "100x100mm" in prompt:
        messy_params = {"width": 100, "height": 100}
    elif "4 inch" in prompt:
        messy_params = {"width": "4 inch", "height": 100}
    elif "dia 20" in prompt:
        messy_params = {"outer_dia": 20, "inner_dia": 8}
    elif "gusset" in prompt:
        messy_params = {"width": 50, "shape": "triangle"}
    elif "l-bracket" in prompt:
        messy_params = {"width": 100, "height": 100, "leg_width": 20}

    mock_raw_response = {
        "action": "create",
        "part_type": case["expected_type"].value,
        "parameters": messy_params,
        "rationale": "Regression test"
    }

    with patch('app.services.nlp.parser._call_gemini', return_value=mock_raw_response):
        intent = parse_engineering_request(prompt, provider="gemini")
        
        assert intent.action == CadAction.CREATE
        assert intent.validated_parameters is not None
        assert intent.validated_parameters.type == case["expected_type"]
        
        # Verify specific parameters
        for key, val in case["expected_params"].items():
            assert getattr(intent.validated_parameters, key) == val

@pytest.mark.parametrize("case", REGRESSION_CASES)
def test_schema_regression_geometry(case):
    """Verifies that the generated geometry remains accurate after schema hardening."""
    # Build a validated intent manually for speed (or use the one from previous test)
    from app.services.nlp.normalization import build_validated_intent
    
    # Using the same mock logic as above or just hardcoding the raw response for the case
    messy_params = {}
    if "100x100mm" in case["prompt"]:
        messy_params = {"width": 100, "height": 100}
    elif "4 inch" in case["prompt"]:
        messy_params = {"width": "4 inch", "height": 100}
    elif "dia 20" in case["prompt"]:
        messy_params = {"outer_dia": 20, "inner_dia": 8}
    elif "gusset" in case["prompt"]:
        messy_params = {"width": 50, "shape": "triangle"}
    elif "l-bracket" in case["prompt"]:
        messy_params = {"width": 100, "height": 100, "leg_width": 20}

    raw_intent = {
        "action": "create",
        "part_type": case["expected_type"].value,
        "parameters": messy_params
    }
    
    intent = build_validated_intent(raw_intent)
    params_dict = intent.validated_parameters.dict()
    
    generator = UniversalPartGenerator(intent.validated_parameters.type.value, params_dict)
    geo, data, schema = generator.generate_geometry()
    
    # Verification of geometric outcomes
    if case["expected_type"] == PartType.PLATE:
        assert data["width"] == 100.0
        assert data["height"] == 100.0
    elif case["expected_type"] == PartType.WASHER:
        # 20mm outer dia -> area ~ 314.15 - inner area (8mm dia -> 50.26)
        # area = pi * (R^2 - r^2) = pi * (100 - 16) = 84pi = 263.89
        assert data["area"] == pytest.approx(263.89, rel=1e-2)

if __name__ == "__main__":
    pytest.main([__file__])
