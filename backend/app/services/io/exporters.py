"""File exporters for DXF and SVG formats."""

import base64
from typing import Dict, Any, List, Tuple
from io import StringIO, BytesIO

import ezdxf
import svgwrite
from shapely.geometry import Polygon

from app.schemas.common import FileFormat
from app.schemas.parts import ExportFile


class FileExporter:
    """File exporter for multiple CAD formats."""
    
    def __init__(self, geometry_data: Dict[str, Any]):
        """Initialize with geometry data."""
        self.geometry_data = geometry_data
        
    def export_formats(self, formats: List[FileFormat], part_type: str = "part") -> List[ExportFile]:
        """Export geometry to multiple file formats."""
        exported_files = []
        
        for format_type in formats:
            if format_type == FileFormat.DXF:
                file_data = self._export_dxf(part_type)
            elif format_type == FileFormat.SVG:
                file_data = self._export_svg(part_type)
            elif format_type == FileFormat.PDF:
                # PDF export is handled by PDFDrawingGenerator
                continue
            else:
                continue
                
            if file_data:
                exported_files.append(file_data)
                
        return exported_files
        
    def _export_dxf(self, part_type: str) -> ExportFile:
        """Export geometry to DXF format."""
        # Create new DXF document
        doc = ezdxf.new("R2010")  # AutoCAD 2010
        msp = doc.modelspace()
        
        # Set up layers
        doc.layers.new(name="OUTLINE", dxfattribs={"color": 7})  # White
        doc.layers.new(name="HOLES", dxfattribs={"color": 3})    # Green
        doc.layers.new(name="CENTERLINES", dxfattribs={"color": 4, "linetype": "CENTER"})  # Cyan
        
        # Draw outline
        outline_coords = self.geometry_data.get("outline_coords", [])
        if outline_coords and len(outline_coords) > 2:
            # Convert to list of (x, y) tuples, removing duplicate last point if present
            points = [(coord[0], coord[1]) for coord in outline_coords[:-1]]
            msp.add_lwpolyline(points, close=True, dxfattribs={"layer": "OUTLINE"})
            
        # Draw holes
        holes = self.geometry_data.get("holes", [])
        for hole_coords in holes:
            if len(hole_coords) > 2:
                points = [(coord[0], coord[1]) for coord in hole_coords[:-1]]
                msp.add_lwpolyline(points, close=True, dxfattribs={"layer": "HOLES"})
                
        # Draw centerlines for holes
        hole_centers = self.geometry_data.get("hole_centers", [])
        params = self.geometry_data.get("parameters", {})
        hole_diameter = params.get("hole_diameter", 0.0)
        
        if hole_centers and hole_diameter is not None and hole_diameter > 0:
            cross_size = hole_diameter * 0.75  # Cross size relative to hole
            
            for center in hole_centers:
                x, y = center[0], center[1]
                
                # Horizontal centerline
                msp.add_line((x - cross_size, y), (x + cross_size, y), 
                           dxfattribs={"layer": "CENTERLINES"})
                # Vertical centerline  
                msp.add_line((x, y - cross_size), (x, y + cross_size),
                           dxfattribs={"layer": "CENTERLINES"})
                           
        # Add text annotations
        bounds = self.geometry_data.get("bounds", [0, 0, 100, 100])
        text_height = (bounds[2] - bounds[0]) * 0.05  # 5% of part width
        
        msp.add_text(
            f"Part Type: {part_type.upper()}",
            dxfattribs={
                "layer": "OUTLINE",
                "height": text_height,
                "insert": (bounds[0], bounds[3] + text_height * 1.5),
            }
        )
        
        # Material info if available
        material = params.get("material", "")
        if material:
            msp.add_text(
                f"Material: {material.upper()}",
                dxfattribs={
                    "layer": "OUTLINE", 
                    "height": text_height,
                    "insert": (bounds[0], bounds[3] + text_height * 0.5),
                }
            )
            
        # Export to string
        stream = StringIO()
        doc.write(stream)
        dxf_content = stream.getvalue()
        stream.close()
        
        # Convert to bytes and encode
        dxf_bytes = dxf_content.encode('utf-8')
        content_base64 = base64.b64encode(dxf_bytes).decode('utf-8')
        
        return ExportFile(
            format=FileFormat.DXF,
            filename=f"{part_type}.dxf",
            content_base64=content_base64,
            size_bytes=len(dxf_bytes)
        )
        
    def _export_svg(self, part_type: str) -> ExportFile:
        """Export geometry to SVG format."""
        # Calculate drawing bounds
        bounds = self.geometry_data.get("bounds", [0, 0, 100, 100])
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]
        
        # Add larger margins for better presentation
        margin = max(width, height) * 0.4  # Increased margin for better spacing
        svg_width = max(width + 2 * margin, 250)  # Ensure minimum bounding width for the label block
        svg_height = height + 3 * margin  # Extra space at bottom for labels
        
        # Create SVG drawing with proper viewBox
        dwg = svgwrite.Drawing(
            filename=f"{part_type}.svg",
            size=(f"{svg_width}mm", f"{svg_height}mm"),
            viewBox=f"{bounds[0] - margin} {bounds[1] - margin} {svg_width} {svg_height}"
        )
        
        # Add white background
        dwg.add(dwg.rect(
            insert=(bounds[0] - margin, bounds[1] - margin),
            size=(svg_width, svg_height),
            fill='white'
        ))
        
        # Define improved styles
        dwg.defs.add(dwg.style("""
            .outline { fill: none; stroke: #2c3e50; stroke-width: 1.5; }
            .holes { fill: white; stroke: #e74c3c; stroke-width: 1; }
            .centerlines { stroke: #3498db; stroke-width: 0.5; stroke-dasharray: 4,2; opacity: 0.5; }
            .dimensions { fill: #27ae60; stroke: none; font-family: 'Segoe UI', Arial, sans-serif; font-size: 5px; }
            .title { fill: #2c3e50; font-family: 'Segoe UI', Arial, sans-serif; font-size: 8px; font-weight: bold; }
            .subtitle { fill: #7f8c8d; font-family: 'Segoe UI', Arial, sans-serif; font-size: 6px; }
            .grid { stroke: #ecf0f1; stroke-width: 0.1; }
        """))
        
        # Add subtle grid background
        grid_spacing = 10
        for x in range(int(bounds[0] - margin), int(bounds[2] + margin), grid_spacing):
            dwg.add(dwg.line((x, bounds[1] - margin), (x, bounds[3] + margin), class_="grid"))
        for y in range(int(bounds[1] - margin), int(bounds[3] + margin), grid_spacing):
            dwg.add(dwg.line((bounds[0] - margin, y), (bounds[2] + margin, y), class_="grid"))
        
        # Create main group for the part
        part_group = dwg.g(id='part')
        
        # Draw outline with shadow effect
        shadow_offset = 1
        outline_coords = self.geometry_data.get("outline_coords", [])
        if outline_coords and len(outline_coords) > 2:
            points = []
            for coord in outline_coords[:-1]:  # Skip duplicate last point
                points.append((coord[0], coord[1]))
            
            # Add shadow
            shadow_points = [(p[0] + shadow_offset, p[1] + shadow_offset) for p in points]
            part_group.add(dwg.polygon(shadow_points, fill='#95a5a6', opacity=0.3))
            
            # Add main outline
            part_group.add(dwg.polygon(points, class_="outline", fill='#ecf0f1'))
            
        # Draw holes with better visibility
        holes = self.geometry_data.get("holes", [])
        for hole_coords in holes:
            if len(hole_coords) > 2:
                points = []
                for coord in hole_coords[:-1]:
                    points.append((coord[0], coord[1]))
                part_group.add(dwg.polygon(points, class_="holes"))
        
        dwg.add(part_group)
                
        # Draw centerlines (optional, subtle)
        hole_centers = self.geometry_data.get("hole_centers", [])
        params = self.geometry_data.get("parameters", {})
        hole_diameter = params.get("hole_diameter", 0.0)
        
        if hole_centers and hole_diameter is not None and hole_diameter > 0:
            cross_size = hole_diameter * 0.6  # Smaller crosses
            
            centerline_group = dwg.g(id='centerlines')
            for center in hole_centers:
                x, y = center[0], center[1]
                
                # Horizontal centerline
                centerline_group.add(dwg.line((x - cross_size, y), (x + cross_size, y), class_="centerlines"))
                # Vertical centerline
                centerline_group.add(dwg.line((x, y - cross_size), (x, y + cross_size), class_="centerlines"))
            dwg.add(centerline_group)
                
        # Add dimension lines and arrows
        dim_offset = margin * 0.3
        arrow_size = 2
        
        # Horizontal dimension
        dim_y = bounds[1] - dim_offset
        dwg.add(dwg.line((bounds[0], dim_y), (bounds[2], dim_y), stroke='#27ae60', stroke_width=0.5))
        # Arrows
        dwg.add(dwg.polygon([
            (bounds[0], dim_y),
            (bounds[0] + arrow_size, dim_y - arrow_size/2),
            (bounds[0] + arrow_size, dim_y + arrow_size/2)
        ], fill='#27ae60'))
        dwg.add(dwg.polygon([
            (bounds[2], dim_y),
            (bounds[2] - arrow_size, dim_y - arrow_size/2),
            (bounds[2] - arrow_size, dim_y + arrow_size/2)
        ], fill='#27ae60'))
        # Dimension text
        dwg.add(dwg.text(
            f"{width:.1f} mm",
            insert=(bounds[0] + width/2, dim_y - 2),
            text_anchor="middle",
            class_="dimensions"
        ))
        
        # Vertical dimension
        dim_x = bounds[2] + dim_offset
        dwg.add(dwg.line((dim_x, bounds[1]), (dim_x, bounds[3]), stroke='#27ae60', stroke_width=0.5))
        # Arrows
        dwg.add(dwg.polygon([
            (dim_x, bounds[1]),
            (dim_x - arrow_size/2, bounds[1] + arrow_size),
            (dim_x + arrow_size/2, bounds[1] + arrow_size)
        ], fill='#27ae60'))
        dwg.add(dwg.polygon([
            (dim_x, bounds[3]),
            (dim_x - arrow_size/2, bounds[3] - arrow_size),
            (dim_x + arrow_size/2, bounds[3] - arrow_size)
        ], fill='#27ae60'))
        # Dimension text
        dwg.add(dwg.text(
            f"{height:.1f} mm",
            insert=(dim_x + 3, bounds[1] + height/2),
            text_anchor="middle",
            transform=f"rotate(90 {dim_x + 3} {bounds[1] + height/2})",
            class_="dimensions"
        ))
        
        # Add title block at bottom with more spacing
        title_y = bounds[3] + margin * 1.5
        
        # Title background
        dwg.add(dwg.rect(
            insert=(bounds[0] - margin * 0.5, title_y - 15),
            size=(svg_width - margin, 30),
            fill='#ecf0f1',
            stroke='#bdc3c7',
            stroke_width=0.5
        ))
        
        # Part type - properly format the name
        # Remove single letter prefixes like 't_', 'l_', etc.
        cleaned_type = part_type
        if len(part_type) > 2 and part_type[1] == '_':
            cleaned_type = part_type[2:]
        
        # Replace underscores and dashes with spaces and title case
        formatted_name = cleaned_type.replace('_', ' ').replace('-', ' ').title()
        
        # Fix specific part names for consistency
        if 'gusset' in part_type.lower():
            formatted_name = 'Gusset'
        elif 'washer' in part_type.lower():
            formatted_name = 'Washer'
        elif 'flange' in part_type.lower():
            formatted_name = 'Flange'
        elif 'bracket' in part_type.lower():
            formatted_name = 'Bracket'
        elif 'plate' in part_type.lower():
            formatted_name = 'Plate'
            
        dwg.add(dwg.text(
            formatted_name,
            insert=(bounds[0], title_y),
            class_="title"
        ))
        
        # Material and other info
        material = params.get("material", "")
        thickness = params.get("thickness", 0)
        info_text = []
        
        if material:
            if isinstance(material, dict):
                material_name = material.get('name', 'Steel')
            else:
                material_name = str(material)
            info_text.append(f"Material: {material_name.replace('_', ' ').title()}")
        
        if thickness:
            info_text.append(f"Thickness: {thickness} mm")
        
        # Count actual holes in the geometry
        hole_count = len(holes)
        if hole_count > 0 and hole_diameter is not None and hole_diameter > 0:
            info_text.append(f"Holes: {hole_count} x D{hole_diameter:.1f} mm")
        elif hole_count > 0:
            info_text.append(f"Holes: {hole_count}")
        
        if info_text:
            dwg.add(dwg.text(
                " | ".join(info_text),
                insert=(bounds[0], title_y + 10),
                class_="subtitle"
            ))
            
        # Export to string
        svg_content = dwg.tostring()
        
        # Convert to bytes and encode
        svg_bytes = svg_content.encode('utf-8')
        content_base64 = base64.b64encode(svg_bytes).decode('utf-8')
        
        return ExportFile(
            format=FileFormat.SVG,
            filename=f"{part_type}.svg", 
            content_base64=content_base64,
            size_bytes=len(svg_bytes)
        )
