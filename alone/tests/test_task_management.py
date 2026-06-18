import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.human_memory import database
from core.human_memory.task_entity import Task
from core.human_memory.task_repository import task_repository
from core.human_memory.task_service import task_service
from core.human_memory.task_controller import task_controller
from core.agent import AloneAgent

def test_task_entity():
    # Test creation and serialization
    t = Task(
        id="t_test",
        title="Spring Boot API",
        description="Write CRUD routes",
        priority="HIGH",
        status="PENDING",
        due_date="2026-06-30",
        project_id="p1",
        goal_id="g1"
    )
    d = t.to_dict()
    assert d["id"] == "t_test"
    assert d["title"] == "Spring Boot API"
    assert d["description"] == "Write CRUD routes"
    assert d["priority"] == "HIGH"
    assert d["status"] == "PENDING"
    assert d["dueDate"] == "2026-06-30"
    assert d["projectId"] == "p1"
    assert d["goalId"] == "g1"

    # Test deserialization
    t2 = Task.from_dict(d)
    assert t2.id == "t_test"
    assert t2.title == "Spring Boot API"
    assert t2.due_date == "2026-06-30"
    assert t2.project_id == "p1"
    assert t2.goal_id == "g1"

def test_task_repository_crud():
    # Setup database
    database.init_db()
    
    # Save a task
    task = Task(
        id="t_repo_test",
        title="Repo Test Task",
        description="Description",
        priority="MEDIUM",
        status="PENDING"
    )
    task_repository.create_task(task)
    
    # Retrieve it
    retrieved = task_repository.find_by_id("t_repo_test")
    assert retrieved is not None
    assert retrieved.title == "Repo Test Task"
    assert retrieved.priority == "MEDIUM"
    assert retrieved.status == "PENDING"
    
    # Update it
    retrieved.status = "IN_PROGRESS"
    task_repository.update_task(retrieved)
    
    updated = task_repository.find_by_id("t_repo_test")
    assert updated.status == "IN_PROGRESS"
    
    # Find all
    all_tasks = task_repository.find_all()
    assert len([t for t in all_tasks if t.id == "t_repo_test"]) == 1
    
    # Delete
    task_repository.delete_task("t_repo_test")
    assert task_repository.find_by_id("t_repo_test") is None

def test_task_service_logic():
    database.init_db()
    
    # Create
    task = task_service.create_task(
        title="Service Test Task",
        description="Context info",
        priority="high"
    )
    tid = task.id
    assert tid is not None
    assert task.title == "Service Test Task"
    assert task.priority == "HIGH"
    assert task.status == "PENDING"
    
    # Complete
    completed = task_service.complete_task(tid)
    assert completed is not None
    assert completed.status == "COMPLETED"
    
    # Cancel
    cancelled = task_service.cancel_task(tid)
    assert cancelled is not None
    assert cancelled.status == "CANCELLED"
    
    # Update
    updated = task_service.update_task(tid, title="Updated Title", priority="medium")
    assert updated is not None
    assert updated.title == "Updated Title"
    assert updated.priority == "MEDIUM"
    
    # Get pending tasks
    pending = task_service.get_pending_tasks()
    assert len([t for t in pending if t.id == tid]) == 0  # Cancelled task is not pending
    
    # Re-open task to pending
    task_service.update_task(tid, status="PENDING")
    pending = task_service.get_pending_tasks()
    assert len([t for t in pending if t.id == tid]) == 1
    
    # Cleanup
    task_service.delete_task(tid)
    assert task_repository.find_by_id(tid) is None

def test_voice_dialog_sequence():
    database.init_db()
    
    # Clear existing tasks to have a clean slate
    all_tasks = task_repository.find_all()
    for t in all_tasks:
        task_repository.delete_task(t.id)
        
    agent = AloneAgent()
    
    # Mock LLM for natural language task processing
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = '{"title": "finish Spring Boot API", "description": null, "priority": "MEDIUM", "status": "PENDING", "due_date": null}'
    mock_llm.invoke.return_value = mock_response
    agent.llm = mock_llm
    
    # 1. Create a task to finish Spring Boot API
    res1 = agent.run("Create a task to finish Spring Boot API.")
    assert "Task created successfully." in res1
    
    # 2. What are my tasks?
    res2 = agent.run("What are my tasks?")
    assert "1. finish Spring Boot API (Pending)" in res2
    
    # 3. Mark Spring Boot API complete
    res3 = agent.run("Mark Spring Boot API complete.")
    assert "Task updated successfully." in res3
    
    # 4. Show pending tasks
    res4 = agent.run("Show pending tasks.")
    assert "No pending tasks found." in res4
