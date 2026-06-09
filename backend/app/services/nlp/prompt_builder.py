"""
Modular prompt builder for the CAD Assistant.
Assembles prompts from layers and returns a versioned PromptBundle.
"""
from typing import Dict, Any, List, Optional
from app.services.nlp import prompts
from app.schemas.nlp import PromptLayer, PromptBundle

class PromptBuilder:
    def __init__(self):
        self.layers: List[PromptLayer] = []

    def add_layer(self, name: str, content: str) -> None:
        self.layers.append(PromptLayer(name=name, content=content.strip()))

    def build_bundle(self) -> PromptBundle:
        """Returns a versioned PromptBundle containing all layers."""
        return PromptBundle(
            layers=self.layers, 
            version_string=prompts.PROMPT_VERSION
        )

def create_prompt_builder(
    is_modification: bool = False,
    session_history: Optional[str] = None
) -> PromptBuilder:
    """
    Creates a canonical PromptBuilder with standardized layers.
    Note: Provider-specific formatting is now handled by Adapters.
    """
    builder = PromptBuilder()
    
    # 1. System Layer
    builder.add_layer("system", prompts.SYSTEM_ROLE)
    
    # 2. Task Layer
    if is_modification:
        builder.add_layer("task", prompts.TASK_MODIFY)
    else:
        builder.add_layer("task", prompts.TASK_CREATE)
    
    # 3. Context Layer (History)
    if session_history:
        history_block = f"==== ACTIVE SESSION GRAPH HISTORY ====\n{session_history}\n======================================\n"
        builder.add_layer("history", history_block)
        
    # 4. Constraint Layer
    builder.add_layer("parts", prompts.SUPPORTED_PARTS)
    builder.add_layer("params", prompts.SUPPORTED_PARAMETERS)
    builder.add_layer("units", prompts.UNIT_RULES)
    
    return builder
