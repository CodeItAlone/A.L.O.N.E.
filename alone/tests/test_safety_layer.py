import os
import sys
import pytest

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.safety import FollowUpValidationService

def test_safety_case_a_rejection():
    # User: "What is my preferred editor?" (simulated previous turn)
    # Background Audio: "Thanks for watching"
    previous_command = "What is my preferred editor?"
    previous_response = "Your preferred editor is VS Code."
    
    is_valid, confidence = FollowUpValidationService.validate_follow_up(
        "Thanks for watching", previous_command, previous_response, is_active_window=True
    )
    assert not is_valid
    assert confidence < 0.5

def test_safety_case_b_acceptance():
    # User: "What is my preferred editor?" (previous turn)
    # Follow-up: "Change it to Cursor" (Expected: Accepted)
    previous_command = "What is my preferred editor?"
    previous_response = "Your preferred editor is VS Code."
    
    is_valid, confidence = FollowUpValidationService.validate_follow_up(
        "Change it to Cursor", previous_command, previous_response, is_active_window=True
    )
    assert is_valid
    assert confidence >= 0.5

def test_safety_case_c_rejection():
    # Background Audio: "Hey everyone"
    is_valid, confidence = FollowUpValidationService.validate_follow_up(
        "Hey everyone", is_active_window=True
    )
    assert not is_valid
    assert confidence < 0.5

def test_safety_case_d_rejection():
    # Background Audio: "Like and subscribe"
    is_valid, confidence = FollowUpValidationService.validate_follow_up(
        "Like and subscribe", is_active_window=True
    )
    assert not is_valid
    assert confidence < 0.5

def test_safety_case_e_acceptance():
    # User: "Open my editor"
    is_valid, confidence = FollowUpValidationService.validate_follow_up(
        "Open my editor", is_active_window=False
    )
    assert is_valid
    assert confidence >= 0.5

def test_tool_safety_blocker():
    # Low confidence should block tool execution
    assert not FollowUpValidationService.verify_tool_execution("thanks for watching")
    
    # High confidence should pass
    assert FollowUpValidationService.verify_tool_execution("open my editor")
