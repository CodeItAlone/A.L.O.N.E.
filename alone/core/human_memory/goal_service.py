import json
import uuid
from typing import List, Optional
from core.human_memory.goal_entity import Goal
from core.human_memory.goal_repository import goal_repository
from core.project_memory_service import project_memory_service
from core.human_memory import service as hm_vector_service

class GoalService:
    def __init__(self, repo=None):
        self.repo = repo or goal_repository

    def create_goal(self, title: str, description: Optional[str] = None, category: str = "", 
                    priority: str = "", status: str = "pending", progress: int = 0, 
                    target_date: Optional[str] = None, parent_goal_id: Optional[str] = None, 
                    project_ids: Optional[List[str]] = None) -> Goal:
        """Creates and validates a new Goal, triggers progress recalculation and vector sync."""
        if not title:
            raise ValueError("Goal title is required.")
        
        # Validate status
        valid_statuses = ["pending", "in_progress", "achieved", "failed"]
        status_clean = status.lower().strip() if status else "pending"
        if status_clean not in valid_statuses:
            status_clean = "pending"
            
        # Validate progress
        try:
            progress_val = int(progress)
            progress_val = max(0, min(100, progress_val))
        except (ValueError, TypeError):
            progress_val = 0
            
        if status_clean == "achieved":
            progress_val = 100
        elif progress_val == 100:
            status_clean = "achieved"
        elif progress_val > 0 and status_clean == "pending":
            status_clean = "in_progress"

        gid = str(uuid.uuid4())[:8]
        resolved_proj_ids = self._resolve_project_ids(project_ids or [])
        
        goal = Goal(
            id=gid,
            title=title,
            description=description,
            category=category,
            priority=priority,
            status=status_clean,
            progress=progress_val,
            targetDate=target_date,
            parentGoalId=parent_goal_id,
            projectIds=resolved_proj_ids
        )
        
        saved_goal = self.repo.save(goal)
        
        # Recalculate parent progress if this is a sub-goal
        if parent_goal_id:
            self.recalculate_parent_progress(parent_goal_id)
            
        self._sync_vector(saved_goal)
        return saved_goal

    def get_goal(self, goal_id: str) -> Optional[Goal]:
        """Retrieves a Goal by ID."""
        return self.repo.find_by_id(goal_id)

    def get_all_goals(self, status: Optional[str] = None) -> List[Goal]:
        """Retrieves all goals, optionally filtered by status."""
        return self.repo.find_all(status)

    def update_goal(self, goal_id: str, title: Optional[str] = None, description: Optional[str] = None, 
                    category: Optional[str] = None, priority: Optional[str] = None, status: Optional[str] = None, 
                    progress: Optional[int] = None, target_date: Optional[str] = None, 
                    parent_goal_id: Optional[str] = None, project_ids: Optional[List[str]] = None) -> Goal:
        """Updates and validates an existing Goal, updating parent progress recursively and syncing to vector store."""
        goal = self.repo.find_by_id(goal_id)
        if not goal:
            raise ValueError(f"Goal with ID {goal_id} not found.")

        if title is not None:
            goal.title = title
        if description is not None:
            goal.description = description
        if category is not None:
            goal.category = category
        if priority is not None:
            goal.priority = priority
        if target_date is not None:
            goal.targetDate = target_date
        if parent_goal_id is not None:
            goal.parentGoalId = parent_goal_id
        if project_ids is not None:
            goal.projectIds = self._resolve_project_ids(project_ids)

        # Update status/progress with dependency checks
        new_status = status.lower().strip() if status else None
        if new_status in ["pending", "in_progress", "achieved", "failed"]:
            goal.status = new_status

        if progress is not None:
            try:
                prog_val = int(progress)
                goal.progress = max(0, min(100, prog_val))
            except (ValueError, TypeError):
                pass
        
        # Enforce consistency
        if status is not None and progress is None:
            if goal.status == "achieved":
                goal.progress = 100
            elif goal.status == "pending":
                goal.progress = 0
        elif progress is not None and status is None:
            if goal.progress == 100:
                goal.status = "achieved"
            elif goal.progress > 0 and goal.status == "pending":
                goal.status = "in_progress"
            elif goal.progress == 0 and goal.status == "in_progress":
                goal.status = "pending"
        elif progress is not None and status is not None:
            # Both specified, enforce progress=100 if achieved
            if goal.status == "achieved":
                goal.progress = 100

        updated_goal = self.repo.save(goal)
        
        # Recursively update parents
        if updated_goal.parentGoalId:
            self.recalculate_parent_progress(updated_goal.parentGoalId)
            
        self._sync_vector(updated_goal)
        return updated_goal

    def delete_goal(self, goal_id: str) -> bool:
        """Deletes a Goal and deletes its vector record."""
        goal = self.repo.find_by_id(goal_id)
        if not goal:
            return False
            
        parent_id = goal.parentGoalId
        success = self.repo.delete(goal_id)
        
        # Remove from vector store
        try:
            hm_vector_service.delete_goal_vector(goal_id)
        except Exception:
            pass
            
        # Recalculate parent progress if it was a sub-goal
        if success and parent_id:
            self.recalculate_parent_progress(parent_id)
            
        return success

    def link_project(self, goal_id: str, project_id_or_name: str) -> bool:
        """Links a project to a goal using case-insensitive project name or ID resolution."""
        # Resolve project
        p = project_memory_service.get_project(project_id_or_name)
        if not p:
            return False
        
        success = self.repo.link_project(goal_id, p["id"])
        if success:
            goal = self.repo.find_by_id(goal_id)
            if goal:
                self._sync_vector(goal)
        return success

    def unlink_project(self, goal_id: str, project_id_or_name: str) -> bool:
        """Unlinks a project from a goal."""
        p = project_memory_service.get_project(project_id_or_name)
        if not p:
            return False
            
        success = self.repo.unlink_project(goal_id, p["id"])
        if success:
            goal = self.repo.find_by_id(goal_id)
            if goal:
                self._sync_vector(goal)
        return success

    def recalculate_parent_progress(self, parent_id: str):
        """Recursively recalculates parent progress as the average of its child goals' progress."""
        if not parent_id:
            return
        
        parent = self.repo.find_by_id(parent_id)
        if not parent:
            return
            
        all_goals = self.repo.find_all()
        children = [g for g in all_goals if g.parentGoalId == parent_id]
        
        if children:
            avg_progress = sum(c.progress for c in children) // len(children)
            parent.progress = avg_progress
            
            # Auto status mapping
            if parent.progress == 100:
                parent.status = "achieved"
            elif parent.progress > 0 and parent.status in ("pending", "achieved"):
                parent.status = "in_progress"
            elif parent.progress == 0 and parent.status == "in_progress":
                parent.status = "pending"
                
            self.repo.save(parent)
            self._sync_vector(parent)
            
            # Recurse up
            if parent.parentGoalId:
                self.recalculate_parent_progress(parent.parentGoalId)

    def _resolve_project_ids(self, project_identifiers: List[str]) -> List[str]:
        """Helper to resolve a list of project names or IDs into verified project IDs."""
        resolved = []
        for ident in project_identifiers:
            p = project_memory_service.get_project(ident)
            if p and p["id"] not in resolved:
                resolved.append(p["id"])
        return resolved

    def _sync_vector(self, goal: Goal):
        """Wrapper to call the enhanced sync service."""
        try:
            hm_vector_service.sync_goal_to_vector(
                goal_id=goal.id,
                title=goal.title,
                description=goal.description,
                status=goal.status,
                parent_goal_id=goal.parentGoalId,
                target_date=goal.targetDate,
                category=goal.category,
                priority=goal.priority,
                progress=goal.progress,
                project_ids=goal.projectIds
            )
        except Exception as e:
            print(f"[GoalService Warning] Failed to sync goal vector: {e}")

    @staticmethod
    def extract(llm, text: str) -> dict:
        """Extracts goals data from natural language user messages using LangChain/Ollama."""
        prompt = (
            "You are a precise metadata extractor for a personal assistant.\n"
            "Analyze the user's message and extract goal/milestone attributes.\n"
            "Extract details matching these fields (if not specified, use null or default):\n"
            "- title: The text representing the main goal (string, REQUIRED)\n"
            "- description: Additional details, scope, or sub-tasks (string or null)\n"
            "- category: Topic (e.g. work, personal, learning, health, etc.) (string or null)\n"
            "- priority: One of ['low', 'medium', 'high'] (string or null)\n"
            "- status: One of ['pending', 'in_progress', 'achieved', 'failed'] (string or null)\n"
            "- progress: A number between 0 and 100 (integer or null)\n"
            "- targetDate: A date when the goal should be completed (string format YYYY-MM-DD or null)\n"
            "- projectIds: Any project names, titles, or project IDs explicitly mentioned to link with this goal (array of strings or null)\n\n"
            "Return ONLY a valid JSON object with these exact keys. If a goal cannot be extracted, return an empty object {}.\n\n"
            f"User Statement: \"{text}\"\n"
            "JSON Output:"
        )
        from langchain_core.messages import SystemMessage, HumanMessage
        messages = [
            SystemMessage(content="You are a precise metadata extractor. You respond with ONLY a valid JSON object."),
            HumanMessage(content=prompt)
        ]
        try:
            response = llm.invoke(messages)
            content = response.content.strip()
            # Clean possible markdown wrap
            if content.startswith("```"):
                lines = content.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                content = "\n".join(lines).strip()
            
            data = json.loads(content)
            if isinstance(data, dict):
                # Ensure structure values
                if "title" in data and data["title"]:
                    return data
        except Exception as e:
            print(f"[Memory Warning] Goal extraction failed: {e}")
        return {}

# Singleton instance
goal_service = GoalService()
