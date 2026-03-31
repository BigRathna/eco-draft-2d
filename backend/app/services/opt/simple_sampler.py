import random
import time
import numpy as np
from typing import Dict, Any, List, Tuple

from app.schemas.optimization_simple import OptimizationPoint, SimpleOptimizationResponse
from app.services.cad.universal import UniversalPartGenerator
from app.core.config import settings

class SimpleSamplerOptimizer:
    """Generates a Pareto front using simple random sampling around a base design."""
    
    def __init__(self, part_type: str, base_parameters: Dict[str, Any], objectives: List[str]):
        self.part_type = part_type
        self.base_parameters = base_parameters
        self.objectives = objectives
        
        # Determine base material properties
        self.material_name = base_parameters.get("material", "steel")
        self.material_props = settings.materials.get(self.material_name, settings.materials["steel"])
        
    def run(self, num_samples: int = 50) -> SimpleOptimizationResponse:
        start_time = time.time()
        points = []
        
        # Always evaluate the base design first
        base_point = self._evaluate_sample(self.base_parameters)
        if base_point:
            points.append(base_point)
            
        # Define variation bounds for standard continuous parameters
        # We'll vary dimensions by ±20%
        variation_keys = [k for k, v in self.base_parameters.items() if isinstance(v, (int, float))]
        
        for _ in range(num_samples - 1):
            # Generate random variation
            sample_params = self.base_parameters.copy()
            for key in variation_keys:
                base_val = float(sample_params[key])
                if base_val > 0:
                    # Variation between 80% and 120%
                    variation = random.uniform(0.8, 1.2)
                    sample_params[key] = round(base_val * variation, 2)
                    
            point = self._evaluate_sample(sample_params)
            if point:
                points.append(point)
                
        # Find Pareto optimal points
        pareto_indices = self._find_pareto_front(points)
        
        end_time = time.time()
        optimization_time_ms = (end_time - start_time) * 1000
        
        return SimpleOptimizationResponse(
            points=points,
            pareto_optimal=pareto_indices,
            optimization_time_ms=optimization_time_ms
        )
        
    def _evaluate_sample(self, params: Dict[str, Any]) -> OptimizationPoint:
        try:
            generator = UniversalPartGenerator(self.part_type, params)
            geometry, geometry_data, part_geometry = generator.generate_geometry()
            
            area = geometry_data.get("area", 0.0)
            perimeter = geometry.length
            thickness = float(params.get("thickness", 5.0))
            
            volume = (area * thickness) / 1000000000.0  # mm3 to m3
            density = self.material_props.get("density", 7850)
            mass = volume * density
            
            # Simplified Cost Model: Function of mass and perimeter (cutting time)
            cost = (mass * 2.5) + (perimeter * 0.01)
            
            # Simplified Carbon Footprint: Material mass * CO2 factor
            co2_factor = self.material_props.get("co2_factor", 1.85)
            carbon_footprint = mass * co2_factor
            
            # Proxy for Strength: Cross-sectional area & moment of inertia approximation
            # Thicker + more area = higher strength score
            strength = (thickness ** 2) * (area ** 0.5) / 100.0
            
            return OptimizationPoint(
                parameters={k: float(v) for k, v in params.items() if isinstance(v, (int, float))},
                objectives={
                    "mass": mass,
                    "cost": cost,
                    "strength": strength,
                    "carbon_footprint": carbon_footprint
                }
            )
        except Exception as e:
            # If generation fails (e.g., self-intersecting polygon due to extreme parameters), skip
            print(f"Skipping failed sample: {e}")
            return None

    def _find_pareto_front(self, points: List[OptimizationPoint]) -> List[int]:
        """
        Identify the Pareto optimal points.
        For Mass, Cost, Carbon: Lower is better.
        For Strength: Higher is better.
        """
        if not points:
            return []
            
        costs = np.zeros((len(points), 4))
        for i, pt in enumerate(points):
            costs[i, 0] = pt.objectives.get("mass", float('inf'))
            costs[i, 1] = pt.objectives.get("cost", float('inf'))
            # Strength is maximized, so we minimize negative strength
            costs[i, 2] = -pt.objectives.get("strength", -float('inf'))
            costs[i, 3] = pt.objectives.get("carbon_footprint", float('inf'))
            
        is_efficient = np.ones(costs.shape[0], dtype=bool)
        for i, c in enumerate(costs):
            if is_efficient[i]:
                # Keep any point with a lower cost (meaning < 0 difference somewhere)
                is_efficient[is_efficient] = np.any(costs[is_efficient] < c, axis=1)
                is_efficient[i] = True  # And keep self
                
        return np.where(is_efficient)[0].tolist()
