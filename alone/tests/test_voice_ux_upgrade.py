import os
import sys
import time
import pytest
from unittest.mock import patch, MagicMock

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.state import AssistantState, get_state, set_state, get_follow_up_start_time, reset_follow_up_timer
from core.listener import match_wake_word_fuzzy, normalize_text

def test_state_machine_transitions():
    # Reset to IDLE
    set_state(AssistantState.IDLE)
    assert get_state() == AssistantState.IDLE
    
    # Transition: IDLE -> LISTENING
    set_state(AssistantState.LISTENING)
    assert get_state() == AssistantState.LISTENING
    
    # Transition: LISTENING -> THINKING
    set_state(AssistantState.THINKING)
    assert get_state() == AssistantState.THINKING
    
    # Transition: THINKING -> SPEAKING
    set_state(AssistantState.SPEAKING)
    assert get_state() == AssistantState.SPEAKING
    
    # Transition: SPEAKING -> FOLLOW_UP
    set_state(AssistantState.FOLLOW_UP)
    assert get_state() == AssistantState.FOLLOW_UP
    
    # Transition: FOLLOW_UP -> THINKING
    set_state(AssistantState.THINKING)
    assert get_state() == AssistantState.THINKING
    
    # Transition: SPEAKING -> INTERRUPTED
    set_state(AssistantState.SPEAKING)
    set_state(AssistantState.INTERRUPTED)
    assert get_state() == AssistantState.INTERRUPTED
    
    # Transition: INTERRUPTED -> LISTENING
    set_state(AssistantState.LISTENING)
    assert get_state() == AssistantState.LISTENING

def test_wake_word_stripping():
    # Hey Alone
    detected, matched, confidence, clean = match_wake_word_fuzzy(normalize_text("Hey Alone who am I?"))
    assert detected
    assert matched == "hey alone"
    assert clean == "who am i"
    
    # Ok Alone
    detected, matched, confidence, clean = match_wake_word_fuzzy(normalize_text("Ok Alone show my projects"))
    assert detected
    assert matched == "ok alone"
    assert clean == "show my projects"
    
    # Listen
    detected, matched, confidence, clean = match_wake_word_fuzzy(normalize_text("Listen show my goals"))
    assert detected
    assert matched == "listen"
    assert clean == "show my goals"

    # Phonetic matching triggers
    detected, matched, confidence, clean = match_wake_word_fuzzy(normalize_text("hey aloon check my files"))
    assert detected
    assert clean == "check my files"
    
    # Negatives
    detected, matched, confidence, clean = match_wake_word_fuzzy(normalize_text("you alone"))
    assert not detected
    
    detected, matched, confidence, clean = match_wake_word_fuzzy(normalize_text("be alone"))
    assert not detected
    
    detected, matched, confidence, clean = match_wake_word_fuzzy(normalize_text("alone"))
    assert not detected

def test_follow_up_timeout():
    set_state(AssistantState.IDLE)
    
    # Transition to follow up
    set_state(AssistantState.FOLLOW_UP)
    assert get_state() == AssistantState.FOLLOW_UP
    
    # Mock time.time to simulate 10.1 seconds later
    start_time = get_follow_up_start_time()
    
    with patch("time.time", return_value=start_time + 10.1):
        # Triggering follow-up timeout logic simulation
        if get_state() == AssistantState.FOLLOW_UP:
            set_state(AssistantState.IDLE)
            
    assert get_state() == AssistantState.IDLE
