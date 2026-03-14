"""Schemas for stress analysis."""

from typing import Optional, List, Union, Dict, Any
from pydantic import BaseModel, Field

from .common import Material, Point2D


class LoadCase(BaseModel):
    """Definition of a load case."""
    name: str = Field(..., description="Name of the load case")
    force_x: float = Field(0.0, description="Force in X direction (N)")
    force_y: float = Field(0.0, description="Force in Y direction (N)")
    moment: float = Field(0.0, description="Applied moment (N⋅mm)")
    application_point: Optional[Point2D] = Field(None, description="Point where load is applied")
    

class AnalysisRequest(BaseModel):
    """Request for stress analysis."""
    part_type: str = Field(..., description="Type of part to analyze")
    geometry_data: dict = Field(..., description="Geometry data (from part generation)")
    material: Union[Material, str, Dict[str, Any]] = Field(..., description="Part material (enum, string, or object)")
    thickness: float = Field(..., description="Part thickness in mm", gt=0)
    load_cases: List[LoadCase] = Field(..., description="Load cases to analyze", min_items=1)
    

class StressResult(BaseModel):
    """Result of stress analysis for a load case."""
    load_case_name: str = Field(..., description="Name of the load case")
    max_stress: float = Field(..., description="Maximum stress (Pa)")
    stress_location: Point2D = Field(..., description="Location of maximum stress")
    net_section_stress: float = Field(..., description="Net section stress (Pa)")
    safety_factor: float = Field(..., description="Safety factor based on yield strength")
    margin_of_safety: float = Field(..., description="Margin of safety")
    passed: bool = Field(..., description="Whether stress levels are acceptable")
    

class AnalysisResponse(BaseModel):
    """Response from stress analysis."""
    material: Union[Material, str] = Field(..., description="Material analyzed")
    yield_strength: float = Field(..., description="Material yield strength (Pa)")
    results: List[StressResult] = Field(..., description="Analysis results for each load case")
    critical_load_case: Optional[str] = Field(None, description="Most critical load case")
    recommendations: List[str] = Field(default_factory=list, description="Design recommendations")
    analysis_time_ms: float = Field(..., description="Time taken for analysis in milliseconds")
