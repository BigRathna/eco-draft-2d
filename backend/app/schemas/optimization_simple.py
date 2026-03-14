"""Simplified optimization schemas for API responses."""

from pydantic import BaseModel, Field
from typing import Dict, List, Any


class OptimizationPoint(BaseModel):
    """Single optimization point."""
    parameters: Dict[str, float] = Field(..., description="Design parameters")
    objectives: Dict[str, float] = Field(..., description="Objective values")
    

class SimpleOptimizationResponse(BaseModel):
    """Simplified optimization response for frontend."""
    points: List[OptimizationPoint] = Field(..., description="All optimization points")
    pareto_optimal: List[int] = Field(..., description="Indices of Pareto optimal points")
    optimization_time_ms: float = Field(0.0, description="Time taken in milliseconds")
