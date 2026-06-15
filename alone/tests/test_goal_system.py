import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.human_memory import database
from core.human_memory.goal_entity import Goal
from core.human_memory.goal_repository import goal_repository
from core.human_memory.goal_service import goal_service
from core.human_memory.goal_controller import goal_controller

def test_goal_entity():
    # Test creation and serialization
    g = Goal(
        id="test_g",
        title="Test Title",
        description="Test Desc",
        category="work",
        priority="high",
        status="pending",
        progress=10,
        targetDate="2026-06-30",
        projectIds=["p1", "p2"]
    )
    d = g.to_dict()
    assert d["id"] == "test_g"
    assert d["title"] == "Test Title"
    assert d["description"] == "Test Desc"
    assert d["category"] == "work"
    assert d["priority"] == "high"
    assert d["status"] == "pending"
    assert d["progress"] == 10
    assert d["targetDate"] == "2026-06-30"
    assert d["projectIds"] == ["p1", "p2"]

    # Test deserialization
    g2 = Goal.from_dict(d)
    assert g2.id == "test_g"
    assert g2.title == "Test Title"
    assert g2.projectIds == ["p1", "p2"]

def test_goal_repository_crud():
    # Setup database
    database.init_db()
    
    # Save a goal
    goal = Goal(
        id="g_repo_test",
        title="Repo Test Goal",
        description="Description",
        category="personal",
        priority="low",
        status="pending",
        progress=0
    )
    goal_repository.save(goal)
    
    # Retrieve it
    retrieved = goal_repository.find_by_id("g_repo_test")
    assert retrieved is not None
    assert retrieved.title == "Repo Test Goal"
    assert retrieved.category == "personal"
    assert retrieved.priority == "low"
    
    # Update it
    retrieved.progress = 50
    retrieved.status = "in_progress"
    goal_repository.save(retrieved)
    
    updated = goal_repository.find_by_id("g_repo_test")
    assert updated.progress == 50
    assert updated.status == "in_progress"
    
    # Find all
    all_goals = goal_repository.find_all()
    assert len([g for g in all_goals if g.id == "g_repo_test"]) == 1
    
    # Delete
    goal_repository.delete("g_repo_test")
    assert goal_repository.find_by_id("g_repo_test") is None

def test_project_goal_linking():
    database.init_db()
    
    # Ensure project exists
    database.delete_project("p_link_test")
    database.add_project("p_link_test", "Link Test Project", "Desc")
    
    goal = Goal(
        id="g_link_test",
        title="Link Test Goal",
        projectIds=["p_link_test"]
    )
    goal_repository.save(goal)
    
    # Check link was created
    retrieved = goal_repository.find_by_id("g_link_test")
    assert "p_link_test" in retrieved.projectIds
    
    # Unlink project
    goal_service.unlink_project("g_link_test", "p_link_test")
    retrieved = goal_repository.find_by_id("g_link_test")
    assert "p_link_test" not in retrieved.projectIds
    
    # Clean up
    goal_repository.delete("g_link_test")
    database.delete_project("p_link_test")

def test_subgoal_progress_recalculation():
    database.init_db()
    
    # Create parent goal
    parent = goal_service.create_goal(title="Parent Goal")
    pid = parent.id
    
    # Create child goals
    child1 = goal_service.create_goal(title="Child 1", parent_goal_id=pid, progress=0)
    child2 = goal_service.create_goal(title="Child 2", parent_goal_id=pid, progress=0)
    
    # Parent progress should be 0
    parent_retrieved = goal_service.get_goal(pid)
    assert parent_retrieved.progress == 0
    
    # Update Child 1 progress
    goal_service.update_goal(child1.id, progress=50)
    parent_retrieved = goal_service.get_goal(pid)
    assert parent_retrieved.progress == 25  # (50 + 0) // 2
    
    # Update Child 2 progress to 50
    goal_service.update_goal(child2.id, progress=50)
    parent_retrieved = goal_service.get_goal(pid)
    assert parent_retrieved.progress == 50  # (50 + 50) // 2
    
    # Update both to 100
    goal_service.update_goal(child1.id, progress=100)
    goal_service.update_goal(child2.id, progress=100)
    parent_retrieved = goal_service.get_goal(pid)
    assert parent_retrieved.progress == 100
    assert parent_retrieved.status == "achieved"
    
    # Clean up
    goal_service.delete_goal(child1.id)
    goal_service.delete_goal(child2.id)
    goal_service.delete_goal(pid)

@patch('core.human_memory.goal_service.hm_vector_service')
def test_goal_extraction_pipeline(mock_vector):
    mock_llm = MagicMock()
    mock_response = MagicMock()
    # Mock LLM returns a structured JSON
    mock_response.content = '{"title": "Finish Phase 1.4", "description": "Write tests", "category": "work", "priority": "high", "progress": 80, "targetDate": "2026-06-20", "projectIds": ["p1"]}'
    mock_llm.invoke.return_value = mock_response
    
    # Run process_natural_language_goal via controller
    res = goal_controller.process_natural_language_goal(mock_llm, "Finish Phase 1.4 for project p1 before 2026-06-20 with high priority")
    assert res["success"] is True
    g = res["goal"]
    assert g["title"] == "Finish Phase 1.4"
    assert g["category"] == "work"
    assert g["priority"] == "high"
    assert g["progress"] == 80
    assert g["targetDate"] == "2026-06-20"
    
    # Clean up created goal
    goal_service.delete_goal(g["id"])
