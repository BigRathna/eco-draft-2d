import math
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

from app.schemas.cad import PartGeometry
from app.schemas.checks import CheckResult
from app.schemas.common import ValidationResult

class ManufacturabilityRule(ABC):
    """Base class for all manufacturability rules."""
    
    @property
    @abstractmethod
    def id(self) -> str:
        """Unique identifier for the rule."""
        pass
        
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of the rule."""
        pass
        
    @abstractmethod
    def evaluate(self, geometry: PartGeometry, process_constraints: Dict[str, Any]) -> List[CheckResult]:
        """Evaluate the rule against the given geometry and constraints."""
        pass

class MinimumKerfRule(ManufacturabilityRule):
    @property
    def id(self) -> str: return "minimum_kerf"
    
    @property
    def description(self) -> str: return "Check if geometry features respect the minimum kerf width"
    
    def evaluate(self, geometry: PartGeometry, process_constraints: Dict[str, Any]) -> List[CheckResult]:
        min_kerf = process_constraints.get("min_kerf", 0.1)
        current_kerf = max(0.1, geometry.thickness * 0.01) # Simple heuristic from original implementation
        
        passed = current_kerf >= min_kerf
        
        return [CheckResult(
            check_type=self.id,
            validation=ValidationResult(
                passed=passed,
                message=f"Kerf width {current_kerf:.3f}mm {'meets' if passed else 'below'} minimum {min_kerf:.3f}mm",
                value=current_kerf,
                threshold=min_kerf
            ),
            recommendation=None if passed else "Increase thickness or use different manufacturing process"
        )]

class MinimumHoleDiameterRule(ManufacturabilityRule):
    @property
    def id(self) -> str: return "minimum_hole_diameter"
    
    @property
    def description(self) -> str: return "Check if hole diameters are strictly greater than the minimum allowed"
    
    def evaluate(self, geometry: PartGeometry, process_constraints: Dict[str, Any]) -> List[CheckResult]:
        min_hole_diameter = process_constraints.get("min_hole_diameter", 1.0)
        
        if not geometry.holes:
            return [CheckResult(
                check_type=self.id,
                validation=ValidationResult(
                    passed=True,
                    message="No holes to validate",
                    value=None,
                    threshold=min_hole_diameter
                )
            )]
            
        min_diameter = min(h.diameter for h in geometry.holes)
        passed = min_diameter >= min_hole_diameter
        
        return [CheckResult(
            check_type=self.id,
            validation=ValidationResult(
                passed=passed,
                message=f"Minimum hole diameter {min_diameter:.3f}mm {'meets' if passed else 'below'} minimum {min_hole_diameter:.3f}mm",
                value=min_diameter,
                threshold=min_hole_diameter
            ),
            recommendation=None if passed else f"Increase hole diameter to at least {min_hole_diameter}mm"
        )]

class MinimumLigamentRule(ManufacturabilityRule):
    @property
    def id(self) -> str: return "minimum_ligament"
    
    @property
    def description(self) -> str: return "Check if the distance between adjacent holes meets the minimum ligament width"
    
    def evaluate(self, geometry: PartGeometry, process_constraints: Dict[str, Any]) -> List[CheckResult]:
        min_ligament = process_constraints.get("min_ligament", 0.8)
        
        if len(geometry.holes) < 2:
            return [CheckResult(
                check_type=self.id,
                validation=ValidationResult(
                    passed=True,
                    message="No adjacent holes to validate ligament width",
                    value=None,
                    threshold=min_ligament
                )
            )]
            
        min_edge_distance = float('inf')
        holes = geometry.holes
        
        for i, h1 in enumerate(holes):
            for h2 in holes[i+1:]:
                dx = h2.center.x - h1.center.x
                dy = h2.center.y - h1.center.y
                center_distance = math.sqrt(dx*dx + dy*dy)
                edge_distance = center_distance - (h1.diameter / 2) - (h2.diameter / 2)
                min_edge_distance = min(min_edge_distance, edge_distance)
                
        if min_edge_distance == float('inf'):
            min_edge_distance = min_ligament + 1
            
        passed = min_edge_distance >= min_ligament
        
        return [CheckResult(
            check_type=self.id,
            validation=ValidationResult(
                passed=passed,
                message=f"Minimum ligament width {min_edge_distance:.3f}mm {'meets' if passed else 'below'} minimum {min_ligament:.3f}mm",
                value=min_edge_distance,
                threshold=min_ligament
            ),
            recommendation=None if passed else f"Increase hole spacing to ensure at least {min_ligament}mm ligament width"
        )]
