"""Schemas for Life Cycle Assessment (LCA)."""

from typing import Optional, Dict, Union, Any
from pydantic import BaseModel, Field

from .common import Material


class LCARequest(BaseModel):
    """Request for LCA calculation."""
    part_type: str = Field(..., description="Type of part to analyze")
    geometry_data: dict = Field(..., description="Geometry data (from part generation)")
    material: Union[Material, str, Dict[str, Any]] = Field(..., description="Part material (enum, string, or object)")
    thickness: float = Field(..., description="Part thickness in mm", gt=0)
    quantity: int = Field(1, description="Number of parts", gt=0)
    

class MaterialData(BaseModel):
    """Material properties for LCA calculations."""
    density: float = Field(..., description="Material density (kg/m³)", gt=0)
    co2_factor: float = Field(..., description="CO₂ emission factor (kg CO₂ / kg material)", ge=0)
    recyclability: float = Field(0.0, description="Recyclability factor (0-1)", ge=0, le=1)
    

class LCAResponse(BaseModel):
    """Response from LCA calculation."""
    material: Union[Material, str] = Field(..., description="Material analyzed")
    material_data: MaterialData = Field(..., description="Material properties used")
    area: float = Field(..., description="Part area (mm²)")
    volume: float = Field(..., description="Part volume (mm³)")
    mass: float = Field(..., description="Part mass (kg)")
    total_mass: float = Field(..., description="Total mass for quantity (kg)")
    co2_emissions: float = Field(..., description="CO₂ emissions (kg CO₂)")
    co2_per_part: float = Field(..., description="CO₂ emissions per part (kg CO₂)")
    sustainability_rating: str = Field(..., description="Sustainability rating (A-F)")
    recommendations: list[str] = Field(default_factory=list, description="Sustainability recommendations")
    calculation_time_ms: float = Field(..., description="Time taken for calculation in milliseconds")
