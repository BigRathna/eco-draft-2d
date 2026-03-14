"""PDF technical drawing generation using ReportLab."""

import time
import base64
from io import BytesIO
from typing import Dict, Any, List, Tuple

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, A3, letter
from reportlab.lib.units import mm, inch
from reportlab.lib.colors import black, blue, red, green
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from app.schemas.drawing import DrawingRequest, DrawingResponse, TitleBlock


class PDFDrawingGenerator:
    """Generator for PDF technical drawings."""
    
    def __init__(self, request: DrawingRequest):
        """Initialize with drawing request."""
        self.request = request
        self.geometry_data = request.geometry_data
        self.title_block = request.title_block
        
        # Drawing settings
        self.page_size = A4
        self.margin = 20 * mm
        self.title_block_height = 50 * mm
        self.drawing_area_height = self.page_size[1] - 2 * self.margin - self.title_block_height
        self.drawing_area_width = self.page_size[0] - 2 * self.margin
        
    def generate_drawing(self) -> DrawingResponse:
        """Generate PDF technical drawing."""
        start_time = time.time()
        
        # Create PDF in memory
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=self.page_size)
        
        # Draw the part
        self._draw_part(c)
        
        # Draw dimensions if requested
        if self.request.show_dimensions:
            self._draw_dimensions(c)
            
        # Draw title block
        self._draw_title_block(c)
        
        # Finalize PDF
        c.save()
        
        # Get PDF data
        buffer.seek(0)
        pdf_data = buffer.getvalue()
        buffer.close()
        
        # Encode to base64
        content_base64 = base64.b64encode(pdf_data).decode('utf-8')
        
        # Generate filename
        part_type = self.geometry_data.get("type", "part")
        drawing_number = self.title_block.drawing_number.replace("/", "_")
        filename = f"{part_type}_{drawing_number}.pdf"
        
        # Drawing metadata
        drawing_info = {
            "part_type": part_type,
            "drawing_number": self.title_block.drawing_number,
            "scale": self.title_block.scale,
            "material": self.title_block.material.value,
            "thickness": self.title_block.thickness
        }
        
        end_time = time.time()
        generation_time_ms = (end_time - start_time) * 1000
        
        return DrawingResponse(
            filename=filename,
            content_base64=content_base64,
            size_bytes=len(pdf_data),
            page_count=1,
            drawing_info=drawing_info,
            generation_time_ms=generation_time_ms
        )
        
    def _draw_part(self, c: canvas.Canvas) -> None:
        """Draw the part geometry."""
        # Calculate drawing scale and position
        bounds = self.geometry_data.get("bounds", [0, 0, 100, 100])
        part_width = bounds[2] - bounds[0]
        part_height = bounds[3] - bounds[1]
        
        # Calculate scale to fit in drawing area with margin
        scale_x = (self.drawing_area_width * 0.8) / part_width
        scale_y = (self.drawing_area_height * 0.8) / part_height
        scale = min(scale_x, scale_y)
        
        # Center the drawing
        drawing_width = part_width * scale
        drawing_height = part_height * scale
        start_x = self.margin + (self.drawing_area_width - drawing_width) / 2
        start_y = self.margin + self.title_block_height + (self.drawing_area_height - drawing_height) / 2
        
        # Set drawing properties
        c.setStrokeColor(black)
        c.setLineWidth(1.0)
        
        # Draw outline
        outline_coords = self.geometry_data.get("outline_coords", [])
        if outline_coords:
            self._draw_polygon(c, outline_coords, start_x, start_y, scale, bounds)
            
        # Draw holes
        holes = self.geometry_data.get("holes", [])
        for hole_coords in holes:
            self._draw_polygon(c, hole_coords, start_x, start_y, scale, bounds)
            
        # Draw centerlines for holes
        hole_centers = self.geometry_data.get("hole_centers", [])
        if hole_centers:
            c.setStrokeColor(blue)
            c.setLineWidth(0.5)
            c.setDash([2, 2])
            
            for center in hole_centers:
                x = start_x + (center[0] - bounds[0]) * scale
                y = start_y + (center[1] - bounds[1]) * scale
                
                # Draw cross
                cross_size = 5 * mm
                c.line(x - cross_size, y, x + cross_size, y)
                c.line(x, y - cross_size, x, y + cross_size)
                
            c.setDash([])  # Reset to solid line
            
    def _draw_polygon(self, c: canvas.Canvas, coords: List[Tuple[float, float]], 
                     start_x: float, start_y: float, scale: float, bounds: List[float]) -> None:
        """Draw a polygon from coordinates."""
        if len(coords) < 3:
            return
            
        # Create path
        path = c.beginPath()
        
        first_coord = coords[0]
        x = start_x + (first_coord[0] - bounds[0]) * scale
        y = start_y + (first_coord[1] - bounds[1]) * scale
        path.moveTo(x, y)
        
        for coord in coords[1:]:
            x = start_x + (coord[0] - bounds[0]) * scale
            y = start_y + (coord[1] - bounds[1]) * scale
            path.lineTo(x, y)
            
        path.close()
        c.drawPath(path)
        
    def _draw_dimensions(self, c: canvas.Canvas) -> None:
        """Draw dimension annotations."""
        bounds = self.geometry_data.get("bounds", [0, 0, 100, 100])
        part_width = bounds[2] - bounds[0]
        part_height = bounds[3] - bounds[1]
        
        # Calculate drawing parameters (same as _draw_part)
        scale_x = (self.drawing_area_width * 0.8) / part_width
        scale_y = (self.drawing_area_height * 0.8) / part_height
        scale = min(scale_x, scale_y)
        
        drawing_width = part_width * scale
        drawing_height = part_height * scale
        start_x = self.margin + (self.drawing_area_width - drawing_width) / 2
        start_y = self.margin + self.title_block_height + (self.drawing_area_height - drawing_height) / 2
        
        # Set dimension properties
        c.setStrokeColor(red)
        c.setLineWidth(0.5)
        c.setFont("Helvetica", 8)
        
        # Draw overall dimensions
        precision = self.request.dimension_precision
        
        # Width dimension (bottom)
        dim_y = start_y - 10 * mm
        c.line(start_x, dim_y, start_x + drawing_width, dim_y)
        c.line(start_x, dim_y - 2*mm, start_x, dim_y + 2*mm)
        c.line(start_x + drawing_width, dim_y - 2*mm, start_x + drawing_width, dim_y + 2*mm)
        
        width_text = f"{part_width:.{precision}f}"
        text_width = c.stringWidth(width_text, "Helvetica", 8)
        c.drawString(start_x + (drawing_width - text_width) / 2, dim_y - 6*mm, width_text)
        
        # Height dimension (right)
        dim_x = start_x + drawing_width + 10 * mm
        c.line(dim_x, start_y, dim_x, start_y + drawing_height)
        c.line(dim_x - 2*mm, start_y, dim_x + 2*mm, start_y)
        c.line(dim_x - 2*mm, start_y + drawing_height, dim_x + 2*mm, start_y + drawing_height)
        
        height_text = f"{part_height:.{precision}f}"
        c.save()
        c.translate(dim_x + 6*mm, start_y + drawing_height / 2)
        c.rotate(90)
        c.drawString(-c.stringWidth(height_text, "Helvetica", 8) / 2, 0, height_text)
        c.restore()
        
        # Hole dimensions if present
        params = self.geometry_data.get("parameters", {})
        hole_diameter = params.get("hole_diameter", 0.0)
        if hole_diameter > 0:
            hole_text = f"⌀{hole_diameter:.{precision}f}"
            hole_centers = self.geometry_data.get("hole_centers", [])
            
            for i, center in enumerate(hole_centers[:3]):  # Limit to first 3 holes
                x = start_x + (center[0] - bounds[0]) * scale
                y = start_y + (center[1] - bounds[1]) * scale
                
                # Draw leader line
                leader_end_x = x + 15 * mm
                leader_end_y = y + 10 * mm
                c.line(x, y, leader_end_x, leader_end_y)
                c.drawString(leader_end_x + 2*mm, leader_end_y - 2*mm, hole_text)
                
    def _draw_title_block(self, c: canvas.Canvas) -> None:
        """Draw the title block."""
        # Title block position
        tb_x = self.margin
        tb_y = self.margin
        tb_width = self.page_size[0] - 2 * self.margin
        tb_height = self.title_block_height
        
        # Draw border
        c.setStrokeColor(black)
        c.setLineWidth(1.5)
        c.rect(tb_x, tb_y, tb_width, tb_height)
        
        # Internal divisions
        c.setLineWidth(0.5)
        col1_width = tb_width * 0.6
        col2_width = tb_width * 0.4
        
        # Vertical divider
        c.line(tb_x + col1_width, tb_y, tb_x + col1_width, tb_y + tb_height)
        
        # Horizontal dividers in right column
        row_height = tb_height / 5
        for i in range(1, 5):
            c.line(tb_x + col1_width, tb_y + i * row_height, 
                   tb_x + tb_width, tb_y + i * row_height)
            
        # Title (left column)
        c.setFont("Helvetica-Bold", 16)
        title_y = tb_y + tb_height - 20 * mm
        c.drawString(tb_x + 5*mm, title_y, self.title_block.title)
        
        # Part details
        c.setFont("Helvetica", 10)
        details_y = title_y - 8 * mm
        part_details = [
            f"Material: {self.title_block.material.value.upper()}",
            f"Thickness: {self.title_block.thickness}mm",
            f"Scale: {self.title_block.scale}",
        ]
        
        for i, detail in enumerate(part_details):
            c.drawString(tb_x + 5*mm, details_y - i * 5*mm, detail)
            
        # Right column data
        c.setFont("Helvetica", 9)
        right_col_x = tb_x + col1_width + 2*mm
        
        fields = [
            ("Drawing No:", self.title_block.drawing_number),
            ("Part No:", self.title_block.part_number or "N/A"),
            ("Revision:", self.title_block.revision),
            ("Drawn by:", self.title_block.drawn_by),
            ("Date:", self.title_block.date.strftime("%Y-%m-%d")),
        ]
        
        for i, (label, value) in enumerate(fields):
            field_y = tb_y + tb_height - (i + 1) * row_height + row_height/2 + 1*mm
            c.drawString(right_col_x, field_y, f"{label} {value}")
            
        # Company name if provided
        if self.title_block.company:
            c.setFont("Helvetica-Bold", 12)
            company_y = tb_y + tb_height / 2 - 15 * mm
            c.drawString(tb_x + 5*mm, company_y, self.title_block.company)
