import pytest
from unittest.mock import patch
from core.memory_retrieval import (
    IdentityMemoryProvider,
    GoalMemoryProvider,
    RelationshipMemoryProvider,
    MemoryRetrievalService
)

def test_identity_memory_provider():
    provider = IdentityMemoryProvider()
    
    mock_profile = {
        "name": "Subrato Kundu",
        "occupation": "Developer",
        "education": "Second year engineering student"
    }
    
    with patch("core.human_memory.database.get_profile", return_value=mock_profile):
        assert provider.get_relevance("Who am I?") == 0.95
        assert provider.get_relevance("what is my name?") == 0.95
        assert provider.get_relevance("tell me about my hobbies") == 0.1
        
        results = provider.search("Who am I?")
        assert len(results) == 3
        for r in results:
            assert r["score"] >= 0.95
            assert r["memory_type"] == "identity"
            
        retrieved = provider.retrieve("Who am I?")
        assert "Subrato Kundu" in retrieved
        assert "Developer" in retrieved

def test_goal_memory_provider():
    provider = GoalMemoryProvider()
    
    mock_goals = [
        {"title": "Become Backend Developer", "description": "Learn SQLite", "status": "in_progress", "progress": 50},
        {"title": "Build ALONE", "description": "Personal assistant", "status": "pending", "progress": 10}
    ]
    
    with patch("core.human_memory.database.get_goals", return_value=mock_goals):
        assert provider.get_relevance("What are my goals?") == 0.95
        assert provider.get_relevance("What am I working towards?") == 0.95
        
        results = provider.search("backend developer")
        assert len(results) == 2
        # First goal should have higher score due to keyword match
        # sort search results first to ensure we compare correctly
        results.sort(key=lambda x: x["score"], reverse=True)
        assert results[0]["score"] > results[1]["score"]
        assert "Become Backend Developer" in results[0]["content"]

def test_relationship_memory_provider():
    provider = RelationshipMemoryProvider()
    
    mock_relationships = [
        {"name": "Rahul", "relation_type": "friend", "notes": "Met at university", "description": "Classmate", "preferences": "Likes tea"}
    ]
    
    with patch("core.human_memory.database.get_relationships", return_value=mock_relationships):
        assert provider.get_relevance("Who is Rahul?") == 0.8
        
        results = provider.search("Rahul")
        assert len(results) == 1
        assert results[0]["score"] >= 0.95
        assert "friend" in results[0]["content"]

def test_memory_retrieval_service():
    service = MemoryRetrievalService()
    id_prov = IdentityMemoryProvider()
    goal_prov = GoalMemoryProvider()
    rel_prov = RelationshipMemoryProvider()
    
    service.register_provider(id_prov)
    service.register_provider(goal_prov)
    service.register_provider(rel_prov)
    
    mock_profile = {"name": "Subrato Kundu"}
    mock_goals = [{"title": "Become Backend Developer", "status": "in_progress", "progress": 50}]
    mock_relationships = [{"name": "Rahul", "relation_type": "friend"}]
    
    with patch("core.human_memory.database.get_profile", return_value=mock_profile), \
         patch("core.human_memory.database.get_goals", return_value=mock_goals), \
         patch("core.human_memory.database.get_relationships", return_value=mock_relationships):
         
         context = service.retrieve_context("Who is Rahul?")
         assert len(context["relationships"]) > 0
         assert "Rahul" in context["relationships"][0]
