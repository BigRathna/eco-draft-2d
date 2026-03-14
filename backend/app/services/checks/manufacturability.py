"""Manufacturability check implementation."""

import time
import math
from typing import List, Tuple, Dict, Any

from shapely.geometry import Polygon, Point
from shapely.ops import unary_union

from app.schemas.checks import ManufacturabilityCheckRequest, ManufacturabilityCheckResponse, CheckResult
from app.schemas.common import ValidationResult, ManufacturingProcess
from app.core.config import settings


class ManufacturabilityChecker:
    """Checker for manufacturability constraints."""
    
    def __init__(self, request: ManufacturabilityCheckRequest):
        """Initialize with check request."""
        self.request = request
        self.process_constraints = settings.manufacturing.get(
            request.manufacturing_process.value, {}
        )
        
    def check_manufacturability(self) -> ManufacturabilityCheckResponse:
        """Perform all manufacturability checks."""
        start_time = time.time()
        
        checks = []
        
        # Extract geometry from data
        geometry_data = self.request.geometry_data
        
        # Perform individual checks
        checks.append(self._check_minimum_kerf())
        checks.append(self._check_minimum_radius(geometry_data))
        checks.append(self._check_hole_diameter(geometry_data))
        checks.append(self._check_ligament_width(geometry_data))
        
        # Overall assessment
        overall_passed = all(check.validation.passed for check in checks)
        
        # Generate summary
        if overall_passed:
            summary = f"Part passes all {self.request.manufacturing_process.value} manufacturability checks."
        else:
            failed_checks = [check.check_type for check in checks if not check.validation.passed]
            summary = f"Part fails {len(failed_checks)} checks: {', '.join(failed_checks)}"
            
        end_time = time.time()
        check_time_ms = (end_time - start_time) * 1000
        
        return ManufacturabilityCheckResponse(
            overall_passed=overall_passed,
            manufacturing_process=self.request.manufacturing_process,
            checks=checks,
            summary=summary,
            check_time_ms=check_time_ms
        )
        
    def _check_minimum_kerf(self) -> CheckResult:
        """Check minimum kerf requirement."""
        min_kerf = self.process_constraints.get("min_kerf", 0.1)
        
        # For this check, we assume the thickness meets kerf requirements
        # In a real implementation, this would check the cutting process capabilities
        current_kerf = max(0.1, self.request.thickness * 0.01)  # Simple heuristic
        
        passed = current_kerf >= min_kerf
        
        validation = ValidationResult(
            passed=passed,
            message=f"Kerf width {current_kerf:.3f}mm {'meets' if passed else 'below'} minimum {min_kerf:.3f}mm",
            value=current_kerf,
            threshold=min_kerf
        )
        
        recommendation = None if passed else f"Increase thickness or use different manufacturing process"
        
        return CheckResult(
            check_type="minimum_kerf",
            validation=validation,
            recommendation=recommendation
        )
        
    def _check_minimum_radius(self, geometry_data: Dict[str, Any]) -> CheckResult:
        """Check minimum radius requirement."""
        min_radius = self.process_constraints.get("min_radius", 0.2)
        
        # Extract corner radius from parameters if available
        params = geometry_data.get("parameters", {})
        corner_radius = params.get("corner_radius", 0.0)
        
        passed = corner_radius >= min_radius
        
        validation = ValidationResult(
            passed=passed,
            message=f"Corner radius {corner_radius:.3f}mm {'meets' if passed else 'below'} minimum {min_radius:.3f}mm",
            value=corner_radius,
            threshold=min_radius
        )
        
        recommendation = None if passed else f"Increase corner radius to at least {min_radius}mm"
        
        return CheckResult(
            check_type="minimum_radius",
            validation=validation,
            recommendation=recommendation
        )
        
    def _check_hole_diameter(self, geometry_data: Dict[str, Any]) -> CheckResult:
        """Check minimum hole diameter requirement."""
        min_hole_diameter = self.process_constraints.get("min_hole_diameter", 1.0)
        
        # Extract hole diameters from parameters
        params = geometry_data.get("parameters", {})
        hole_diameters = []
        
        if "hole_diameter" in params and params["hole_diameter"]:
            hole_diameters.append(params["hole_diameter"])
            
        if not hole_diameters:
            # No holes to check
            validation = ValidationResult(
                passed=True,
                message="No holes to validate",
                value=None,
                threshold=min_hole_diameter
            )
            
            return CheckResult(
                check_type="minimum_hole_diameter",
                validation=validation,
                recommendation=None
            )
            
        min_diameter = min(hole_diameters)
        passed = min_diameter >= min_hole_diameter
        
        validation = ValidationResult(
            passed=passed,
            message=f"Minimum hole diameter {min_diameter:.3f}mm {'meets' if passed else 'below'} minimum {min_hole_diameter:.3f}mm",
            value=min_diameter,
            threshold=min_hole_diameter
        )
        
        recommendation = None if passed else f"Increase hole diameter to at least {min_hole_diameter}mm"
        
        return CheckResult(
            check_type="minimum_hole_diameter",
            validation=validation,
            recommendation=recommendation
        )
        
    def _check_ligament_width(self, geometry_data: Dict[str, Any]) -> CheckResult:
        """Check minimum ligament width requirement."""
        min_ligament = self.process_constraints.get("min_ligament", 0.8)
        
        # Calculate minimum ligament width from hole pattern
        params = geometry_data.get("parameters", {})
        hole_centers = geometry_data.get("hole_centers", [])
        
        if len(hole_centers) < 2:
            # No adjacent holes to check
            validation = ValidationResult(
                passed=True,
                message="No adjacent holes to validate ligament width",
                value=None,
                threshold=min_ligament
            )
            
            return CheckResult(
                check_type="minimum_ligament",
                validation=validation,
                recommendation=None
            )
            
        # Calculate minimum distance between hole edges
        hole_radius = params.get("hole_diameter", 8.0) / 2
        min_edge_distance = float('inf')
        
        for i, center1 in enumerate(hole_centers):
            for j, center2 in enumerate(hole_centers[i+1:], i+1):
                # Calculate distance between centers
                dx = center2[0] - center1[0]
                dy = center2[1] - center1[1]
                center_distance = math.sqrt(dx*dx + dy*dy)
                
                # Calculate edge-to-edge distance (ligament width)
                edge_distance = center_distance - 2 * hole_radius
                min_edge_distance = min(min_edge_distance, edge_distance)
                
        if min_edge_distance == float('inf'):
            min_edge_distance = min_ligament + 1  # Default to passing
            
        passed = min_edge_distance >= min_ligament
        
        validation = ValidationResult(
            passed=passed,
            message=f"Minimum ligament width {min_edge_distance:.3f}mm {'meets' if passed else 'below'} minimum {min_ligament:.3f}mm",
            value=min_edge_distance,
            threshold=min_ligament
        )
        
        recommendation = None if passed else f"Increase hole spacing to ensure at least {min_ligament}mm ligament width"
        
        return CheckResult(
            check_type="minimum_ligament",
            validation=validation,
            recommendation=recommendation
        )
