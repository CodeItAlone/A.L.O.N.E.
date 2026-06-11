import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.listener import match_wake_word_fuzzy, normalize_text
from core.agent import AloneAgent

def test_fuzzy_match_thresholds():
    # Exclusion of distance-2 inputs
    detected, matched_phrase, confidence, clean_command = match_wake_word_fuzzy(normalize_text("you alone"))
    assert not detected, f"Should reject 'you alone', got similarity {confidence}"
    
    detected, matched_phrase, confidence, clean_command = match_wake_word_fuzzy(normalize_text("be alone"))
    assert not detected, f"Should reject 'be alone', got similarity {confidence}"

    detected, matched_phrase, confidence, clean_command = match_wake_word_fuzzy(normalize_text("see you alone"))
    assert not detected, "Should reject 'see you alone'"

    # Inclusion of correct target
    detected, matched_phrase, confidence, clean_command = match_wake_word_fuzzy(normalize_text("hey alone my name is subrato"))
    assert detected
    assert matched_phrase == "hey alone"
    assert clean_command == "my name is subrato"

    # Inclusion of phonetical trigger
    detected, matched_phrase, confidence, clean_command = match_wake_word_fuzzy(normalize_text("hey aloon check my files"))
    assert detected
    assert matched_phrase == "hey aloon"
    assert clean_command == "check my files"

def test_intent_heuristic_classification():
    agent = AloneAgent()
    
    # Verify profile identity triggers
    assert agent.heuristics_classify("my name is subrato") == "USER_PROFILE_UPDATE"
    assert agent.heuristics_classify("i am a student") == "USER_PROFILE_UPDATE"
    assert agent.heuristics_classify("i am a developer") == "USER_PROFILE_UPDATE"
    assert agent.heuristics_classify("i am an engineering student") == "USER_PROFILE_UPDATE"
    
    # Verify non-identity triggers (should fallback to LLM classification and return None for heuristics)
    assert agent.heuristics_classify("i am going to check my files") is None
    assert agent.heuristics_classify("i'm writing code now") is None
