"""Base plate geometry generation using Shapely."""

import math
from typing import Dict, Any, List, Tuple

from shapely.geometry import Polygon, Point
from shapely.ops import unary_union

from app.schemas.parts import BasePlateParams
from app.schemas.common import Point2D, GeometryInfo
from app.core.config import settings


class BasePlateGenerator:
    """Generator for base plate geometry."""
    
    def __init__(self, params: BasePlateParams):
        """Initialize with base plate parameters."""
        self.params = params
        
    def generate_geometry(self) -> Tuple[Polygon, Dict[str, Any]]:
        """Generate base plate geometry.
        
        Returns:
            Tuple of (Shapely Polygon, geometry data dict)
        """
        # Create basic rectangular outline
        outline = self._create_outline()
        
        # Create holes based on pattern
        holes = self._create_holes()
        
        # Subtract holes from outline
        for hole in holes:
            outline = outline.difference(hole)
            
        # Calculate geometry info
        geometry_info = self._calculate_geometry_info(outline)
        
        # Create geometry data dictionary
        geometry_data = {
            "type": "base_plate",
            "parameters": self.params.dict(),
            "outline_coords": list(outline.exterior.coords),
            "holes": self._get_hole_coords(outline),
            "hole_centers": self._get_hole_centers(),
            "area": outline.area,
            "perimeter": outline.length,
            "centroid": {"x": outline.centroid.x, "y": outline.centroid.y},
            "bounds": outline.bounds,
        }
        
        return outline, geometry_data
        
    def _create_outline(self) -> Polygon:
        """Create basic rectangular outline."""
        return Polygon([
            (0, 0),
            (self.params.length, 0),
            (self.params.length, self.params.width),
            (0, self.params.width),
        ])
        
    def _create_holes(self) -> List[Polygon]:
        """Create holes based on the specified pattern."""
        if self.params.hole_pattern == "rectangular":
            return self._create_rectangular_hole_pattern()
        elif self.params.hole_pattern == "circular":
            return self._create_circular_hole_pattern()
        else:
            return self._create_rectangular_hole_pattern()
            
    def _create_rectangular_hole_pattern(self) -> List[Polygon]:
        """Create rectangular grid of holes."""
        holes = []
        radius = self.params.hole_diameter / 2
        
        # Calculate number of holes in each direction
        available_length = self.params.length - 2 * self.params.edge_distance
        available_width = self.params.width - 2 * self.params.edge_distance
        
        num_holes_x = max(1, int(available_length / self.params.hole_spacing_x) + 1)
        num_holes_y = max(1, int(available_width / self.params.hole_spacing_y) + 1)
        
        # Adjust spacing to center the holes
        actual_spacing_x = available_length / max(1, num_holes_x - 1) if num_holes_x > 1 else 0
        actual_spacing_y = available_width / max(1, num_holes_y - 1) if num_holes_y > 1 else 0
        
        for i in range(num_holes_x):
            for j in range(num_holes_y):
                center_x = self.params.edge_distance + i * actual_spacing_x
                center_y = self.params.edge_distance + j * actual_spacing_y
                
                hole = self._create_circular_hole(center_x, center_y, radius)
                holes.append(hole)
                
        return holes
        
    def _create_circular_hole_pattern(self) -> List[Polygon]:
        """Create circular pattern of holes."""
        holes = []
        radius = self.params.hole_diameter / 2
        
        # Calculate center of plate
        center_x = self.params.length / 2
        center_y = self.params.width / 2
        
        # Calculate pattern radius
        pattern_radius = min(
            self.params.length / 2 - self.params.edge_distance - radius,
            self.params.width / 2 - self.params.edge_distance - radius
        )
        
        # Number of holes in circular pattern
        circumference = 2 * math.pi * pattern_radius
        num_holes = max(4, int(circumference / self.params.hole_spacing_x))
        
        for i in range(num_holes):
            angle = 2 * math.pi * i / num_holes
            hole_x = center_x + pattern_radius * math.cos(angle)
            hole_y = center_y + pattern_radius * math.sin(angle)
            
            hole = self._create_circular_hole(hole_x, hole_y, radius)
            holes.append(hole)
            
        # Add center hole
        center_hole = self._create_circular_hole(center_x, center_y, radius)
        holes.append(center_hole)
        
        return holes
        
    def _create_circular_hole(self, center_x: float, center_y: float, radius: float) -> Polygon:
        """Create a single circular hole."""
        # Create circle as polygon with many sides
        num_sides = 32
        angles = [i * 2 * math.pi / num_sides for i in range(num_sides)]
        coords = [(center_x + radius * math.cos(a), center_y + radius * math.sin(a)) 
                 for a in angles]
        
        return Polygon(coords)
        
    def _get_hole_coords(self, polygon: Polygon) -> List[List[Tuple[float, float]]]:
        """Get coordinates of all holes in the polygon."""
        holes = []
        if hasattr(polygon, 'interiors'):
            for interior in polygon.interiors:
                holes.append(list(interior.coords))
        return holes
        
    def _get_hole_centers(self) -> List[Tuple[float, float]]:
        """Get centers of all holes."""
        hole_centers = []
        
        if self.params.hole_pattern == "rectangular":
            available_length = self.params.length - 2 * self.params.edge_distance
            available_width = self.params.width - 2 * self.params.edge_distance
            
            num_holes_x = max(1, int(available_length / self.params.hole_spacing_x) + 1)
            num_holes_y = max(1, int(available_width / self.params.hole_spacing_y) + 1)
            
            actual_spacing_x = available_length / max(1, num_holes_x - 1) if num_holes_x > 1 else 0
            actual_spacing_y = available_width / max(1, num_holes_y - 1) if num_holes_y > 1 else 0
            
            for i in range(num_holes_x):
                for j in range(num_holes_y):
                    center_x = self.params.edge_distance + i * actual_spacing_x
                    center_y = self.params.edge_distance + j * actual_spacing_y
                    hole_centers.append((center_x, center_y))
                    
        return hole_centers
        
    def _calculate_geometry_info(self, polygon: Polygon) -> GeometryInfo:
        """Calculate geometry information."""
        centroid = polygon.centroid
        bounds = polygon.bounds
        
        return GeometryInfo(
            area=polygon.area,
            perimeter=polygon.length,
            centroid=Point2D(x=centroid.x, y=centroid.y),
            bounding_box=(
                Point2D(x=bounds[0], y=bounds[1]),  # min
                Point2D(x=bounds[2], y=bounds[3])   # max
            )
        )
        
    def calculate_mass(self, area_mm2: float) -> float:
        """Calculate part mass based on area and material density."""
        material_props = settings.materials.get(self.params.material.value, {})
        density = material_props.get("density", 7850)  # kg/m³
        
        # Convert area from mm² to m²
        area_m2 = area_mm2 / 1e6
        thickness_m = self.params.thickness / 1000
        
        volume_m3 = area_m2 * thickness_m
        mass_kg = volume_m3 * density
        
        return mass_kg
