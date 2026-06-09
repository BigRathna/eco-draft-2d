import pytest
import sys
import os

# Ensure backend/ is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.services.nlp.prompt_builder import create_prompt_builder
from app.services.nlp.adapters import get_adapter, GeminiAdapter, OpenAICompatibleAdapter
from app.services.nlp import prompts

def test_prompt_bundle_versioning():
    builder1 = create_prompt_builder(is_modification=False)
    bundle1 = builder1.build_bundle()
    
    builder2 = create_prompt_builder(is_modification=False)
    bundle2 = builder2.build_bundle()
    
    assert bundle1.version_hash == bundle2.version_hash
    
    builder3 = create_prompt_builder(is_modification=True)
    bundle3 = builder3.build_bundle()
    
    assert bundle1.version_hash != bundle3.version_hash

def test_prompt_bundle_content():
    builder = create_prompt_builder(is_modification=False)
    bundle = builder.build_bundle()
    full_prompt = bundle.build_full_string()
    
    assert prompts.SYSTEM_ROLE in full_prompt
    assert prompts.TASK_CREATE in full_prompt
    assert prompts.UNIT_RULES in full_prompt

def test_provider_equivalence_logic():
    """
    Verify that both Gemini and OpenAI adapters receive the same logical information.
    Note: They may have different formatting (messages vs string), but core content should match.
    """
    builder = create_prompt_builder(is_modification=False)
    bundle = builder.build_bundle()
    user_msg = "test message"
    
    gemini_payload = GeminiAdapter().transform(bundle, user_msg)
    openai_payload = OpenAICompatibleAdapter().transform(bundle, user_msg)
    
    # Check that core instructions are in both
    assert prompts.SYSTEM_ROLE in gemini_payload
    assert prompts.SYSTEM_ROLE in openai_payload[0]["content"]
    
    assert prompts.UNIT_RULES in gemini_payload
    assert prompts.UNIT_RULES in openai_payload[0]["content"]

def test_openai_adapter_formatting():
    builder = create_prompt_builder(is_modification=False)
    bundle = builder.build_bundle()
    user_msg = "Create a part"
    
    payload = OpenAICompatibleAdapter().transform(bundle, user_msg)
    
    assert len(payload) == 2
    assert payload[0]["role"] == "system"
    assert payload[1]["role"] == "user"
    assert payload[1]["content"] == user_msg
    # OpenAI specifically gets the JSON instructions
    assert prompts.JSON_SCHEMA in payload[0]["content"]

if __name__ == "__main__":
    import pytest
    pytest.main([__file__])
