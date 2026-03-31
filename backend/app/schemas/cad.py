from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from .common import Point2D

class CadParameters(BaseModel):
    """Parameters defining a CAD part."""
    type: str = Field(..., description="Type of part (e.g., plate, flange, gusset)")
    values: Dict[str, Any] = Field(..., description="Dictionary of parameters")

class CadIntent(BaseModel):
    """User intent derived from natural language."""
    action: Literal["create", "modify", "checkout"] = Field(..., description="Action to perform")
    target_id: Optional[str] = Field(None, description="ID of the part to modify or checkout")
    parameters: CadParameters = Field(..., description="Parameters extracted from text")
    rationale: Optional[str] = Field(None, description="Explanation for the extracted parameters")

class CadState(BaseModel):
    """Current state of a CAD design."""
    part_id: str = Field(..., description="Unique identifier for this part state")
    part_type: str = Field(..., description="Type of part")
    parameters: CadParameters = Field(..., description="Current parameters")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context (e.g., material)")

class HoleFeature(BaseModel):
    """A hole feature within a part."""
    id: str = Field(..., description="Unique ID for this hole")
    center: Point2D = Field(..., description="Center coordinates")
    diameter: float = Field(..., description="Hole diameter")

class PartGeometry(BaseModel):
    """Canonical geometric representation of a part."""
    outer_boundary: List[Point2D] = Field(..., description="Coordinates forming the outer perimeter")
    holes: List[HoleFeature] = Field(default_factory=list, description="Hole features")
    material: str = Field(default="steel", description="Material of the part")
    thickness: float = Field(..., description="Thickness in mm")
