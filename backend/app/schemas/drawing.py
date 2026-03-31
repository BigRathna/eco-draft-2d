"""Schemas for technical drawing generation."""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

from .common import Material


class TitleBlock(BaseModel):
    """Title block information for technical drawings."""
    title: str = Field(..., description="Drawing title")
    part_number: Optional[str] = Field(None, description="Part number")
    drawing_number: str = Field(..., description="Drawing number")
    revision: str = Field("A", description="Drawing revision")
    scale: str = Field("1:1", description="Drawing scale")
    material: Material = Field(..., description="Part material")
    thickness: float = Field(..., description="Part thickness in mm")
    drawn_by: str = Field("Eco Draft 2D", description="Drawn by")
    checked_by: Optional[str] = Field(None, description="Checked by")
    approved_by: Optional[str] = Field(None, description="Approved by")
    date: datetime = Field(default_factory=datetime.now, description="Drawing date")
    company: str = Field("", description="Company name")
    mass: Optional[float] = Field(None, description="Analyzed part mass in kg")
    max_stress: Optional[float] = Field(None, description="Peak stress in MPa")
    

class DrawingRequest(BaseModel):
    """Request for technical drawing generation."""
    part_type: str = Field(..., description="Type of part to draw")
    geometry_data: dict = Field(..., description="Geometry data (from part generation)")
    title_block: TitleBlock = Field(..., description="Title block information")
    show_dimensions: bool = Field(True, description="Whether to show dimensions")
    show_tolerances: bool = Field(False, description="Whether to show tolerances")
    dimension_precision: int = Field(1, description="Number of decimal places for dimensions", ge=0, le=3)
    

class DrawingResponse(BaseModel):
    """Response from drawing generation."""
    filename: str = Field(..., description="Generated PDF filename")
    content_base64: str = Field(..., description="PDF content encoded as base64")
    size_bytes: int = Field(..., description="File size in bytes")
    page_count: int = Field(..., description="Number of pages in PDF")
    drawing_info: dict = Field(..., description="Drawing metadata")
    generation_time_ms: float = Field(..., description="Time taken to generate drawing in milliseconds")
