from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import hashlib

class PromptLayer(BaseModel):
    """A single logical layer of a prompt (e.g., System, Task, Context)."""
    name: str = Field(description="Name of the layer")
    content: str = Field(description="Text content of the layer")

class PromptBundle(BaseModel):
    """A collection of prompt layers with a version string and integrity hash."""
    layers: List[PromptLayer] = Field(description="Ordered list of prompt layers")
    version_string: str = Field(description="Explicit version ID (e.g., 0.1.0)")
    version_hash: Optional[str] = Field(None, description="SHA-256 hash of the bundled content")

    def model_post_init(self, __context: Any) -> None:
        """Automatically compute the version hash if not provided."""
        if not self.version_hash:
            self.version_hash = self.compute_hash()

    def compute_hash(self) -> str:
        """Computes a SHA-256 hash of the normalized layer contents."""
        # Use name-content pairs to ensure order and content are captured
        serialized = "|".join([f"{l.name}:{l.content.strip()}" for l in self.layers])
        return hashlib.sha256(serialized.encode()).hexdigest()[:12]

    def build_full_string(self) -> str:
        """Assembles all layers into a single string."""
        return "\n\n".join([l.content.strip() for l in self.layers])

class PromptVersion(BaseModel):
    """Metadata for a prompt version."""
    version_hash: str
    provider: str
    is_modification: bool
    context_present: bool
