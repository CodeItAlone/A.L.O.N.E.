import os
import sys
import io
import pytest
from datetime import datetime

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.human_memory import database
from core.human_memory.relationship_entity import Relationship
from core.human_memory.relationship_repository import relationship_repository
from core.human_memory.relationship_service import relationship_service, IMPORTANCE_MAP
from core.human_memory.relationship_controller import relationship_controller
from core.human_memory.relationship_memory_provider import relationship_memory_provider
from core.agent import AloneAgent

@pytest.fixture(autouse=True)
def clean_db():
    # Clean up any test relationships
    for rel in relationship_repository.find_all():
        relationship_repository.delete(rel.id)
    yield
    # Clean up again after test
    for rel in relationship_repository.find_all():
        relationship_repository.delete(rel.id)

def test_database_crud_and_logging():
    # Assert database path logging is happening on CRUD
    captured_output = io.StringIO()
    sys.stdout = captured_output
    try:
        database.add_relationship(
            rel_id="test_id_123",
            name="Alice Smith",
            relation_type="friend",
            contact_info="alice@example.com",
            notes="Met at a tech meetup.",
            description="Software engineer",
            preferences="Likes Python, coffee",
            importance_score=60
        )
    finally:
        sys.stdout = sys.__stdout__
        
    output = captured_output.getvalue()
    assert "[RELATIONSHIP SAVE]" in output
    assert "human_memory.db" in output or "Database Path:" in output

    # Test retrieval
    captured_output = io.StringIO()
    sys.stdout = captured_output
    try:
        rels = database.get_relationships()
    finally:
        sys.stdout = sys.__stdout__
        
    output = captured_output.getvalue()
    assert "[RELATIONSHIP RETRIEVAL]" in output
    assert len(rels) >= 1
    alice = next(r for r in rels if r["id"] == "test_id_123")
    assert alice["name"] == "Alice Smith"
    assert alice["relation_type"] == "friend"
    assert alice["importance_score"] == 60
    assert alice["preferences"] == "Likes Python, coffee"

    # Test update
    captured_output = io.StringIO()
    sys.stdout = captured_output
    try:
        database.update_relationship(
            rel_id="test_id_123",
            name="Alice Smith",
            relation_type="friend",
            notes="Met at a tech meetup. Changed company.",
            importance_score=65
        )
    finally:
        sys.stdout = sys.__stdout__
        
    output = captured_output.getvalue()
    assert "[RELATIONSHIP UPDATE]" in output
    
    # Test delete
    database.delete_relationship("test_id_123")
    rels_after = database.get_relationships()
    assert not any(r["id"] == "test_id_123" for r in rels_after)


def test_importance_scoring():
    # Verify exact static scores are mapped correctly for all categories
    for rel_type, expected_score in IMPORTANCE_MAP.items():
        rel = relationship_service.create_relationship(
            name=f"Test {rel_type}",
            relationship_type=rel_type
        )
        assert rel.importance_score == expected_score
        relationship_repository.delete(rel.id)


def test_deduplication_and_merging():
    # Day 1: Rahul is friend
    rel1 = relationship_service.create_relationship(
        name="Rahul",
        relationship_type="FRIEND",
        description="Software developer friend"
    )
    
    # Day 2: Rahul likes React (updates preferences)
    rel2 = relationship_service.create_relationship(
        name="Rahul",
        relationship_type="FRIEND",
        preferences="Likes React"
    )
    
    # Day 3: Rahul works on frontend (updates notes)
    rel3 = relationship_service.create_relationship(
        name="Rahul",
        relationship_type="FRIEND",
        notes="Works on frontend projects"
    )

    # Verify we only have 1 Rahul in the database
    all_rels = relationship_repository.find_all()
    rahuls = [r for r in all_rels if r.name == "Rahul"]
    assert len(rahuls) == 1
    
    rahul = rahuls[0]
    assert rahul.id == rel1.id
    assert rahul.description == "Software developer friend"
    assert rahul.preferences == "Likes React"
    assert rahul.notes == "Works on frontend projects"
    
    # Check that appending preferences works if we pass multiple items
    relationship_service.create_relationship(
        name="Rahul",
        relationship_type="FRIEND",
        preferences="Likes Python, Loves AI"
    )
    rahul_updated = relationship_repository.find_by_name("Rahul")
    assert "Likes React" in rahul_updated.preferences
    assert "Likes Python" in rahul_updated.preferences
    assert "Loves AI" in rahul_updated.preferences


def test_memory_provider_integration():
    # Add relationship
    relationship_service.create_relationship(
        name="John Doe",
        relationship_type="MENTOR",
        description="Senior Architect at Google",
        preferences="Likes clean architecture",
        notes="Gave me career advice"
    )
    
    # Call retrieve through relationship_memory_provider
    res = relationship_memory_provider.retrieve("John Doe")
    assert "john doe is your mentor" in res.lower()
    assert "clean architecture" in res.lower()
    assert "google" in res.lower()


class DummyLLM:
    def __init__(self, response_content):
        self.response_content = response_content
    
    def invoke(self, messages):
        class DummyResponse:
            def __init__(self, content):
                self.content = content
        return DummyResponse(self.response_content)


def test_agent_relationship_intent_routing():
    # Mock LLM for classifier to return RELATIONSHIP_INTENT
    agent = AloneAgent()
    agent.llm = DummyLLM("RELATIONSHIP_INTENT")
    
    # Test intent classification
    intent = agent.determine_intent("My father is Bob")
    assert intent == "RELATIONSHIP_INTENT"
    
    # Mock LLM extraction response to create relationship
    extraction_json = '{"name": "Bob", "relationshipType": "FATHER", "description": "Strict but caring", "preferences": "Likes chess", "notes": "Lives in Seattle"}'
    agent.llm = DummyLLM(extraction_json)
    
    # Run agent loop for relationship store
    response = agent.run("Bob is my father. He is strict but caring and likes chess. He lives in Seattle.")
    assert "Bob" in response
    assert "father" in response.lower()
    
    # Verify Bob was created in DB
    bob = relationship_repository.find_by_name("Bob")
    assert bob is not None
    assert bob.relationship_type == "FATHER"
    assert bob.importance_score == 100
    assert bob.description == "Strict but caring"
    assert bob.preferences == "Likes chess"
    assert bob.notes == "Lives in Seattle"
