import pytest
import sys
import os

# Ensure backend/ is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.services.nlp.prompt_builder import create_prompt_builder
from app.services.nlp import prompts

def test_prompt_builder_basic():
    builder = create_prompt_builder(is_modification=False, provider="gemini")
    prompt = builder.build_string()
    
    assert prompts.SYSTEM_ROLE in prompt
    assert prompts.TASK_CREATE in prompt
    assert prompts.UNIT_RULES in prompt
    assert "MODIFICATION request" not in prompt

def test_prompt_builder_modification():
    builder = create_prompt_builder(is_modification=True, provider="gemini")
    prompt = builder.build_string()
    
    assert prompts.TASK_MODIFY in prompt
    assert "MODIFICATION request" in prompt

def test_prompt_builder_context():
    history = "Node 1: Created plate"
    builder = create_prompt_builder(session_history=history, provider="gemini")
    prompt = builder.build_string()
    
    assert history in prompt
    assert "ACTIVE SESSION GRAPH HISTORY" in prompt

def test_prompt_builder_ollama_formatting():
    builder = create_prompt_builder(provider="ollama")
    prompt = builder.build_string()
    
    assert prompts.JSON_SCHEMA in prompt
    assert prompts.JSON_ONLY_CRITICAL in prompt

def test_prompt_builder_messages():
    user_msg = "Create a 100mm square plate"
    builder = create_prompt_builder(provider="ollama")
    messages = builder.build_messages(user_msg)
    
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == user_msg
    assert prompts.JSON_SCHEMA in messages[0]["content"]

if __name__ == "__main__":
    # If run directly, run the tests
    import sys
    pytest.main([__file__])
