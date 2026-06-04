import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import HumanMessage, AIMessage

from core.brain import Brain

@pytest.fixture
def mock_brain():
    with patch("core.brain.Brain._health_check"):
        with patch("core.brain.Brain._load_config", return_value={
            "model": "llama3.1:8b",
            "model_url": "http://localhost:11434",
            "max_history": 5,
            "history_file": "test_history.json"
        }):
            with patch("core.brain.Brain._load_history", return_value=[]):
                brain = Brain()
                brain.client = MagicMock()
                yield brain

def test_chat_history_trimming(mock_brain):
    mock_brain.client.invoke.return_value = MagicMock(content="Hello Sir.")
    
    # Send multiple messages to exceed max_history=5
    for i in range(7):
        mock_brain.chat(f"msg {i}")
        
    # max_history keeps 5 items. Each chat adds 1 human + 1 ai message = 2 messages per chat.
    # History gets trimmed to keep last 5 messages
    assert len(mock_brain.history) <= 5

@patch("core.memory.retrieve_context", return_value="[Past context] Favorite editor is VSCode")
def test_dynamic_system_prompt_injection(mock_retrieve, mock_brain):
    # Setup chat invoke response
    mock_brain.client.invoke.return_value = MagicMock(content="Excellent, Sir.")
    
    res = mock_brain.chat("What is my favorite editor?")
    
    # Assert query context was pulled
    mock_retrieve.assert_called_once_with("What is my favorite editor?", top_k=3)
    
    # Assert ChatOllama was invoked with the dynamic prompt containing the context
    args, kwargs = mock_brain.client.invoke.call_args
    messages = args[0]
    
    # SystemMessage is always the first message
    system_msg = messages[0]
    assert "Favorite editor is VSCode" in system_msg.content
    assert "Excellent, Sir." in res
