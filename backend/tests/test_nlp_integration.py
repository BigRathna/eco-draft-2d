import pytest
import sys
import os
from unittest.mock import patch, MagicMock

# Ensure backend/ is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.services.nlp.parser import parse_engineering_request
from app.services.nlp.prompt_builder import create_prompt_builder
from app.services.nlp.adapters import GeminiAdapter, OpenAICompatibleAdapter
from app.services.nlp import prompts

def test_nlp_integration_end_to_end_gemini():
    """
    Verifies that session history, material context, and constraints 
    all reach the Gemini adapter through parse_engineering_request.
    """
    # 1. Setup mock context and tracker
    with patch('app.services.session.store.tracker') as mock_tracker:
        mock_tracker.get_context_summary.return_value = "Created Node 1: Plate"
        
        # We need to mock the LLM call to avoid network requests
        with patch('app.services.nlp.parser._call_gemini') as mock_gemini:
            mock_gemini.return_value = {
                "action": "create",
                "part_type": "plate",
                "parameters": {"width": 100, "height": 100}
            }
            
            # 2. Execute parse request
            user_msg = "make a square plate from aluminum"
            # In a real scenario, the material would be auto-detected or passed via msg
            parse_engineering_request(user_msg, provider="gemini")
            
            # 3. Verify the prompt seen by _call_gemini
            # It should contain version, history, material rules, and constraints
            prompt_arg = mock_gemini.call_args[0][0]
            
            assert prompts.PROMPT_VERSION in prompt_arg
            assert "Created Node 1: Plate" in prompt_arg
            assert prompts.UNIT_RULES in prompt_arg
            assert prompts.SUPPORTED_PARTS in prompt_arg
            # Engineering Rule Inventory items should be present implicitly through fragments

def test_nlp_integration_end_to_end_ollama():
    """
    Verifies that logic survives the OpenAI-compatible adapter transformation.
    """
    with patch('app.services.session.store.tracker') as mock_tracker:
        mock_tracker.get_context_summary.return_value = "Context A"
        
        with patch('app.services.nlp.parser._call_openai_compatible') as mock_openai:
            mock_openai.return_value = {
                "action": "create",
                "part_type": "gusset",
                "parameters": {"width": 50, "height": 50}
            }
            
            parse_engineering_request("new gusset", provider="ollama")
            
            # Verify the messages list
            messages = mock_openai.call_args[0][0]
            system_msg = messages[0]["content"]
            
            assert prompts.PROMPT_VERSION in system_msg
            assert "Context A" in system_msg
            assert prompts.JSON_SCHEMA in system_msg
            assert prompts.UNIT_RULES in system_msg

if __name__ == "__main__":
    pytest.main([__file__])
