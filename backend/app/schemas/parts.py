"""Schemas for part generation."""

from typing import Optional, Union, List, Dict, Any
from abc import ABC, abstractmethod

from pydantic import BaseModel, Field, validator

from .common import Material, FileFormat, GeometryInfo, Point2D
from .checks import ManufacturabilityCheckResponse


class BasePartParams(BaseModel, ABC):
    """Base class for part parameters."""
    material: Material = Field(..., description="Material for the part")
    thickness: float = Field(..., description="Part thickness in mm", gt=0)
    

class GussetParams(BasePartParams):
    """Parameters for gusset plate generation."""
    width: float = Field(..., description="Gusset width in mm", gt=0)
    height: float = Field(..., description="Gusset height in mm", gt=0)
    corner_radius: float = Field(5.0, description="Corner radius in mm", ge=0)
    hole_diameter: Optional[float] = Field(None, description="Central hole diameter in mm", gt=0)
    chamfer_size: float = Field(2.0, description="Chamfer size in mm", ge=0)
    

class BasePlateParams(BasePartParams):
    """Parameters for base plate generation."""
    length: float = Field(..., description="Base plate length in mm", gt=0)
    width: float = Field(..., description="Base plate width in mm", gt=0)
    hole_pattern: str = Field("rectangular", description="Hole pattern type")
    hole_diameter: float = Field(8.0, description="Hole diameter in mm", gt=0)
    hole_spacing_x: float = Field(50.0, description="Hole spacing in X direction in mm", gt=0)
    hole_spacing_y: float = Field(50.0, description="Hole spacing in Y direction in mm", gt=0)
    edge_distance: float = Field(25.0, description="Distance from edge to first hole in mm", gt=0)
    

class GenericPartParams(BaseModel):
    """Generic parameters for any part type."""
    # Common parameters that most parts might have
    material: Optional[str] = Field(None, description="Material for the part")
    thickness: Optional[float] = Field(None, description="Part thickness in mm", gt=0)
    
    # Allow any additional parameters via extra fields
    class Config:
        extra = "allow"  # Allow additional fields not defined in the model


class PartGenerateRequest(BaseModel):
    """Request to generate a part."""
    part_type: str = Field(..., description="Type of part to generate")
    parameters: Union[GussetParams, BasePlateParams, GenericPartParams, Dict[str, Any]] = Field(..., description="Part-specific parameters")
    export_formats: List[FileFormat] = Field(default=[FileFormat.DXF], description="Output file formats")
    
    @validator("parameters", pre=True)
    def validate_parameters(cls, v, values):
        """Validate parameters based on part type."""
        part_type = values.get("part_type")
        
        # For legacy part types, still use specific validation
        if part_type == "gusset" and isinstance(v, dict):
            return GussetParams(**v)
        elif part_type == "base_plate" and isinstance(v, dict):
            return BasePlateParams(**v)
        
        # For new generic part types, accept any parameters
        if isinstance(v, dict):
            return GenericPartParams(**v)
        
        return v


class GeneratedPart(BaseModel):
    """Information about a generated part."""
    part_type: str = Field(..., description="Type of part")
    geometry_info: GeometryInfo = Field(..., description="Geometric properties")
    geometry_data: Dict[str, Any] = Field(default_factory=dict, description="Raw geometric generation data")
    material: Material = Field(..., description="Part material")
    thickness: float = Field(..., description="Part thickness in mm")
    mass: float = Field(..., description="Part mass in kg")
    

class ExportFile(BaseModel):
    """Information about an exported file."""
    format: FileFormat = Field(..., description="File format")
    filename: str = Field(..., description="Generated filename")
    content_base64: str = Field(..., description="File content encoded as base64")
    size_bytes: int = Field(..., description="File size in bytes")
    

class PartGenerateResponse(BaseModel):
    """Response from part generation."""
    part: GeneratedPart = Field(..., description="Generated part information")
    files: List[ExportFile] = Field(..., description="Exported files")
    generation_time_ms: float = Field(..., description="Time taken to generate part in milliseconds")
    checks: Optional[ManufacturabilityCheckResponse] = Field(None, description="Manufacturability check results")
