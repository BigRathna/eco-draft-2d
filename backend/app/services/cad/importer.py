import ezdxf
import io
import math
from typing import Dict, Any, List, Tuple, Union
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union

class DxfImporter:
    """Imports DXF files and converts them into the native geometry_data format."""
    
    def __init__(self, dxf_content: Union[bytes, str]):
        """Initialize with raw DXF file bytes or strings."""
        if isinstance(dxf_content, str):
            self.doc = ezdxf.read(io.StringIO(dxf_content))
        else:
            try:
                # Try decoding as text first; DXF is standard ASCII
                text_content = dxf_content.decode('utf-8')
                self.doc = ezdxf.read(io.StringIO(text_content))
            except UnicodeDecodeError:
                # Fallback to binary Stream for newer DWG/DXF schemas
                self.doc = ezdxf.read(io.BytesIO(dxf_content))
        
        self.msp = self.doc.modelspace()
        
    def _extract_shapes(self) -> Tuple[List[Polygon], List[Polygon]]:
        """
        Extract out the main perimeter (outer bound) and any internal circular holes.
        Returns (outer_polygons, inner_hole_polygons).
        """
        import ezdxf.path
        from shapely.ops import polygonize
        
        lines = []
        polygons = []
        circles = []
        
        for entity in self.msp:
            dxftype = entity.dxftype()
            
            if dxftype == 'CIRCLE':
                center = Point(entity.dxf.center.x, entity.dxf.center.y)
                radius = entity.dxf.radius
                circles.append(center.buffer(radius))
                continue
                
            if dxftype in ['LINE', 'LWPOLYLINE', 'POLYLINE', 'ARC', 'SPLINE', 'ELLIPSE']:
                try:
                    path = ezdxf.path.make_path(entity)
                    # .has_sub_paths ensures multi-path extraction
                    paths_to_process = path.sub_paths() if path.has_sub_paths else [path]
                    
                    for sub in paths_to_process:
                        points = [(pt.x, pt.y) for pt in sub.flattening(distance=0.1)]
                        if len(points) > 1:
                            if sub.is_closed and points[0] != points[-1]:
                                points.append(points[0])
                            lines.append(LineString(points))
                except Exception:
                    pass
                    
        # Construct all connected nodes into unified polygon representations
        if lines:
            merged_lines = unary_union(lines)
            for poly in polygonize(merged_lines):
                if not poly.is_valid:
                    poly = poly.buffer(0)
                polygons.append(poly)
                
        all_shapes = polygons + circles
        
        if not all_shapes:
            if lines:
                return [unary_union(lines).envelope], []
            return [Polygon([(0,0), (100,0), (100,100), (0,100)])], []
            
        all_shapes.sort(key=lambda p: p.area if isinstance(p, Polygon) else 0, reverse=True)
        
        outer_bound = all_shapes[0]
        inner_holes = all_shapes[1:]
        
        return [outer_bound], inner_holes

    def extract_geometry(self) -> Dict[str, Any]:
        """Parse DXF vectors and construct formal geometry_data."""
        outer_bounds, holes = self._extract_shapes()
        
        # Merge if multiple bounds were somehow found (take the largest)
        if not outer_bounds:
            main_geometry = Polygon([(0,0), (100,0), (100,100), (0,100)])
        else:
            main_geometry = max(outer_bounds, key=lambda p: p.area if isinstance(p, Polygon) else 0)
            
        # Cleanly subtract holes from the main body
        for hole in holes:
            if isinstance(main_geometry, Polygon) and main_geometry.contains(hole.centroid):
                main_geometry = main_geometry.difference(hole)

        if not isinstance(main_geometry, Polygon):
            main_geometry = main_geometry.envelope

        bounds = main_geometry.bounds
        area = main_geometry.area
        perimeter = main_geometry.length
        
        outline_coords = []
        hole_coords = []
        hole_centers = []
        
        if hasattr(main_geometry, 'exterior'):
            outline_coords = list(main_geometry.exterior.coords)
            if hasattr(main_geometry, 'interiors'):
                for interior in main_geometry.interiors:
                    hole_coords.append(list(interior.coords))
                    
        # Extract explicit hole centers from the un-subtracted circles for UI overlay overlays
        for c in holes:
            hole_centers.append([c.centroid.x, c.centroid.y])

        return {
            "area": area,
            "perimeter": perimeter,
            "bounds": [bounds[0], bounds[1], bounds[2], bounds[3]],
            "width": bounds[2] - bounds[0],
            "height": bounds[3] - bounds[1],
            "centroid": {
                "x": main_geometry.centroid.x,
                "y": main_geometry.centroid.y
            },
            "outline_coords": outline_coords,
            "holes": hole_coords,
            "hole_centers": hole_centers,
            "parameters": {
                "material": "steel",
                "thickness": 5.0,
                "imported": True
            }
        }
