from dataclasses import dataclass, field
from typing import Optional, Any, Dict

@dataclass
class Task:
    id: str
    title: str
    description: Optional[str] = None
    priority: str = "MEDIUM"
    status: str = "PENDING"
    due_date: Optional[str] = None
    project_id: Optional[str] = None
    goal_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the Task object into a dictionary with camelCase fields."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "status": self.status,
            "dueDate": self.due_date,
            "projectId": self.project_id,
            "goalId": self.goal_id,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """Creates a Task object from a dictionary."""
        return cls(
            id=data.get("id"),
            title=data.get("title"),
            description=data.get("description"),
            priority=data.get("priority", "MEDIUM"),
            status=data.get("status", "PENDING"),
            due_date=data.get("dueDate") or data.get("due_date"),
            project_id=data.get("projectId") or data.get("project_id"),
            goal_id=data.get("goalId") or data.get("goal_id"),
            created_at=data.get("createdAt") or data.get("created_at"),
            updated_at=data.get("updatedAt") or data.get("updated_at")
        )
