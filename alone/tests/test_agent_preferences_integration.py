import os
import sys
import io
import pytest
from unittest.mock import patch, MagicMock

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.agent import AloneAgent
from core.preferences_service import preference_service
from core.human_memory import database
try:
    from langchain.agents import AgentExecutor
except (ImportError, ModuleNotFoundError):
    from langchain_classic.agents import AgentExecutor  # type: ignore

@pytest.fixture(autouse=True)
def clean_db():
    database.delete_preference("editor")
    database.delete_preference("programming_language")
    yield
    database.delete_preference("editor")
    database.delete_preference("programming_language")

def test_scenario_a_update_intent_routing():
    agent = AloneAgent()
    
    with patch.object(AgentExecutor, 'invoke') as mock_invoke:
        captured_output = io.StringIO()
        sys.stdout = captured_output
        try:
            response = agent.run("My preferred code editor is VS Code")
        finally:
            sys.stdout = sys.__stdout__
            
        output = captured_output.getvalue()
        
        # Check output logs
        assert "[Preference Update Detected]" in output
        assert "[Preference Saved]" in output
        assert not mock_invoke.called
        assert "Understood, Sir. I have updated your preferred editor to VS Code." in response

def test_scenario_b_c_d_retrieval_and_update():
    agent = AloneAgent()
    
    with patch.object(AgentExecutor, 'invoke') as mock_invoke:
        # First query when none is set
        res1 = agent.run("What is my preferred code editor?")
        assert "I do not have a record of your preferred editor yet" in res1
        
        # Scenario B (simulate save first, then ask)
        agent.run("My preferred code editor is VS Code")
        
        captured_output = io.StringIO()
        sys.stdout = captured_output
        try:
            res2 = agent.run("What is my preferred code editor?")
        finally:
            sys.stdout = sys.__stdout__
        output = captured_output.getvalue()
        
        assert "[Preference Intent Detected]" in output
        assert "VS Code" in res2
        
        # Scenario C: "I use Cursor now"
        captured_output = io.StringIO()
        sys.stdout = captured_output
        try:
            res3 = agent.run("I use Cursor now")
        finally:
            sys.stdout = sys.__stdout__
        output = captured_output.getvalue()
        
        assert "[Preference Update Detected]" in output
        assert "[Preference Updated]" in output
        assert "Cursor" in res3
        
        # Scenario D: "What editor do I use?"
        res4 = agent.run("What editor do I use?")
        assert "Cursor" in res4

def test_scenario_e_context_injection():
    agent = AloneAgent()
    
    # Setup preferences
    agent.run("My preferred code editor is VS Code")
    agent.run("My preferred language is Java")
    
    with patch.object(AgentExecutor, 'invoke', return_value={"output": "Sir, I have generated the backend code."}) as mock_invoke:
        captured_output = io.StringIO()
        sys.stdout = captured_output
        try:
            response = agent.run("Generate backend code")
        finally:
            sys.stdout = sys.__stdout__
            
        output = captured_output.getvalue()
        
        # Ensure context was injected
        assert "[Preference Context Injected]" in output
        
        # Ensure correct single-input key invocation
        mock_invoke.assert_called_once()
        called_args = mock_invoke.call_args[0][0]
        assert "input" in called_args
        assert "preferences_context" not in called_args
        assert "VS Code" in called_args["input"]
        assert "Java" in called_args["input"]

