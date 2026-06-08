import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.project_memory_service import ProjectMemoryService, project_memory_service
from core.human_memory import database
from core.preferences_service import preference_service
from core.agent import AloneAgent

TEST_PROJECT_IDS = []

@pytest.fixture(autouse=True)
def cleanup_projects():
    global TEST_PROJECT_IDS
    TEST_PROJECT_IDS = []
    # Clear active project preference
    database.delete_preference("active_project_id")
    yield
    # Cleanup any projects created during test
    for pid in TEST_PROJECT_IDS:
        try:
            database.delete_project(pid)
        except Exception:
            pass
    # Clean by name just in case
    for name in ["test project alpha", "test project beta", "test project update", "test project persistence", "proj1", "proj2"]:
        try:
            projects = database.get_projects()
            for p in projects:
                if p["name"].lower().strip() == name:
                    database.delete_project(p["id"])
        except Exception:
            pass
    database.delete_preference("active_project_id")

def test_project_memory_service_crud():
    service = ProjectMemoryService()
    
    # 1. Create Project
    p = service.create_project(
        name="Test Project Alpha",
        description="This is a test project",
        phase="1.0",
        priority="High"
    )
    TEST_PROJECT_IDS.append(p["id"])
    
    assert p["name"] == "Test Project Alpha"
    assert p["description"] == "This is a test project"
    assert p["phase"] == "1.0"
    assert p["priority"] == "High"
    assert p["status"] == "active"
    
    # 2. Get Project
    retrieved = service.get_project(p["id"])
    assert retrieved is not None
    assert retrieved["name"] == "Test Project Alpha"
    
    # Get by Name
    retrieved_by_name = service.get_project("Test Project Alpha")
    assert retrieved_by_name is not None
    assert retrieved_by_name["id"] == p["id"]
    
    # 3. Update Project
    updated = service.update_project(
        p["id"],
        name="Test Project Alpha Updated",
        description="New description",
        phase="2.0",
        priority="Critical"
    )
    assert updated["name"] == "Test Project Alpha Updated"
    assert updated["description"] == "New description"
    assert updated["phase"] == "2.0"
    assert updated["priority"] == "Critical"
    
    # 4. Archive Project
    archived = service.archive_project(p["id"])
    assert archived["status"] == "archived"
    
    # 5. Delete Project
    assert service.delete_project(p["id"]) is True
    assert service.get_project(p["id"]) is None

def test_project_intents_bypass():
    agent = AloneAgent()
    
    # 1. Project Create Intent
    response = agent.run("create project Test Project Beta with phase 2.1 and priority Medium")
    assert "created the project" in response
    assert "Test Project Beta" in response
    
    # Retrieve created project to track it
    p = project_memory_service.get_project("Test Project Beta")
    assert p is not None
    TEST_PROJECT_IDS.append(p["id"])
    assert p["phase"] == "2.1"
    assert p["priority"] == "Medium"
    
    # 2. Project Update Intent
    update_response = agent.run("set project Test Project Beta phase to 3.0")
    assert "updated the project" in update_response
    p_updated = project_memory_service.get_project(p["id"])
    assert p_updated["phase"] == "3.0"
    
    # 3. Project Status Intent
    status_response = agent.run("project status Test Project Beta")
    assert "status of project 'Test Project Beta'" in status_response
    assert "3.0" in status_response
    
    # 4. Project List Intent
    list_response = agent.run("list my projects")
    assert "Test Project Beta" in list_response
    
    # 5. Project Details Intent
    details_response = agent.run("tell me about project Test Project Beta")
    assert "details for project 'Test Project Beta'" in details_response

def test_project_persistence():
    service1 = ProjectMemoryService()
    p = service1.create_project(
        name="Test Project Persistence",
        description="Persistent test",
        phase="1.0",
        priority="Low"
    )
    TEST_PROJECT_IDS.append(p["id"])
    
    # Simulate service restart/re-instantiation
    service2 = ProjectMemoryService()
    retrieved = service2.get_project(p["id"])
    assert retrieved is not None
    assert retrieved["name"] == "Test Project Persistence"
    assert retrieved["phase"] == "1.0"
    assert retrieved["priority"] == "Low"

def test_multi_project_and_context_injection():
    service = ProjectMemoryService()
    
    # Create project 1
    p1 = service.create_project(name="Proj1", phase="1.0", priority="Low")
    TEST_PROJECT_IDS.append(p1["id"])
    
    # Create project 2
    p2 = service.create_project(name="Proj2", phase="2.0", priority="High")
    TEST_PROJECT_IDS.append(p2["id"])
    
    # Verify both exist
    assert service.get_project(p1["id"]) is not None
    assert service.get_project(p2["id"]) is not None
    
    # Verify p2 was automatically set as active because it was created last
    active_id = preference_service.get_preference("active_project_id")
    assert active_id == p2["id"]
    
    # Verify context injection matches p2
    context = service.get_active_project_context()
    assert "Proj2" in context
    assert "2.0" in context
    assert "High" in context
    
    # Switch active project explicitly via preference
    preference_service.save_preference("active_project_id", p1["id"])
    
    # Verify context injection matches p1
    context2 = service.get_active_project_context()
    assert "Proj1" in context2
    assert "1.0" in context2
    assert "Low" in context2
