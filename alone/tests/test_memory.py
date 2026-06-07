import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import core.memory as memory

@pytest.fixture(autouse=True)
def setup_mocks():
    # Save original values
    orig_memory_col = memory.memory_col
    orig_pref_col = memory.pref_col
    
    # Setup mock collections for clean memory testing boundaries
    memory.memory_col = MagicMock()
    memory.pref_col = MagicMock()
    
    # Disable structured preferences for legacy ChromaDB memory tests
    from core.preferences_service import preference_service
    orig_use_structured = preference_service.use_structured
    preference_service.use_structured = False
    
    yield
    
    # Restore original values
    memory.memory_col = orig_memory_col
    memory.pref_col = orig_pref_col
    preference_service.use_structured = orig_use_structured

def test_add_memory():
    memory.add_memory("user", "Hello assistant", {"topic": "greeting"})
    memory.memory_col.add.assert_called_once()
    
    # Assert args passed to add
    args, kwargs = memory.memory_col.add.call_args
    assert "Hello assistant" in kwargs["documents"]
    assert kwargs["metadatas"][0]["role"] == "user"

def test_retrieve_context_empty():
    memory.memory_col.query.return_value = {"documents": [[]], "metadatas": [[]]}
    res = memory.retrieve_context("hello")
    assert res == ""

def test_retrieve_context_found():
    memory.memory_col.query.return_value = {
        "documents": [["My project is in C:\\workspace"]],
        "metadatas": [[{"role": "user", "date": "2026-05-28 12:00:00"}]]
    }
    res = memory.retrieve_context("project path")
    assert "workspace" in res
    assert "User" in res

def test_clear_last_memory_empty():
    memory.memory_col.get.return_value = {"ids": [], "metadatas": []}
    res = memory.clear_last_memory()
    assert "No memories" in res

def test_clear_last_memory_deleted():
    memory.memory_col.get.return_value = {
        "ids": ["mem_1", "mem_2"],
        "metadatas": [{"timestamp": 100.0}, {"timestamp": 200.0}]
    }
    res = memory.clear_last_memory()
    assert "forgotten" in res
    memory.memory_col.delete.assert_called_once_with(ids=["mem_2"])

def test_save_preference():
    memory.pref_col.get.return_value = {"ids": []}
    memory.save_preference("user_name", "Shan")
    memory.pref_col.add.assert_called_once_with(
        ids=["pref_user_name"],
        documents=["Shan"],
        metadatas=[{"key": "user_name"}]
    )

def test_get_preference():
    memory.pref_col.get.return_value = {"ids": ["pref_user_name"], "documents": ["Shan"]}
    res = memory.get_preference("user_name")
    assert res == "Shan"
