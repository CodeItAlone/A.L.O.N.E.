import sqlite3
from datetime import datetime
from typing import List, Optional
from core.human_memory.database import get_connection, db_lock
from core.human_memory.goal_entity import Goal

class GoalRepository:
    def save(self, goal: Goal) -> Goal:
        """Saves a Goal using database.py CRUD functions to maintain test patch compatibility."""
        from core.human_memory import database
        
        all_goals = database.get_goals()
        exists = any(g["id"] == goal.id for g in all_goals)
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if exists:
            database.update_goal(
                goal_id=goal.id,
                title=goal.title,
                description=goal.description,
                status=goal.status,
                parent_goal_id=goal.parentGoalId,
                target_date=goal.targetDate,
                category=goal.category,
                priority=goal.priority,
                progress=goal.progress
            )
            goal.updatedAt = now
        else:
            if not goal.createdAt:
                goal.createdAt = now
            if not goal.updatedAt:
                goal.updatedAt = now
            database.add_goal(
                goal_id=goal.id,
                title=goal.title,
                description=goal.description,
                status=goal.status,
                parent_goal_id=goal.parentGoalId,
                target_date=goal.targetDate,
                category=goal.category,
                priority=goal.priority,
                progress=goal.progress
            )
            
        # Update project links
        with db_lock:
            conn = get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("DELETE FROM project_goals WHERE goal_id = ?", (goal.id,))
                for proj_id in goal.projectIds:
                    cursor.execute("SELECT id FROM projects WHERE id = ?", (proj_id,))
                    if cursor.fetchone():
                        cursor.execute("INSERT INTO project_goals (project_id, goal_id) VALUES (?, ?)", (proj_id, goal.id))
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                conn.close()
                
        return goal

    def find_by_id(self, goal_id: str) -> Optional[Goal]:
        """Finds a Goal by ID."""
        all_goals = self.find_all()
        for g in all_goals:
            if g.id == goal_id:
                return g
        return None

    def find_all(self, status: Optional[str] = None) -> List[Goal]:
        """Retrieves all goals using database.get_goals() and resolves project links."""
        from core.human_memory import database
        rows = database.get_goals(status)
        
        # Load links
        with db_lock:
            conn = get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT project_id, goal_id FROM project_goals")
                links = cursor.fetchall()
            finally:
                conn.close()
                
        # Group links
        links_by_goal = {}
        for link in links:
            gid = link["goal_id"]
            pid = link["project_id"]
            if gid not in links_by_goal:
                links_by_goal[gid] = []
            links_by_goal[gid].append(pid)
            
        goals = []
        for row in rows:
            goal_dict = dict(row)
            goal_dict["project_ids"] = links_by_goal.get(row["id"], [])
            goals.append(Goal.from_dict(goal_dict))
        return goals

    def delete(self, goal_id: str) -> bool:
        """Deletes a Goal from SQLite (project links are cascaded)."""
        from core.human_memory import database
        database.delete_goal(goal_id)
        return True

    def link_project(self, goal_id: str, project_id: str) -> bool:
        """Links a project to a goal in SQLite."""
        with db_lock:
            conn = get_connection()
            cursor = conn.cursor()
            try:
                # Ensure project exists
                cursor.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
                if not cursor.fetchone():
                    return False
                # Ensure goal exists
                cursor.execute("SELECT id FROM goals WHERE id = ?", (goal_id,))
                if not cursor.fetchone():
                    return False
                
                cursor.execute("""
                    INSERT OR IGNORE INTO project_goals (project_id, goal_id)
                    VALUES (?, ?)
                """, (project_id, goal_id))
                conn.commit()
                return True
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                conn.close()

    def unlink_project(self, goal_id: str, project_id: str) -> bool:
        """Unlinks a project from a goal in SQLite."""
        with db_lock:
            conn = get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    DELETE FROM project_goals WHERE project_id = ? AND goal_id = ?
                """, (project_id, goal_id))
                conn.commit()
                return True
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                conn.close()

    def get_project_ids(self, goal_id: str) -> List[str]:
        """Gets all linked project IDs for a goal."""
        with db_lock:
            conn = get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT project_id FROM project_goals WHERE goal_id = ?", (goal_id,))
                return [r["project_id"] for r in cursor.fetchall()]
            finally:
                conn.close()

# Singleton instance
goal_repository = GoalRepository()
