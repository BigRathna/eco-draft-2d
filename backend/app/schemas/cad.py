from typing import Dict, Any, List, Optional, Literal, Union
from enum import Enum
from pydantic import BaseModel, Field, model_validator, field_validator
from datetime import datetime
from .common import Point2D

class CadAction(str, Enum):
    """Supported CAD actions."""
    CREATE = "create"
    MODIFY = "modify"
    CHECKOUT = "checkout"

class PartType(str, Enum):
    """Supported mechanical part types."""
    PLATE = "plate"
    GUSSET = "gusset"
    BRACKET = "bracket"
    L_BRACKET = "l_bracket"
    T_BRACKET = "t_bracket"
    WASHER = "washer"
    SPACER = "spacer"
    FLANGE = "flange"
    ANGLE = "angle"

class BasePartParameters(BaseModel):
    """Common parameters for all CAD parts."""
    material: str = Field("steel", description="Material of the part")
    thickness: float = Field(5.0, description="Thickness in mm", gt=0)
    
    @field_validator("material")
    @classmethod
    def validate_material(cls, v: str) -> str:
        allowed = ["steel", "aluminum", "titanium", "brass", "copper"]
        if v.lower() not in allowed:
            pass
        return v.lower()

class PlateParameters(BasePartParameters):
    """Parameters for a rectangular plate."""
    type: Literal[PartType.PLATE] = PartType.PLATE
    width: float = Field(description="Width in mm", gt=0)
    height: float = Field(description="Height in mm", gt=0)
    hole_diameter: Optional[float] = Field(None, description="Diameter of holes in mm", gt=0)
    hole_spacing_x: Optional[float] = Field(None, description="X spacing between holes", gt=0)
    hole_spacing_y: Optional[float] = Field(None, description="Y spacing between holes", gt=0)
    edge_distance: Optional[float] = Field(None, description="Distance from edge to holes", gt=0)

class GussetParameters(BasePartParameters):
    """Parameters for a gusset plate."""
    type: Literal[PartType.GUSSET] = PartType.GUSSET
    width: float = Field(description="Width in mm", gt=0)
    height: float = Field(description="Height in mm", gt=0)
    shape: Literal["triangle", "rectangle"] = Field("triangle", description="Basic shape")
    corner_radius: Optional[float] = Field(5.0, description="Fillet radius", ge=0)

class BracketParameters(BasePartParameters):
    """Parameters for an L or T bracket."""
    type: Literal[PartType.BRACKET, PartType.L_BRACKET, PartType.T_BRACKET, PartType.ANGLE] = PartType.BRACKET
    width: float = Field(description="Overall width", gt=0)
    height: float = Field(description="Overall height", gt=0)
    leg_length: Optional[float] = Field(None, description="Length of the leg", gt=0)
    leg_width: Optional[float] = Field(None, description="Width of the leg", gt=0)
    stem_width: Optional[float] = Field(None, description="Width of the T-bracket stem", gt=0)
    flange_height: Optional[float] = Field(None, description="Height of the T-bracket flange", gt=0)
    hole_diameter: Optional[float] = Field(None, description="Bolt hole diameter", gt=0)
    hole_spacing: Optional[float] = Field(None, description="Distance between holes", gt=0)

class WasherParameters(BasePartParameters):
    """Parameters for a washer or spacer."""
    type: Literal[PartType.WASHER, PartType.SPACER] = PartType.WASHER
    outer_diameter: float = Field(description="Outer diameter", gt=0)
    inner_diameter: float = Field(description="Inner diameter", gt=0)
    
    @model_validator(mode='after')
    def validate_diameters(self) -> 'WasherParameters':
        if self.inner_diameter >= self.outer_diameter:
            raise ValueError("Inner diameter must be smaller than outer diameter")
        return self

class FlangeParameters(BasePartParameters):
    """Parameters for a circular flange."""
    type: Literal[PartType.FLANGE] = PartType.FLANGE
    outer_diameter: float = Field(description="Outer diameter", gt=0)
    inner_diameter: float = Field(description="Inner diameter", gt=0)
    bolt_circle_diameter: float = Field(description="Bolt circle diameter", gt=0)
    bolt_holes: int = Field(8, description="Number of bolt holes", gt=0)
    bolt_diameter: float = Field(12.0, description="Diameter of bolt holes", gt=0)

class CadParameters(BaseModel):
    """Discriminated union for CAD part parameters."""
    __root__: Union[
        PlateParameters, 
        GussetParameters, 
        BracketParameters, 
        WasherParameters, 
        FlangeParameters
    ] = Field(discriminator="type")

class CadIntent(BaseModel):
    """User intent derived from natural language."""
    action: CadAction = Field(description="Action to perform")
    target_id: Optional[str] = Field(None, description="ID of the part to modify or checkout")
    parameters: Any = Field(..., description="Parameters extracted from text (can be raw dict before normalization)")
    # We will use this field for the VALIDATED version
    validated_parameters: Optional[AnyPartParameters] = Field(None, description="Normalized and validated parameters")
    rationale: Optional[str] = Field(None, description="Explanation for the extracted parameters")

class CadState(BaseModel):
    """Current state of a CAD design."""
    part_id: str = Field(description="Unique identifier for this part state")
    part_type: PartType = Field(description="Type of part")
    parameters: AnyPartParameters = Field(description="Current parameters")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context")

class HoleFeature(BaseModel):
    """A hole feature within a part."""
    id: str = Field(description="Unique ID for this hole")
    center: Point2D = Field(description="Center coordinates")
    diameter: float = Field(description="Hole diameter", gt=0)

class PartGeometry(BaseModel):
    """Canonical geometric representation of a part."""
    outer_boundary: List[Point2D] = Field(description="Coordinates forming the outer perimeter")
    holes: List[HoleFeature] = Field(default_factory=list, description="Hole features")
    material: str = Field(default="steel", description="Material of the part")
    thickness: float = Field(description="Thickness in mm", gt=0)

# Type alias for any valid parameter model
AnyPartParameters = Union[
    PlateParameters, 
    GussetParameters, 
    BracketParameters, 
    WasherParameters, 
    FlangeParameters
]
