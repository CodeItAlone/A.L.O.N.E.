import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.agent import run_agent

@patch("core.agent.AloneAgent.__init__", return_value=None)
def test_pipeline_react_loop(mock_init):
    # Create manual mock agent executor
    mock_agent = MagicMock()
    mock_agent.tools = []
    
    # Create the AloneAgent instance manually
    from core.agent import AloneAgent
    agent = AloneAgent()
    agent.tools = []
    agent.agent_executor = MagicMock()
    
    # Configure mock agent executor output
    agent.agent_executor.invoke.return_value = {
        "output": "Sir, I have analyzed your files and they are clean."
    }
    
    # Bind singleton instance for run_agent call
    import core.agent as agent_module
    agent_module._agent_instance = agent
    
    # Run the pipeline
    res = run_agent("Check my files")
    
    # Verify outputs
    assert "Sir," in res
    assert "clean" in res
    agent.agent_executor.invoke.assert_called_once_with({"input": "Check my files"})
