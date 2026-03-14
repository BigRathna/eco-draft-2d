"""Common schemas used across the application."""

from enum import Enum
from typing import Any, Generic, TypeVar, Optional

from pydantic import BaseModel, Field


T = TypeVar("T")


class Point2D(BaseModel):
    """2D point coordinates."""
    x: float = Field(..., description="X coordinate")
    y: float = Field(..., description="Y coordinate")


class Material(str, Enum):
    """Available materials."""
    STEEL = "steel"
    ALUMINUM = "aluminum"
    STAINLESS_STEEL = "stainless_steel"


class ManufacturingProcess(str, Enum):
    """Available manufacturing processes."""
    LASER_CUTTING = "laser_cutting"
    WATERJET = "waterjet"
    PLASMA = "plasma"


class FileFormat(str, Enum):
    """Supported file formats for export."""
    DXF = "dxf"
    SVG = "svg"
    PDF = "pdf"


class APIResponse(BaseModel, Generic[T]):
    """Generic API response wrapper."""
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Human-readable message")
    data: Optional[T] = Field(None, description="Response data")
    errors: Optional[list[str]] = Field(None, description="List of error messages")


class GeometryInfo(BaseModel):
    """Basic geometry information."""
    area: float = Field(..., description="Area in square units", ge=0)
    perimeter: float = Field(..., description="Perimeter in linear units", ge=0)
    centroid: Point2D = Field(..., description="Geometric centroid")
    bounding_box: tuple[Point2D, Point2D] = Field(..., description="Bounding box (min, max)")


class ValidationResult(BaseModel):
    """Result of a validation check."""
    passed: bool = Field(..., description="Whether the validation passed")
    message: str = Field(..., description="Validation message")
    value: Optional[float] = Field(None, description="Measured value")
    threshold: Optional[float] = Field(None, description="Required threshold")
