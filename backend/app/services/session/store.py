import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from app.schemas.session import SessionEvent, SessionGraph

class SessionTracker:
    """In-memory singleton store for tracking design evolution."""
    
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.start_time = datetime.now()
        self.events = []
        
        # Track the active tip of the branch
        self.current_event_id: Optional[str] = None
        
        # Log initialization
        self.log_event(action_type="INIT")

    def log_event(
        self, 
        action_type: str, 
        prompt: Optional[str] = None, 
        rationale: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        geometry_data: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None,
        parent_id: Optional[str] = None
    ) -> SessionEvent:
        """Log a new systemic edge onto the chronological design graph."""
        
        # Auto-link to the previous tip unless overridden (e.g., reverting to an older design)
        if parent_id is None:
            parent_id = self.current_event_id
            
        version = "1.0.0"
        if parent_id:
            parent_event = next((e for e in self.events if e.event_id == parent_id), None)
            if parent_event:
                if action_type == "GENERATE":
                    v_parts = parent_event.version.split('.')
                    if len(v_parts) >= 2:
                        version = f"{v_parts[0]}.{int(v_parts[1]) + 1}.0"
                    else:
                        version = parent_event.version
                elif action_type in ["CHECK", "OPTIMIZE", "EXPORT"]:
                    v_parts = parent_event.version.split('.')
                    if len(v_parts) >= 3:
                        version = f"{v_parts[0]}.{v_parts[1]}.{int(v_parts[2]) + 1}"
                    else:
                        version = parent_event.version
                else: 
                    version = parent_event.version
            
        event = SessionEvent(
            action_type=action_type,
            version=version,
            prompt=prompt,
            rationale=rationale,
            parameters=parameters,
            geometry_data=geometry_data,
            metrics=metrics,
            parent_event_id=parent_id
        )
        
        self.events.append(event)
        self.current_event_id = event.event_id
        
        print(f"📡 TELEMETRY: Logged [{action_type}] event - Graph nodes: {len(self.events)}")
        return event

    def export_graph(self) -> SessionGraph:
        """Materialize the memory cache into a portable NetworkX-compatible JSON graph."""
        current_event = next((e for e in self.events if e.event_id == self.current_event_id), None)
        return SessionGraph(
            session_id=self.session_id,
            start_time=self.start_time,
            events=self.events,
            current_event_id=self.current_event_id,
            current_version=current_event.version if current_event else None
        )

    def checkout_event(self, identifier: str) -> Optional[SessionEvent]:
        """Move the current HEAD to a historical event to branch off it using event_id or version string."""
        identifier = identifier.replace("ID ", "").replace("v", "").strip()
        for event in reversed(self.events): # Reverse to get the latest match
            if event.event_id.startswith(identifier) or event.version == identifier:
                self.current_event_id = event.event_id
                print(f"📡 TELEMETRY: Checked out event [{event.event_id}] (v{event.version})")
                return event
        return None
        
    def get_context_summary(self) -> str:
        """Return a string summary of the latest events for NLP context."""
        def trim_string(s: str) -> str:
            return s if len(s) <= 100 else s[:100]
            
        summary = []
        for event in self.events:
            if event.action_type in ["GENERATE", "OPTIMIZE", "NLP_INTENT"]:
                param_str = trim_string(str(event.parameters)) if event.parameters else "None"
                summary.append(f"v{event.version} ID {event.event_id[:8]}: [Action: {event.action_type}] Prompt: '{event.prompt}' Params: {param_str}")
                
        # Return last 10
        if len(summary) > 10:
            summary = summary[-10:]
        return "\n".join(summary)

# Initialize a global singleton to track the active server instance
tracker = SessionTracker()
