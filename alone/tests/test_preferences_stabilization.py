import os
import sys
import io
import pytest

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.preferences_service import PreferenceService, preference_service
from core.human_memory import database

@pytest.fixture(autouse=True)
def clean_db():
    database.delete_preference("editor")
    database.delete_preference("ide")
    database.delete_preference("programming_language")
    yield
    database.delete_preference("editor")
    database.delete_preference("ide")
    database.delete_preference("programming_language")

def test_save_and_retrieve_preference():
    service = PreferenceService()
    
    # Capture print output
    captured_output = io.StringIO()
    sys.stdout = captured_output
    try:
        service.save_preference("editor", "VS Code")
    finally:
        sys.stdout = sys.__stdout__
        
    output = captured_output.getvalue()
    assert "[Preference Validation Passed]" in output
    assert "[Preference Saved]" in output
    
    # Retrieve preference
    val = service.get_preference("editor")
    assert val == "VS Code"

def test_update_preference_overwrite():
    service = PreferenceService()
    
    # Save first value
    service.save_preference("editor", "VS Code")
    assert service.get_preference("editor") == "VS Code"
    
    # Update value
    captured_output = io.StringIO()
    sys.stdout = captured_output
    try:
        service.save_preference("editor", "Cursor")
    finally:
        sys.stdout = sys.__stdout__
        
    output = captured_output.getvalue()
    assert "[Preference Validation Passed]" in output
    assert "[Preference Updated]" in output
    assert service.get_preference("editor") == "Cursor"

def test_delete_preference():
    service = PreferenceService()
    service.save_preference("editor", "VS Code")
    assert service.get_preference("editor") == "VS Code"
    
    service.delete_preference("editor")
    assert service.get_preference("editor") is None

def test_restart_persistence():
    # Save using first instance
    service1 = PreferenceService()
    service1.save_preference("editor", "VS Code")
    
    # Create second instance to simulate restart and verify value is loaded
    service2 = PreferenceService()
    val = service2.get_preference("editor")
    assert val == "VS Code"

def test_duplicate_handling():
    service = PreferenceService()
    service.save_preference("editor", "VS Code")
    service.save_preference("editor", "VS Code")
    
    # Verify only one row exists in SQLite table for key='editor'
    prefs = database.get_preferences()
    assert "editor" in prefs
    # Ensure there's only 1 matching value
    assert prefs["editor"]["value"] == "VS Code"

def test_missing_preference_handling():
    service = PreferenceService()
    val = service.get_preference("nonexistent_key", default="DefaultVal")
    assert val == "DefaultVal"
    
    val2 = service.get_preference("another_nonexistent_key")
    assert val2 is None
