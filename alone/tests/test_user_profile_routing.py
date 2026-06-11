import os
import sys
import io
import pytest
from unittest.mock import patch, MagicMock

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.agent import AloneAgent
from core.human_memory import database
from core.human_memory.service import UserProfileService

@pytest.fixture(autouse=True)
def clean_db():
    database.delete_profile_field("name")
    database.delete_profile_field("education")
    database.delete_profile_field("profession")
    database.delete_profile_field("role")
    yield
    patch.stopall()
    database.delete_profile_field("name")
    database.delete_profile_field("education")
    database.delete_profile_field("profession")
    database.delete_profile_field("role")

def setup_mock_llm(agent, extraction_return=None, confirmation_return=None, retrieve_return=None):
    def mock_invoke(self_obj, messages, **kwargs):
        # Determine the prompt type based on message content
        system_content = ""
        human_content = ""
        for msg in messages:
            if msg.__class__.__name__ == "SystemMessage":
                system_content = msg.content
            elif msg.__class__.__name__ == "HumanMessage":
                human_content = msg.content
                
        # 0. Intent classification prompt
        if "intent classifier for A.L.O.N.E." in human_content:
            if "who am i" in human_content.lower() or "who am i" in system_content.lower():
                mock_res = MagicMock()
                mock_res.content = "MEMORY_RETRIEVE"
                return mock_res
            if "name is" in human_content.lower() or "i am" in human_content.lower():
                mock_res = MagicMock()
                mock_res.content = "USER_PROFILE_UPDATE"
                return mock_res
            mock_res = MagicMock()
            mock_res.content = "GENERAL_CHAT"
            return mock_res
            
        # 1. Metadata extraction prompt
        if "metadata extractor" in human_content or "extract" in human_content:
            ret_val = extraction_return or "{}"
            mock_res = MagicMock()
            mock_res.content = ret_val
            return mock_res
            
        # 2. Confirmation response prompt
        elif "confirmation response" in human_content or "acknowledging" in human_content:
            ret_val = confirmation_return or "Sir, I have updated your profile."
            mock_res = MagicMock()
            mock_res.content = ret_val
            return mock_res
            
        # 3. Retrieve response prompt
        elif "answer the user's question naturally" in human_content or "retrieved memory context" in human_content:
            ret_val = retrieve_return or "Sir, you are Subrato."
            mock_res = MagicMock()
            mock_res.content = ret_val
            return mock_res
            
        # Default fallback
        mock_res = MagicMock()
        mock_res.content = "Sir, indeed."
        return mock_res
        
    patcher = patch('langchain_ollama.ChatOllama.invoke', new=mock_invoke)
    patcher.start()
    return patcher

def test_1_profile_save():
    agent = AloneAgent()
    setup_mock_llm(
        agent,
        extraction_return='{"name": "Subrato"}',
        confirmation_return="Sir, I have saved your name as Subrato."
    )
    
    # Capture output to assert logs
    captured = io.StringIO()
    sys.stdout = captured
    try:
        response = agent.run("My name is Subrato.")
    finally:
        sys.stdout = sys.__stdout__
        
    logs = captured.getvalue()
    
    # Assert logs and status
    assert "[PROFILE DETECTED]" in logs
    assert "name=Subrato" in logs
    assert "[PROFILE SAVE]" in logs
    assert "success=True" in logs
    assert "[PROFILE VERIFY]" in logs
    assert "status=PASS" in logs
    
    # Assert DB check
    profile = database.get_profile()
    assert profile.get("name") == "Subrato"
    assert "Sir, I have saved your name as Subrato." in response

def test_2_profile_update():
    agent = AloneAgent()
    
    # Step 1: Save first field
    setup_mock_llm(agent, extraction_return='{"name": "Subrato"}')
    agent.run("My name is Subrato.")
    
    # Step 2: Update/add another field
    setup_mock_llm(
        agent,
        extraction_return='{"education": "Second year engineering student"}',
        confirmation_return="Sir, I have updated your education."
    )
    
    captured = io.StringIO()
    sys.stdout = captured
    try:
        response = agent.run("I am a second year engineering student.")
    finally:
        sys.stdout = sys.__stdout__
        
    logs = captured.getvalue()
    
    assert "[PROFILE DETECTED]" in logs
    assert "education=Second year engineering student" in logs
    # Should log PROFILE SAVE since education is a new key, or UPDATE if updating existing
    assert "[PROFILE SAVE]" in logs
    assert "success=True" in logs
    assert "[PROFILE VERIFY]" in logs
    assert "status=PASS" in logs
    
    profile = database.get_profile()
    assert profile.get("name") == "Subrato"
    assert profile.get("education") == "Second year engineering student"

def test_3_profile_retrieve():
    agent = AloneAgent()
    
    # Insert facts into database
    database.set_profile_field("name", "Subrato")
    database.set_profile_field("education", "Second year engineering student")
    
    setup_mock_llm(
        agent,
        retrieve_return="Sir, you are Subrato, a second year engineering student."
    )
    
    captured = io.StringIO()
    sys.stdout = captured
    try:
        response = agent.run("Who am I?")
    finally:
        sys.stdout = sys.__stdout__
        
    logs = captured.getvalue()
    
    assert "[PROFILE RETRIEVE]" in logs
    assert "name=Subrato" in logs
    assert "education=Second year engineering student" in logs
    assert "Sir, you are Subrato, a second year engineering student." in response

def test_4_restart_persistence():
    # 1. Start session, save profile
    agent1 = AloneAgent()
    setup_mock_llm(agent1, extraction_return='{"name": "Subrato"}')
    agent1.run("My name is Subrato.")
    
    # 2. Simulate restart: instantiate a new AloneAgent
    agent2 = AloneAgent()
    setup_mock_llm(agent2, retrieve_return="Sir, you are Subrato.")
    
    captured = io.StringIO()
    sys.stdout = captured
    try:
        response = agent2.run("Who am I?")
    finally:
        sys.stdout = sys.__stdout__
        
    logs = captured.getvalue()
    
    # Assert logs and output
    assert "[PROFILE RETRIEVE]" in logs
    assert "name=Subrato" in logs
    assert "Sir, you are Subrato." in response

def test_5_update_existing_profile_keys():
    agent = AloneAgent()
    
    # Save first name
    setup_mock_llm(agent, extraction_return='{"name": "Subrato"}')
    agent.run("My name is Subrato.")
    
    # Update name key with different value
    setup_mock_llm(
        agent,
        extraction_return='{"name": "Subrato Kundu"}',
        confirmation_return="Sir, I have updated your name to Subrato Kundu."
    )
    
    captured = io.StringIO()
    sys.stdout = captured
    try:
        response = agent.run("My name is Subrato Kundu.")
    finally:
        sys.stdout = sys.__stdout__
        
    logs = captured.getvalue()
    
    # Logs should reflect PROFILE UPDATE instead of PROFILE SAVE
    assert "[PROFILE DETECTED]" in logs
    assert "name=Subrato Kundu" in logs
    assert "[PROFILE UPDATE]" in logs
    assert "success=True" in logs
    assert "[PROFILE VERIFY]" in logs
    assert "status=PASS" in logs
    
    # Verify database state
    profile = database.get_profile()
    assert profile.get("name") == "Subrato Kundu"
    
    # Make sure we only have 1 row for 'name' in SQLite user_profile
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM user_profile WHERE key = 'name'")
    count = cursor.fetchone()[0]
    conn.close()
    assert count == 1
