"""Gusset plate geometry generation using Shapely."""

import math
from typing import Dict, Any, Optional, List, Tuple

from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from shapely.affinity import translate

from app.schemas.parts import GussetParams
from app.schemas.common import Point2D, GeometryInfo
from app.core.config import settings


class GussetGenerator:
    """Generator for gusset plate geometry."""
    
    def __init__(self, params: GussetParams):
        """Initialize with gusset parameters."""
        self.params = params
        
    def generate_geometry(self) -> Tuple[Polygon, Dict[str, Any]]:
        """Generate gusset plate geometry.
        
        Returns:
            Tuple of (Shapely Polygon, geometry data dict)
        """
        # Create basic rectangular outline
        outline = self._create_outline()
        
        # Apply corner radius
        if self.params.corner_radius > 0:
            outline = self._apply_corner_radius(outline)
            
        # Apply chamfers
        if self.params.chamfer_size > 0:
            outline = self._apply_chamfers(outline)
            
        # Add central hole if specified
        if self.params.hole_diameter is not None and self.params.hole_diameter > 0:
            hole = self._create_central_hole()
            outline = outline.difference(hole)
            
        # Calculate geometry info
        geometry_info = self._calculate_geometry_info(outline)
        
        # Create geometry data dictionary
        geometry_data = {
            "type": "gusset",
            "parameters": self.params.dict(),
            "outline_coords": list(outline.exterior.coords),
            "holes": self._get_hole_coords(outline),
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
            (self.params.width, 0),
            (self.params.width, self.params.height),
            (0, self.params.height),
        ])
        
    def _apply_corner_radius(self, polygon: Polygon) -> Polygon:
        """Apply corner radius to polygon."""
        # Get corner coordinates
        coords = list(polygon.exterior.coords)[:-1]  # Remove duplicate last point
        
        # Create rounded corners
        rounded_coords = []
        radius = self.params.corner_radius
        
        for i in range(len(coords)):
            curr = coords[i]
            prev = coords[i-1]
            next_coord = coords[(i+1) % len(coords)]
            
            # Calculate vectors from current point
            prev_vec = (prev[0] - curr[0], prev[1] - curr[1])
            next_vec = (next_coord[0] - curr[0], next_coord[1] - curr[1])
            
            # Normalize vectors
            prev_len = math.sqrt(prev_vec[0]**2 + prev_vec[1]**2)
            next_len = math.sqrt(next_vec[0]**2 + next_vec[1]**2)
            
            if prev_len > 0 and next_len > 0:
                prev_unit = (prev_vec[0]/prev_len, prev_vec[1]/prev_len)
                next_unit = (next_vec[0]/next_len, next_vec[1]/next_len)
                
                # Calculate arc points
                start_point = (curr[0] + radius * prev_unit[0], curr[1] + radius * prev_unit[1])
                end_point = (curr[0] + radius * next_unit[0], curr[1] + radius * next_unit[1])
                
                # Add arc points (simplified - just add start and end)
                rounded_coords.extend([start_point, end_point])
                
        if rounded_coords:
            return Polygon(rounded_coords).buffer(0)  # Fix any self-intersections
        return polygon
        
    def _apply_chamfers(self, polygon: Polygon) -> Polygon:
        """Apply chamfers to polygon corners."""
        # Simplified chamfer implementation
        chamfer_size = self.params.chamfer_size
        buffered = polygon.buffer(-chamfer_size/2)
        return buffered.buffer(chamfer_size/2)
        
    def _create_central_hole(self) -> Polygon:
        """Create central circular hole."""
        center_x = self.params.width / 2
        center_y = self.params.height / 2
        radius = self.params.hole_diameter / 2
        
        # Create circle as polygon with many sides
        angles = [i * 2 * math.pi / 32 for i in range(32)]
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
