"""
Universal 2D CAD Part Generator

This module provides a flexible system for generating 2D mechanical parts
based on generic parameters. It can handle any part type by mapping common
shapes and features to CAD operations.
"""

import math
from typing import Dict, Any, List, Tuple, Union
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
import numpy as np

from app.schemas.parts import BasePartParams


class UniversalPartGenerator:
    """Universal generator for 2D mechanical parts."""
    
    def __init__(self, part_type: str, parameters: Dict[str, Any]):
        """Initialize the universal part generator.
        
        Args:
            part_type: Type of part (e.g., 'bracket', 'angle', 'plate', 'washer')
            parameters: Dictionary of part parameters
        """
        self.part_type = part_type.lower()
        self.params = self._validate_and_set_defaults(parameters)
        
    def _validate_and_set_defaults(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate parameters and set defaults based on part type."""
        params = parameters.copy()
        
        # Common defaults for all parts
        common_defaults = {
            "material": "steel",
            "thickness": 5.0,
            "width": 100.0,
            "height": 100.0,
            "corner_radius": 0.0,
            "chamfer_size": 0.0,
        }
        
        # Part-specific defaults
        part_defaults = self._get_part_specific_defaults()
        
        # Apply defaults
        for key, value in {**common_defaults, **part_defaults}.items():
            if key not in params:
                params[key] = value
                
        return params
    
    def _get_part_specific_defaults(self) -> Dict[str, Any]:
        """Get default parameters specific to the part type."""
        defaults_map = {
            "gusset": {
                "shape": "triangle",
                "width": 100.0,
                "height": 80.0,
                "corner_radius": 5.0,
            },
            "bracket": {
                "shape": "L",
                "width": 120.0,
                "height": 100.0,
                "leg_length": 80.0,
                "hole_diameter": 8.0,
                "hole_spacing": 40.0,
            },
            "l_bracket": {
                "shape": "L",
                "width": 120.0,
                "height": 100.0,
                "leg_length": 80.0,
                "leg_width": 25.0,
                "hole_diameter": 8.0,
                "hole_spacing": 40.0,
            },
            "t_bracket": {
                "shape": "T",
                "width": 150.0,
                "height": 120.0,
                "stem_width": 30.0,
                "flange_height": 30.0,
                "hole_diameter": 8.0,
                "hole_spacing": 40.0,
            },
            "angle": {
                "shape": "L", 
                "width": 100.0,
                "height": 100.0,
                "leg_width": 20.0,
                "thickness": 8.0,
            },
            "plate": {
                "shape": "rectangle",
                "length": 200.0,
                "width": 150.0,
                "hole_diameter": 8.0,
                "hole_spacing_x": 50.0,
                "hole_spacing_y": 50.0,
            },
            "washer": {
                "shape": "circle",
                "outer_diameter": 20.0,
                "inner_diameter": 8.0,
            },
            "flange": {
                "shape": "circle",
                "outer_diameter": 200.0,
                "inner_diameter": 100.0,
                "bolt_circle_diameter": 160.0,
                "bolt_holes": 8,
                "bolt_diameter": 12.0,
            },
            "base_plate": {
                "shape": "rectangle",
                "length": 200.0,
                "width": 150.0,
                "hole_pattern": "rectangular",
                "hole_diameter": 8.0,
                "hole_spacing_x": 50.0,
                "hole_spacing_y": 50.0,
                "edge_distance": 25.0,
            }
        }
        
        # Also check for generic "bracket" if specific type not found
        if self.part_type not in defaults_map and "bracket" in self.part_type:
            # Default bracket settings
            return defaults_map.get("bracket", {})
        
        return defaults_map.get(self.part_type, {})
    
    def generate_geometry(self) -> Tuple[Polygon, Dict[str, Any]]:
        """Generate the 2D geometry for the part."""
        shape_type = self.params.get("shape", "rectangle")
        
        # Generate base shape
        if shape_type == "rectangle":
            geometry = self._create_rectangle()
        elif shape_type == "circle":
            geometry = self._create_circle()
        elif shape_type == "triangle":
            geometry = self._create_triangle()
        elif shape_type == "L":
            geometry = self._create_l_shape()
        elif shape_type == "T":
            geometry = self._create_t_shape()
        elif shape_type == "hexagon":
            geometry = self._create_hexagon()
        elif shape_type == "ellipse":
            geometry = self._create_ellipse()
        else:
            # Default to rectangle if unknown shape
            geometry = self._create_rectangle()
        
        # Apply features (holes, slots, fillets)
        geometry = self._apply_features(geometry)
        
        # Calculate geometry data
        geometry_data = self._calculate_geometry_data(geometry)
        
        return geometry, geometry_data
    
    def _create_rectangle(self) -> Polygon:
        """Create a rectangular geometry."""
        width = self.params.get("width", 100.0)
        height = self.params.get("height", 100.0)
        
        # Create rectangle centered at origin
        coords = [
            (-width/2, -height/2),
            (width/2, -height/2),
            (width/2, height/2),
            (-width/2, height/2),
            (-width/2, -height/2)
        ]
        
        return Polygon(coords)
    
    def _create_circle(self) -> Polygon:
        """Create a circular geometry."""
        radius = self.params.get("radius")
        if radius is None:
            diameter = self.params.get("diameter", self.params.get("outer_diameter", 100.0))
            radius = diameter / 2
        
        # Create circle using polygon approximation
        num_points = 64
        angles = np.linspace(0, 2*math.pi, num_points, endpoint=False)
        coords = [(radius * math.cos(a), radius * math.sin(a)) for a in angles]
        coords.append(coords[0])  # Close the polygon
        
        circle = Polygon(coords)
        
        # Add inner hole if specified
        inner_diameter = self.params.get("inner_diameter")
        if inner_diameter is not None and inner_diameter > 0:
            inner_radius = inner_diameter / 2
            inner_coords = [(inner_radius * math.cos(a), inner_radius * math.sin(a)) for a in angles]
            inner_coords.append(inner_coords[0])
            inner_circle = Polygon(inner_coords)
            circle = circle.difference(inner_circle)
        
        return circle
    
    def _create_triangle(self) -> Polygon:
        """Create a triangular geometry (default: right triangle)."""
        width = self.params.get("width", 100.0)
        height = self.params.get("height", 80.0)
        
        # Create right triangle
        coords = [
            (0, 0),
            (width, 0),
            (0, height),
            (0, 0)
        ]
        
        return Polygon(coords)
    
    def _create_l_shape(self) -> Polygon:
        """Create an L-shaped geometry."""
        width = self.params.get("width", 120.0)
        height = self.params.get("height", 100.0)
        leg_length = self.params.get("leg_length", 80.0)
        leg_width = self.params.get("leg_width", 20.0)
        
        # Create L-shape
        coords = [
            (0, 0),
            (width, 0),
            (width, leg_width),
            (leg_width, leg_width),
            (leg_width, height),
            (0, height),
            (0, 0)
        ]
        
        return Polygon(coords)
    
    def _create_t_shape(self) -> Polygon:
        """Create a T-shaped geometry."""
        width = self.params.get("width", 120.0)
        height = self.params.get("height", 100.0)
        stem_width = self.params.get("stem_width", 30.0)
        flange_height = self.params.get("flange_height", 30.0)
        
        # Center the T-shape around origin
        half_width = width / 2
        half_height = height / 2
        half_stem = stem_width / 2
        
        # Create T-shape centered at origin
        coords = [
            (-half_width, half_height - flange_height),  # Top-left of flange
            (-half_width, half_height),                   # Top-left corner
            (half_width, half_height),                    # Top-right corner
            (half_width, half_height - flange_height),    # Top-right of flange
            (half_stem, half_height - flange_height),     # Right side of stem top
            (half_stem, -half_height),                    # Right side of stem bottom
            (-half_stem, -half_height),                   # Left side of stem bottom
            (-half_stem, half_height - flange_height),    # Left side of stem top
            (-half_width, half_height - flange_height)    # Back to start
        ]
        
        return Polygon(coords)
    
    def _create_hexagon(self) -> Polygon:
        """Create a hexagonal geometry."""
        size = self.params.get("size", 50.0)  # Distance from center to vertex
        
        angles = [i * math.pi / 3 for i in range(6)]
        coords = [(size * math.cos(a), size * math.sin(a)) for a in angles]
        coords.append(coords[0])
        
        return Polygon(coords)
    
    def _create_ellipse(self) -> Polygon:
        """Create an elliptical geometry."""
        width = self.params.get("width", 100.0) / 2  # semi-major axis
        height = self.params.get("height", 60.0) / 2  # semi-minor axis
        
        num_points = 64
        angles = np.linspace(0, 2*math.pi, num_points, endpoint=False)
        coords = [(width * math.cos(a), height * math.sin(a)) for a in angles]
        coords.append(coords[0])
        
        return Polygon(coords)
    
    def _apply_features(self, geometry: Polygon) -> Polygon:
        """Apply features like holes, slots, fillets to the geometry."""
        # Apply corner radius/fillets
        corner_radius = self.params.get("corner_radius", 0)
        if corner_radius is not None and corner_radius > 0:
            geometry = geometry.buffer(-corner_radius/2).buffer(corner_radius/2)
        
        # Apply holes
        geometry = self._apply_holes(geometry)
        
        # Apply slots
        geometry = self._apply_slots(geometry)
        
        return geometry
    
    def _apply_holes(self, geometry: Polygon) -> Polygon:
        """Apply holes to the geometry."""
        hole_diameter = self.params.get("hole_diameter")
        if not hole_diameter:
            return geometry
        
        holes = []
        hole_radius = hole_diameter / 2
        
        # Different hole patterns based on part type and parameters
        if self.part_type in ["bracket", "l_bracket", "angle"]:
            holes.extend(self._create_bracket_holes(hole_radius))
        elif self.part_type == "t_bracket":
            holes.extend(self._create_t_bracket_holes(hole_radius))
        elif self.part_type in ["plate", "base_plate"]:
            holes.extend(self._create_plate_holes(hole_radius))
        elif self.part_type == "flange":
            holes.extend(self._create_flange_holes(hole_radius))
        elif self.part_type == "gusset":
            holes.extend(self._create_gusset_holes(hole_radius))
        else:
            # No default holes for unknown types
            pass
        
        # Remove holes from geometry
        for hole in holes:
            if geometry.contains(hole) or geometry.overlaps(hole):
                geometry = geometry.difference(hole)
        
        return geometry
    
    def _create_bracket_holes(self, radius: float) -> List[Polygon]:
        """Create holes for bracket-type parts."""
        holes = []
        spacing = self.params.get("hole_spacing", 40.0)
        
        # Two holes along each leg of the bracket
        leg_length = self.params.get("leg_length", 80.0)
        leg_width = self.params.get("leg_width", 20.0)
        
        # Horizontal leg holes
        holes.append(Point(spacing, leg_width/2).buffer(radius))
        holes.append(Point(leg_length - spacing, leg_width/2).buffer(radius))
        
        # Vertical leg holes  
        holes.append(Point(leg_width/2, spacing).buffer(radius))
        holes.append(Point(leg_width/2, leg_length - spacing).buffer(radius))
        
        return holes
    
    def _create_plate_holes(self, radius: float) -> List[Polygon]:
        """Create holes for plate-type parts."""
        holes = []
        
        spacing_x = self.params.get("hole_spacing_x", 50.0)
        spacing_y = self.params.get("hole_spacing_y", 50.0)
        edge_distance = self.params.get("edge_distance", 25.0)
        
        width = self.params.get("width", self.params.get("length", 200.0))
        height = self.params.get("height", 150.0)
        
        # Create grid of holes
        x_start = -width/2 + edge_distance
        y_start = -height/2 + edge_distance
        x_end = width/2 - edge_distance
        y_end = height/2 - edge_distance
        
        x = x_start
        while x <= x_end:
            y = y_start
            while y <= y_end:
                holes.append(Point(x, y).buffer(radius))
                y += spacing_y
            x += spacing_x
        
        return holes
    
    def _create_flange_holes(self, radius: float) -> List[Polygon]:
        """Create bolt holes for flange-type parts."""
        holes = []
        
        bolt_circle_diameter = self.params.get("bolt_circle_diameter", 160.0)
        bolt_holes = self.params.get("bolt_holes", 8)
        bolt_circle_radius = bolt_circle_diameter / 2
        
        for i in range(bolt_holes):
            angle = 2 * math.pi * i / bolt_holes
            x = bolt_circle_radius * math.cos(angle)
            y = bolt_circle_radius * math.sin(angle)
            holes.append(Point(x, y).buffer(radius))
        
        return holes
    
    def _create_t_bracket_holes(self, radius: float) -> List[Polygon]:
        """Create holes for T-bracket parts."""
        holes = []
        spacing = self.params.get("hole_spacing", 30.0)
        width = self.params.get("width", 150.0)
        height = self.params.get("height", 120.0)
        stem_width = self.params.get("stem_width", 30.0)
        flange_height = self.params.get("flange_height", 30.0)
        
        half_width = width / 2
        half_height = height / 2
        
        # Holes along the top flange (centered coordinates)
        flange_y = half_height - flange_height/2
        holes.append(Point(-half_width + spacing, flange_y).buffer(radius))
        holes.append(Point(half_width - spacing, flange_y).buffer(radius))
        
        # Holes along the stem (centered coordinates)
        holes.append(Point(0, 0).buffer(radius))  # Center hole
        holes.append(Point(0, -half_height + spacing).buffer(radius))  # Bottom hole
        
        return holes
    
    def _create_gusset_holes(self, radius: float) -> List[Polygon]:
        """Create holes for gusset parts."""
        holes = []
        width = self.params.get("width", 100.0)
        height = self.params.get("height", 80.0)
        edge_distance = self.params.get("edge_distance", 20.0)
        
        # Three holes at the corners of the triangle
        holes.append(Point(edge_distance, edge_distance).buffer(radius))
        holes.append(Point(width - edge_distance, edge_distance).buffer(radius))
        holes.append(Point(edge_distance, height - edge_distance).buffer(radius))
        
        return holes
    
    def _apply_slots(self, geometry: Polygon) -> Polygon:
        """Apply slots to the geometry."""
        slot_length = self.params.get("slot_length")
        slot_width = self.params.get("slot_width")
        
        if not (slot_length and slot_width):
            return geometry
        
        # Create slot as rounded rectangle
        slot = self._create_slot(0, 0, slot_length, slot_width)
        geometry = geometry.difference(slot)
        
        return geometry
    
    def _create_slot(self, x: float, y: float, length: float, width: float) -> Polygon:
        """Create a slot (rounded rectangle) at specified position."""
        radius = width / 2
        half_length = (length - width) / 2
        
        # Create slot as rectangle with rounded ends
        rect_coords = [
            (x - half_length, y - radius),
            (x + half_length, y - radius),
            (x + half_length, y + radius),
            (x - half_length, y + radius),
            (x - half_length, y - radius)
        ]
        
        slot = Polygon(rect_coords)
        
        # Add rounded ends
        left_circle = Point(x - half_length, y).buffer(radius)
        right_circle = Point(x + half_length, y).buffer(radius)
        
        slot = unary_union([slot, left_circle, right_circle])
        
        return slot
    
    def _calculate_geometry_data(self, geometry: Polygon) -> Dict[str, Any]:
        """Calculate geometric properties of the part."""
        bounds = geometry.bounds
        area = geometry.area
        
        # Extract coordinate arrays for export
        outline_coords = []
        holes = []
        
        if hasattr(geometry, 'exterior'):
            # Main outline coordinates
            outline_coords = list(geometry.exterior.coords)
            
            # Interior holes (if any)
            if hasattr(geometry, 'interiors'):
                for interior in geometry.interiors:
                    holes.append(list(interior.coords))
        
        return {
            "area": area,
            "perimeter": geometry.length,
            "bounds": [bounds[0], bounds[1], bounds[2], bounds[3]],  # Format expected by FileExporter
            "width": bounds[2] - bounds[0],
            "height": bounds[3] - bounds[1],
            "centroid": {
                "x": geometry.centroid.x,
                "y": geometry.centroid.y
            },
            # For FileExporter compatibility
            "outline_coords": outline_coords,
            "holes": holes,
            "hole_centers": [],  # Will be populated if holes are created
            "parameters": self.params
        }
    
    def calculate_mass(self, area: float) -> float:
        """Calculate the mass of the part."""
        # Material densities (kg/m³)
        densities = {
            "steel": 7850,
            "aluminum": 2700,
            "titanium": 4500,
            "brass": 8500,
            "copper": 8960,
        }
        
        material = self.params.get("material", "steel").lower()
        density = densities.get(material, 7850)  # Default to steel
        thickness = self.params.get("thickness", 5.0)
        
        # Convert area from mm² to m², thickness from mm to m
        area_m2 = area / 1_000_000
        thickness_m = thickness / 1000
        
        volume_m3 = area_m2 * thickness_m
        mass_kg = volume_m3 * density
        
        return mass_kg
    
    def _calculate_geometry_info(self, geometry: Polygon):
        """Calculate detailed geometry information for the generated part."""
        from app.schemas.common import GeometryInfo, Point2D
        
        bounds = geometry.bounds
        centroid = geometry.centroid
        
        return GeometryInfo(
            area=geometry.area,
            perimeter=geometry.length,
            centroid=Point2D(x=centroid.x, y=centroid.y),
            bounding_box=(
                Point2D(x=bounds[0], y=bounds[1]),  # min point
                Point2D(x=bounds[2], y=bounds[3])   # max point
            )
        )
