import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.preferences_service import PreferenceService, preference_service
from core.human_memory import database

@pytest.fixture(autouse=True)
def clean_db():
    # Delete test preferences before and after each test
    database.delete_preference("ide")
    database.delete_preference("project_path")
    database.delete_preference("user_name")
    database.delete_preference("voice_rate")
    database.delete_preference("test_key")
    yield
    database.delete_preference("ide")
    database.delete_preference("project_path")
    database.delete_preference("user_name")
    database.delete_preference("voice_rate")
    database.delete_preference("test_key")

def test_preference_service_crud():
    service = PreferenceService()
    # Test setting categorized preference
    service.save_preference("ide", "VS Code")
    assert service.get_preference("ide") == "VS Code"
    
    # Test category retrieval
    dev_prefs = service.get_preferences_by_category("development")
    assert dev_prefs.get("ide") == "VS Code"
    
    # Test delete
    service.delete_preference("ide")
    assert service.get_preference("ide") is None

def test_preference_service_formatting():
    service = PreferenceService()
    service.save_preference("project_path", "C:\\projects")
    service.save_preference("user_name", "Shan")
    service.save_preference("voice_rate", "180")
    
    formatted = service.get_formatted_context()
    assert "=== USER PREFERENCES ===" in formatted
    assert "[Development Preferences]" in formatted
    assert "project_path: C:\\projects" in formatted
    assert "[Communication Preferences]" in formatted
    assert "user_name: Shan" in formatted
    assert "[Assistant Preferences]" in formatted
    assert "voice_rate: 180" in formatted

@patch("core.memory.get_preference_legacy")
@patch("core.memory.save_preference_legacy")
def test_preference_service_fallback(mock_save_legacy, mock_get_legacy):
    # Create service with feature flag disabled
    config_mock = {
        "features": {
            "use_structured_preferences": False
        }
    }
    
    with patch.object(PreferenceService, "_load_config", return_value=config_mock):
        service = PreferenceService()
        assert service.use_structured is False
        
        # Test get preference calls legacy
        mock_get_legacy.return_value = "LegacyVal"
        val = service.get_preference("test_key")
        assert val == "LegacyVal"
        mock_get_legacy.assert_called_once_with("test_key")
        
        # Test save preference calls legacy
        service.save_preference("test_key", "NewVal")
        mock_save_legacy.assert_called_once_with("test_key", "NewVal")

@patch("core.memory.pref_col")
def test_preference_service_migration(mock_pref_col):
    # Setup mock data in ChromaDB
    mock_pref_col.get.return_value = {
        "ids": ["pref_user_name", "pref_project_path"],
        "documents": ["Iron Man", "C:\\workspace"],
        "metadatas": [{"key": "user_name"}, {"key": "project_path"}]
    }
    
    # Mock database is active, prevent automatic init migration to isolate test execution
    with patch.object(PreferenceService, "migrate_from_chromadb"):
        service = PreferenceService()
        
    # Manually run migration
    service._migration_done = False
    service.migrate_from_chromadb()
    
    # Verify migration saved to SQLite preferences table
    assert service.get_preference("user_name") == "Iron Man"
    assert service.get_preference("project_path") == "C:\\workspace"
    
    # Verify categories were mapped correctly in SQLite database
    dev_prefs = service.get_preferences_by_category("development")
    comm_prefs = service.get_preferences_by_category("communication")
    assert dev_prefs.get("project_path") == "C:\\workspace"
    assert comm_prefs.get("user_name") == "Iron Man"
    
    # Clean up database
    database.delete_preference("user_name")
    database.delete_preference("project_path")
