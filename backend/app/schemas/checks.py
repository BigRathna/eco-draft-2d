"""Schemas for manufacturability checks."""

from typing import List, Optional
from pydantic import BaseModel, Field

from .common import ManufacturingProcess, ValidationResult


class ManufacturabilityCheckRequest(BaseModel):
    """Request for manufacturability check."""
    part_type: str = Field(..., description="Type of part to check")
    geometry_data: dict = Field(..., description="Geometry data (from part generation)")
    manufacturing_process: ManufacturingProcess = Field(..., description="Manufacturing process to validate against")
    thickness: float = Field(..., description="Part thickness in mm", gt=0)
    

class CheckResult(BaseModel):
    """Result of a single manufacturability check."""
    check_type: str = Field(..., description="Type of check performed")
    validation: ValidationResult = Field(..., description="Validation result")
    recommendation: Optional[str] = Field(None, description="Recommendation for improvement")
    

class ManufacturabilityCheckResponse(BaseModel):
    """Response from manufacturability check."""
    overall_passed: bool = Field(..., description="Whether all checks passed")
    manufacturing_process: ManufacturingProcess = Field(..., description="Manufacturing process checked")
    checks: List[CheckResult] = Field(..., description="Individual check results")
    summary: str = Field(..., description="Overall summary of results")
    check_time_ms: float = Field(..., description="Time taken to perform checks in milliseconds")
