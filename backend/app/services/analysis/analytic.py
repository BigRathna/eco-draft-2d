"""Analytic stress analysis implementation."""

import time
import math
from typing import List, Dict, Any, Optional

import numpy as np

from app.schemas.analysis import AnalysisRequest, AnalysisResponse, StressResult, LoadCase
from app.schemas.common import Point2D, Material
from app.core.config import settings


class AnalyticAnalyzer:
    """Analytic stress analyzer for 2D parts."""
    
    def __init__(self, request: AnalysisRequest):
        """Initialize with analysis request."""
        self.request = request
        # Extract material name from various input formats
        material_name = self._extract_material_name(request.material)
        self.material_props = settings.materials.get(material_name, {})
        
    def _extract_material_name(self, material_input) -> str:
        """Extract material name from various input formats."""
        if isinstance(material_input, dict):
            # Material object with properties
            return material_input.get("name", "steel").lower()
        elif hasattr(material_input, 'value'):
            # Material enum
            return material_input.value
        else:
            # String
            return str(material_input).lower()
        
    def analyze(self) -> AnalysisResponse:
        """Perform stress analysis for all load cases."""
        start_time = time.time()
        
        results = []
        critical_load_case = None
        max_stress = 0.0
        
        for load_case in self.request.load_cases:
            result = self._analyze_load_case(load_case)
            results.append(result)
            
            if result.max_stress > max_stress:
                max_stress = result.max_stress
                critical_load_case = load_case.name
                
        # Generate recommendations
        recommendations = self._generate_recommendations(results)
        
        end_time = time.time()
        analysis_time_ms = (end_time - start_time) * 1000
        
        # Convert material to appropriate response format
        material_name = self._extract_material_name(self.request.material)
        
        return AnalysisResponse(
            material=material_name,
            yield_strength=self.material_props.get("yield_strength", 250e6),
            results=results,
            critical_load_case=critical_load_case,
            recommendations=recommendations,
            analysis_time_ms=analysis_time_ms
        )
        
    def _analyze_load_case(self, load_case: LoadCase) -> StressResult:
        """Analyze a single load case."""
        geometry_data = self.request.geometry_data
        
        # Calculate net section area
        net_area = self._calculate_net_section_area(geometry_data)
        
        # Calculate direct stress from axial load
        force_magnitude = math.sqrt(load_case.force_x**2 + load_case.force_y**2)
        direct_stress = force_magnitude / net_area if net_area > 0 else 0.0
        
        # Calculate bending stress from moment
        bending_stress = self._calculate_bending_stress(load_case.moment, geometry_data)
        
        # Combine stresses (simplified approach)
        max_stress = direct_stress + abs(bending_stress)
        net_section_stress = direct_stress
        
        # Calculate safety factors
        yield_strength = self.material_props.get("yield_strength", 250e6)
        MAX_SAFETY_FACTOR = 1e6  # Large finite number instead of infinity
        safety_factor = yield_strength / max_stress if max_stress > 0 else MAX_SAFETY_FACTOR
        margin_of_safety = safety_factor - 1.0
        
        # Determine if stress levels are acceptable (safety factor > 2.0)
        passed = safety_factor >= 2.0
        
        # Find stress location (simplified - assume at centroid)
        centroid_data = geometry_data.get("centroid", {"x": 0, "y": 0})
        stress_location = Point2D(x=centroid_data["x"], y=centroid_data["y"])
        
        return StressResult(
            load_case_name=load_case.name,
            max_stress=max_stress,
            stress_location=stress_location,
            net_section_stress=net_section_stress,
            safety_factor=safety_factor,
            margin_of_safety=margin_of_safety,
            passed=passed
        )
        
    def _calculate_net_section_area(self, geometry_data: Dict[str, Any]) -> float:
        """Calculate net section area (gross area minus holes)."""
        gross_area = geometry_data.get("area", 0.0)
        
        # Subtract hole areas
        params = geometry_data.get("parameters", {})
        hole_diameter = params.get("hole_diameter", 0.0)
        
        if hole_diameter is not None and hole_diameter > 0:
            hole_area = math.pi * (hole_diameter / 2)**2
            
            # Count number of holes
            hole_centers = geometry_data.get("hole_centers", [])
            num_holes = len(hole_centers)
            
            # For gusset with single central hole
            if geometry_data.get("type") == "gusset":
                num_holes = 1 if hole_diameter > 0 else 0
                
            net_area = gross_area - num_holes * hole_area
        else:
            net_area = gross_area
            
        return max(net_area, 0.01)  # Minimum area to avoid division by zero
        
    def _calculate_bending_stress(self, moment: float, geometry_data: Dict[str, Any]) -> float:
        """Calculate bending stress from applied moment."""
        if abs(moment) < 1e-6:
            return 0.0
            
        # Calculate section modulus (simplified rectangular approximation)
        bounds = geometry_data.get("bounds", [0, 0, 100, 100])
        width = bounds[2] - bounds[0]  # x-direction
        height = bounds[3] - bounds[1]  # y-direction
        
        thickness = self.request.thickness
        
        # Section modulus for rectangular section
        I = (width * thickness**3) / 12  # Moment of inertia about neutral axis
        c = thickness / 2  # Distance from neutral axis to extreme fiber
        
        section_modulus = I / c if c > 0 else 0.0
        
        bending_stress = moment / section_modulus if section_modulus > 0 else 0.0
        
        return bending_stress
        
    def _generate_recommendations(self, results: List[StressResult]) -> List[str]:
        """Generate design recommendations based on analysis results."""
        recommendations = []
        
        failed_cases = [r for r in results if not r.passed]
        
        if not failed_cases:
            recommendations.append("All load cases pass stress requirements.")
            return recommendations
            
        # Analyze failure modes
        min_safety_factor = min(r.safety_factor for r in results)
        
        if min_safety_factor < 1.0:
            recommendations.append("CRITICAL: Part exceeds yield strength under applied loads.")
        elif min_safety_factor < 2.0:
            recommendations.append("WARNING: Safety factor below recommended minimum of 2.0.")
            
        # Specific recommendations
        if min_safety_factor < 2.0:
            recommendations.extend([
                "Consider increasing part thickness",
                "Consider using higher strength material",
                "Review loading conditions and reduce if possible",
                "Add reinforcement features like ribs or gussets"
            ])
            
        # Net section recommendations
        high_net_stress_cases = [r for r in results if r.net_section_stress > 0.6 * self.material_props.get("yield_strength", 250e6)]
        if high_net_stress_cases:
            recommendations.append("High net section stress detected - consider larger cross-section or fewer/smaller holes")
            
        return recommendations
