"""
Adapters for converting a canonical PromptBundle into provider-specific formats.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from app.schemas.nlp import PromptBundle
from app.services.nlp import prompts

class BaseProviderAdapter(ABC):
    @abstractmethod
    def transform(self, bundle: PromptBundle, user_message: str) -> Any:
        """Transforms a PromptBundle into the format expected by the provider."""
        pass

class GeminiAdapter(BaseProviderAdapter):
    """Adapter for Google Gemini API (uses string + manual tool appending)."""
    def transform(self, bundle: PromptBundle, user_message: str) -> str:
        # Gemini currently uses a single string combining system and user content 
        # in the way we've implemented _call_gemini
        return bundle.build_full_string()

class OpenAICompatibleAdapter(BaseProviderAdapter):
    """Adapter for OpenAI-compatible APIs (Ollama, OpenRouter)."""
    def transform(self, bundle: PromptBundle, user_message: str) -> List[Dict[str, str]]:
        # Inject JSON schema and JSON-only instructions for these providers
        system_content = bundle.build_full_string()
        system_content += f"\n\n{prompts.JSON_SCHEMA}\n\n{prompts.JSON_ONLY_CRITICAL}"
        
        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_message}
        ]

def get_adapter(provider: str) -> BaseProviderAdapter:
    if provider in ["ollama", "openrouter"]:
        return OpenAICompatibleAdapter()
    return GeminiAdapter()
