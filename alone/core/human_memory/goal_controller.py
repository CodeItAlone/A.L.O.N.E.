from typing import List, Optional, Dict, Any
from core.human_memory.goal_service import goal_service
from core.human_memory.goal_entity import Goal

class GoalController:
    def __init__(self, service=None):
        self.service = service or goal_service

    def create_goal(self, title: str, description: Optional[str] = None, category: str = "", 
                    priority: str = "", status: str = "pending", progress: int = 0, 
                    target_date: Optional[str] = None, parent_goal_id: Optional[str] = None, 
                    project_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Creates a goal and returns it as a dictionary."""
        try:
            goal = self.service.create_goal(
                title=title,
                description=description,
                category=category,
                priority=priority,
                status=status,
                progress=progress,
                target_date=target_date,
                parent_goal_id=parent_goal_id,
                project_ids=project_ids
            )
            return {"success": True, "goal": goal.to_dict()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_goal(self, goal_id: str) -> Dict[str, Any]:
        """Retrieves a goal by ID."""
        goal = self.service.get_goal(goal_id)
        if not goal:
            return {"success": False, "error": f"Goal with ID {goal_id} not found."}
        return {"success": True, "goal": goal.to_dict()}

    def get_goals(self, status: Optional[str] = None) -> Dict[str, Any]:
        """Retrieves all goals, optionally filtered by status."""
        try:
            goals = self.service.get_all_goals(status)
            return {"success": True, "goals": [g.to_dict() for g in goals]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def update_goal(self, goal_id: str, title: Optional[str] = None, description: Optional[str] = None, 
                    category: Optional[str] = None, priority: Optional[str] = None, status: Optional[str] = None, 
                    progress: Optional[int] = None, target_date: Optional[str] = None, 
                    parent_goal_id: Optional[str] = None, project_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Updates a goal and returns the updated goal."""
        try:
            goal = self.service.update_goal(
                goal_id=goal_id,
                title=title,
                description=description,
                category=category,
                priority=priority,
                status=status,
                progress=progress,
                target_date=target_date,
                parent_goal_id=parent_goal_id,
                project_ids=project_ids
            )
            return {"success": True, "goal": goal.to_dict()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_goal(self, goal_id: str) -> Dict[str, Any]:
        """Deletes a goal."""
        try:
            success = self.service.delete_goal(goal_id)
            return {"success": success}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def link_project_to_goal(self, goal_id: str, project_id_or_name: str) -> Dict[str, Any]:
        """Links a project to a goal."""
        try:
            success = self.service.link_project(goal_id, project_id_or_name)
            return {"success": success}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def unlink_project_from_goal(self, goal_id: str, project_id_or_name: str) -> Dict[str, Any]:
        """Unlinks a project from a goal."""
        try:
            success = self.service.unlink_project(goal_id, project_id_or_name)
            return {"success": success}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def process_natural_language_goal(self, llm, user_message: str) -> Dict[str, Any]:
        """Runs extraction pipeline and saves the extracted Goal."""
        try:
            extracted = self.service.extract(llm, user_message)
            if not extracted or "title" not in extracted or not extracted["title"]:
                return {"success": False, "error": "No goal title could be extracted from statement."}
            
            goal = self.service.create_goal(
                title=extracted["title"],
                description=extracted.get("description"),
                category=extracted.get("category") or "",
                priority=extracted.get("priority") or "",
                status=extracted.get("status") or "pending",
                progress=extracted.get("progress") or 0,
                target_date=extracted.get("targetDate"),
                project_ids=extracted.get("projectIds") or []
            )
            return {"success": True, "goal": goal.to_dict(), "extracted": extracted}
        except Exception as e:
            return {"success": False, "error": str(e)}

# Singleton instance
goal_controller = GoalController()
