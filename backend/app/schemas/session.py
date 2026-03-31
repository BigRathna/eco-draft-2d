from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
import uuid

class SessionEvent(BaseModel):
    """A discrete event in the platform's chronological session."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the event")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the event occurred")
    action_type: str = Field(..., description="Type of action: INIT, GENERATE, CHECK, OPTIMIZE, EXPORT")
    version: str = Field("1.0.0", description="Semantic version of this design state")
    
    # NLP Context
    prompt: Optional[str] = Field(None, description="The raw user prompt that triggered the event")
    rationale: Optional[str] = Field(None, description="The LLM's reasoning for parameter choices")
    
    # Mathematical Context
    parameters: Optional[Dict[str, Any]] = Field(None, description="Engineering bounds and variables applied")
    geometry_data: Optional[Dict[str, Any]] = Field(None, description="Output geometry constraints and coordinates")
    
    # Analytical Context
    metrics: Optional[Dict[str, Any]] = Field(None, description="Mass, stress, or LCA results from analysis")
    
    # Graph Topology
    parent_event_id: Optional[str] = Field(None, description="The event_id from which this state diverged")

class SessionGraph(BaseModel):
    """A complete chronological network mapping of a design session."""
    session_id: str = Field(..., description="Unique identifier for the session")
    start_time: datetime = Field(..., description="When the session initialized")
    events: List[SessionEvent] = Field(default_factory=list, description="Chronological listing of state transitions")
    current_event_id: Optional[str] = Field(None, description="The currently active event in the session")
    current_version: Optional[str] = Field(None, description="The currently active version in the session")
