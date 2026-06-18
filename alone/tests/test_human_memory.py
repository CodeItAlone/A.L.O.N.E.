import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.human_memory import database, service
from tools.human_memory import search_human_memory, manage_goals, manage_projects, manage_contacts

@pytest.fixture(autouse=True)
def cleanup_test_data():
    # Clean before test
    _do_cleanup()
    yield
    # Clean after test
    _do_cleanup()

def _do_cleanup():
    with database.db_lock:
        conn = database.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_profile WHERE key IN ('test_key', 'name')")
            cursor.execute("DELETE FROM preferences WHERE key = 'test_pref'")
            cursor.execute("DELETE FROM projects WHERE id IN ('test_proj_123', 'p1')")
            cursor.execute("DELETE FROM goals WHERE id IN ('test_goal_123', 'g1', 'Test Goal Tool')")
            cursor.execute("DELETE FROM relationships WHERE id IN ('test_rel_123', 'r1')")
            conn.commit()
        except Exception:
            pass
        finally:
            conn.close()

def test_database_profile_crud():
    # Test setting and retrieving profile field
    database.set_profile_field("test_key", "test_value")
    prof = database.get_profile()
    assert prof.get("test_key") == "test_value"
    
    # Test updating profile field
    database.set_profile_field("test_key", "new_value")
    prof = database.get_profile()
    assert prof.get("test_key") == "new_value"
    
    # Test deleting profile field
    database.delete_profile_field("test_key")
    prof = database.get_profile()
    assert "test_key" not in prof

def test_database_preferences_crud():
    # Test preferences
    database.set_preference("test_pref", "val", "test_category")
    prefs = database.get_preferences(category="test_category")
    assert "test_pref" in prefs
    assert prefs["test_pref"]["value"] == "val"
    assert prefs["test_pref"]["category"] == "test_category"
    
    database.delete_preference("test_pref")
    prefs = database.get_preferences(category="test_category")
    assert "test_pref" not in prefs

def test_database_projects_crud():
    project_id = "test_proj_123"
    database.add_project(project_id, "Test Project", "Description of test project", "active")
    
    projects = database.get_projects()
    matched = [p for p in projects if p["id"] == project_id]
    assert len(matched) == 1
    assert matched[0]["name"] == "Test Project"
    assert matched[0]["status"] == "active"
    
    # Update status
    database.update_project(project_id, "Test Project", "Updated desc", "completed")
    projects = database.get_projects()
    matched = [p for p in projects if p["id"] == project_id]
    assert matched[0]["description"] == "Updated desc"
    assert matched[0]["status"] == "completed"
    
    # Delete
    database.delete_project(project_id)
    projects = database.get_projects(include_deleted=False)
    matched = [p for p in projects if p["id"] == project_id]
    assert len(matched) == 0

    # Clean up completely (hard delete for tests so it doesn't conflict)
    with database.db_lock:
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        conn.commit()
        conn.close()

def test_database_goals_crud():
    goal_id = "test_goal_123"
    database.add_goal(goal_id, "Test Goal", "Goal description", "pending", target_date="2026-12-31")
    
    goals = database.get_goals()
    matched = [g for g in goals if g["id"] == goal_id]
    assert len(matched) == 1
    assert matched[0]["title"] == "Test Goal"
    assert matched[0]["target_date"] == "2026-12-31"
    
    database.update_goal(goal_id, "Updated Goal", "New desc", "in_progress")
    goals = database.get_goals()
    matched = [g for g in goals if g["id"] == goal_id]
    assert matched[0]["title"] == "Updated Goal"
    assert matched[0]["status"] == "in_progress"
    
    database.delete_goal(goal_id)
    goals = database.get_goals(include_deleted=False)
    matched = [g for g in goals if g["id"] == goal_id]
    assert len(matched) == 0

    # Clean up completely (hard delete for tests so it doesn't conflict)
    with database.db_lock:
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
        conn.commit()
        conn.close()

def test_database_relationships_crud():
    rel_id = "test_rel_123"
    database.add_relationship(rel_id, "Bruce Wayne", "friend", "bruce@waynecorp.com", "Loves bats")
    
    rels = database.get_relationships()
    matched = [r for r in rels if r["id"] == rel_id]
    assert len(matched) == 1
    assert matched[0]["name"] == "Bruce Wayne"
    assert matched[0]["relation_type"] == "friend"
    
    database.update_relationship(rel_id, "Bruce Wayne", "colleague", "bruce@waynecorp.com", "Has a dark suit")
    rels = database.get_relationships()
    matched = [r for r in rels if r["id"] == rel_id]
    assert matched[0]["relation_type"] == "colleague"
    assert matched[0]["notes"] == "Has a dark suit"
    
    database.delete_relationship(rel_id)
    rels = database.get_relationships(include_deleted=False)
    matched = [r for r in rels if r["id"] == rel_id]
    assert len(matched) == 0

    # Clean up completely (hard delete for tests so it doesn't conflict)
    with database.db_lock:
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM relationships WHERE id = ?", (rel_id,))
        conn.commit()
        conn.close()

def test_service_context_summary():
    # Setup test entries
    database.set_profile_field("name", "Tony Stark")
    database.add_project("p1", "Iron Suit", "Build Mark 85", "active")
    database.add_goal("g1", "Save Universe", "Use infinity stones", "pending")
    database.add_relationship("r1", "Pepper Potts", "family", "pepper@stark.com", "Wife")
    
    summary = service.get_active_context_summary()
    assert "Tony Stark" in summary
    assert "Iron Suit" in summary
    assert "Save Universe" in summary
    assert "Pepper Potts" in summary
    
    # Cleanup
    database.delete_profile_field("name")
    database.delete_project("p1")
    database.delete_goal("g1")
    database.delete_relationship("r1")

    # Hard delete setup entries
    with database.db_lock:
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM projects WHERE id = 'p1'")
        cursor.execute("DELETE FROM goals WHERE id = 'g1'")
        cursor.execute("DELETE FROM relationships WHERE id = 'r1'")
        conn.commit()
        conn.close()

@patch('core.human_memory.service.projects_vector_col')
@patch('core.human_memory.service.goals_vector_col')
@patch('core.human_memory.service.relationships_vector_col')
def test_tools_goals_management(mock_rels, mock_goals, mock_projects):
    # Test list empty
    with patch('core.human_memory.database.get_goals', return_value=[]):
        res = manage_goals.run({"action": "list"})
        assert "No goals found" in res
        
    # Test add goal
    with patch('core.human_memory.database.add_goal') as mock_add:
        res = manage_goals.run({"action": "add", "title": "Test Goal Tool", "desc": "Tool desc", "status": "pending"})
        assert "Successfully added goal" in res
        mock_add.assert_called_once()
