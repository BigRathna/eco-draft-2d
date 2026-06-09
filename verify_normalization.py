import sys
import os
import json

# Ensure backend/ is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.services.nlp.normalization import normalize_value, normalize_parameters, build_validated_intent

results = {}

try:
    results["unit_10_inch"] = normalize_value("10 inch")
    results["unit_5_cm"] = normalize_value("5 cm")
    results["alias_dia"] = normalize_parameters({"dia": 10})["diameter"]
    
    raw_intent = {
        "action": "create",
        "part_type": "washer",
        "parameters": {
            "outer_dia": "1 inch",
            "inner_dia": "10 mm"
        }
    }
    intent = build_validated_intent(raw_intent)
    results["intent_action"] = str(intent.action)
    results["intent_outer_dia"] = intent.validated_parameters.outer_diameter
    results["status"] = "OK"
except Exception as e:
    results["status"] = "ERROR"
    results["error"] = str(e)

with open("/run/media/brr/PrimeStore/Work/eco-draft-2d/test_results.json", "w") as f:
    json.dump(results, f, indent=4)

print("Done")
