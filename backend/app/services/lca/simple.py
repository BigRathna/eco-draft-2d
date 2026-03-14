"""Simple Life Cycle Assessment calculator."""

import time
from typing import List

from app.schemas.lca import LCARequest, LCAResponse, MaterialData
from app.schemas.common import Material
from app.core.config import settings


class SimpleLCACalculator:
    """Simple LCA calculator focusing on material production emissions."""
    
    def __init__(self, request: LCARequest):
        """Initialize with LCA request."""
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
        
    def calculate_lca(self) -> LCAResponse:
        """Calculate life cycle assessment metrics."""
        start_time = time.time()
        
        # Extract geometry data
        geometry_data = self.request.geometry_data
        area_mm2 = geometry_data.get("area", 0.0)
        
        # Convert to SI units
        area_m2 = area_mm2 / 1e6  # mm² to m²
        thickness_m = self.request.thickness / 1000  # mm to m
        volume_m3 = area_m2 * thickness_m
        
        # Calculate mass
        density = self.material_props.get("density", 7850)  # kg/m³
        mass_per_part = volume_m3 * density
        total_mass = mass_per_part * self.request.quantity
        
        # Calculate CO₂ emissions
        co2_factor = self.material_props.get("co2_factor", 1.85)  # kg CO₂ / kg material
        co2_per_part = mass_per_part * co2_factor
        total_co2_emissions = total_mass * co2_factor
        
        # Create material data object
        material_data = MaterialData(
            density=density,
            co2_factor=co2_factor,
            recyclability=self._get_recyclability_factor()
        )
        
        # Calculate sustainability rating
        sustainability_rating = self._calculate_sustainability_rating(co2_per_part, mass_per_part)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            co2_per_part, mass_per_part, sustainability_rating
        )
        
        end_time = time.time()
        calculation_time_ms = (end_time - start_time) * 1000
        
        # Convert material to appropriate response format
        material_name = self._extract_material_name(self.request.material)
        
        return LCAResponse(
            material=material_name,
            material_data=material_data,
            area=area_mm2,
            volume=volume_m3 * 1e9,  # Convert to mm³ for display
            mass=mass_per_part,
            total_mass=total_mass,
            co2_emissions=total_co2_emissions,
            co2_per_part=co2_per_part,
            sustainability_rating=sustainability_rating,
            recommendations=recommendations,
            calculation_time_ms=calculation_time_ms
        )
        
    def _get_recyclability_factor(self) -> float:
        """Get recyclability factor for the material."""
        material_name = self._extract_material_name(self.request.material)
        recyclability_factors = {
            "steel": 0.85,
            "aluminum": 0.95,
            "stainless_steel": 0.80
        }
        return recyclability_factors.get(material_name, 0.80)
        
    def _calculate_sustainability_rating(self, co2_per_part: float, mass_per_part: float) -> str:
        """Calculate sustainability rating A-F based on CO₂ intensity."""
        # Calculate CO₂ intensity (kg CO₂ / kg part)
        co2_intensity = co2_per_part / mass_per_part if mass_per_part > 0 else 0.0
        
        # Rating thresholds based on material CO₂ factors
        if co2_intensity <= 2.0:
            return "A"  # Excellent
        elif co2_intensity <= 4.0:
            return "B"  # Good
        elif co2_intensity <= 6.0:
            return "C"  # Fair
        elif co2_intensity <= 8.0:
            return "D"  # Poor
        elif co2_intensity <= 12.0:
            return "E"  # Very Poor
        else:
            return "F"  # Unacceptable
            
    def _generate_recommendations(
        self, co2_per_part: float, mass_per_part: float, rating: str
    ) -> List[str]:
        """Generate sustainability recommendations."""
        recommendations = []
        
        # Material-specific recommendations
        material_name = self._extract_material_name(self.request.material)
        if material_name == "aluminum":
            if co2_per_part > 0.1:  # High CO₂ for aluminum part
                recommendations.extend([
                    "Consider using recycled aluminum content to reduce CO₂ impact",
                    "Aluminum has high recyclability - plan for end-of-life recycling"
                ])
        elif material_name == "steel":
            recommendations.extend([
                "Steel has relatively low CO₂ impact compared to aluminum",
                "Consider using high-strength steel to reduce material usage"
            ])
        elif material_name == "stainless_steel":
            recommendations.extend([
                "Stainless steel has moderate CO₂ impact but excellent durability",
                "Long service life can offset higher initial environmental impact"
            ])
            
        # Design optimization recommendations
        geometry_data = self.request.geometry_data
        if geometry_data.get("type") == "base_plate":
            recommendations.append("Optimize hole pattern to minimize material waste")
        elif geometry_data.get("type") == "gusset":
            recommendations.append("Consider topology optimization to reduce material usage")
            
        # General recommendations based on rating
        if rating in ["D", "E", "F"]:
            recommendations.extend([
                "Consider alternative materials with lower CO₂ impact",
                "Evaluate design optimization to reduce material usage",
                "Investigate manufacturing process efficiency improvements"
            ])
        elif rating in ["A", "B"]:
            recommendations.extend([
                "Excellent sustainability performance",
                "Consider sharing design practices for other projects"
            ])
        else:  # C rating
            recommendations.extend([
                "Good sustainability performance with room for improvement",
                "Consider minor design optimizations to reduce material usage"
            ])
            
        # Quantity-based recommendations
        if self.request.quantity > 100:
            recommendations.extend([
                "High production volume - consider investing in material efficiency",
                "Bulk production enables sustainable practices like material recycling loops"
            ])
            
        # Mass-based recommendations
        if mass_per_part > 1.0:  # Heavy parts
            recommendations.append("Consider lightweighting strategies to reduce material usage")
        elif mass_per_part < 0.01:  # Very light parts
            recommendations.append("Thin section - verify structural adequacy vs. sustainability trade-offs")
            
        return recommendations
