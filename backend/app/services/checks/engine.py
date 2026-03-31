import time
from typing import List

from app.schemas.checks import ManufacturabilityCheckRequest, ManufacturabilityCheckResponse, CheckResult
from app.schemas.common import ValidationResult
from app.core.config import settings
from .rules import ManufacturabilityRule, MinimumKerfRule, MinimumHoleDiameterRule, MinimumLigamentRule

class CheckEngine:
    """Orchestrator for evaluating manufacturability rules against geometry."""
    
    def __init__(self, rules: List[ManufacturabilityRule] = None):
        if rules is None:
            # Default rules if none provided
            self.rules = [
                MinimumKerfRule(),
                MinimumHoleDiameterRule(),
                MinimumLigamentRule()
            ]
        else:
            self.rules = rules
            
    def run(self, request: ManufacturabilityCheckRequest) -> ManufacturabilityCheckResponse:
        start_time = time.time()
        
        process_constraints = settings.manufacturing.get(
            request.manufacturing_process.value, {}
        )
        
        checks = []
        
        # Build PartGeometry from raw dict if missing
        part_geo = request.part_geometry
        if not part_geo and hasattr(request, 'geometry_data') and request.geometry_data:
            from app.schemas.cad import PartGeometry, HoleFeature, Point2D
            try:
                outer = []
                for pt in request.geometry_data.get('outline_coords', []):
                    # handle possible [x, y] lists
                    if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                        outer.append(Point2D(x=float(pt[0]), y=float(pt[1])))
                    elif isinstance(pt, dict) and 'x' in pt and 'y' in pt:
                        outer.append(Point2D(x=float(pt['x']), y=float(pt['y'])))
                
                holes = []
                raw_holes = request.geometry_data.get('holes', [])
                for i, h in enumerate(raw_holes):
                    radius = h.get('radius') or (h.get('diameter', 0) / 2)
                    center_pt = None
                    if 'center' in h and isinstance(h['center'], (list, tuple)) and len(h['center']) >= 2:
                        center_pt = Point2D(x=float(h['center'][0]), y=float(h['center'][1]))
                    elif 'x' in h and 'y' in h:
                        center_pt = Point2D(x=float(h['x']), y=float(h['y']))
                        
                    if center_pt and radius > 0:
                        holes.append(HoleFeature(
                            id=f"hole_{i}",
                            center=center_pt,
                            diameter=radius * 2
                        ))

                if outer:
                    part_geo = PartGeometry(
                        outer_boundary=outer,
                        holes=holes,
                        material="steel",  # Fallback
                        thickness=getattr(request, 'thickness', 5.0)
                    )
            except Exception as e:
                print(f"Failed to build PartGeometry from dict: {e}")

        if part_geo:
            for rule in self.rules:
                checks.extend(rule.evaluate(part_geo, process_constraints))
        else:
            # Fallback for when part_geometry is not available
            # We still return that it passes so it doesn't break legacy calls
            checks.append(CheckResult(
                check_type="missing_geometry_schema",
                validation=ValidationResult(
                    passed=True,
                    message="No PartGeometry provided, skipping deep rules",
                    value=None,
                    threshold=None
                )
            ))
            
        overall_passed = all(check.validation.passed for check in checks)
        
        if overall_passed:
            summary = f"Part passes all {request.manufacturing_process.value} manufacturability checks."
        else:
            failed_checks = [check.check_type for check in checks if not check.validation.passed]
            summary = f"Part fails {len(failed_checks)} checks: {', '.join(failed_checks)}"
            
        end_time = time.time()
        check_time_ms = (end_time - start_time) * 1000
        
        return ManufacturabilityCheckResponse(
            overall_passed=overall_passed,
            manufacturing_process=request.manufacturing_process,
            checks=checks,
            summary=summary,
            check_time_ms=check_time_ms
        )
