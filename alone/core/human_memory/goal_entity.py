from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict

@dataclass
class Goal:
    id: str
    title: str
    description: Optional[str] = None
    category: str = ""
    priority: str = ""
    status: str = "pending"
    progress: int = 0
    targetDate: Optional[str] = None  # maps to target_date in SQLite
    parentGoalId: Optional[str] = None  # maps to parent_goal_id in SQLite
    projectIds: List[str] = field(default_factory=list)
    createdAt: Optional[str] = None  # maps to created_at in SQLite
    updatedAt: Optional[str] = None  # maps to updated_at in SQLite

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the Goal object into a dictionary with camelCase fields."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "priority": self.priority,
            "status": self.status,
            "progress": self.progress,
            "targetDate": self.targetDate,
            "parentGoalId": self.parentGoalId,
            "projectIds": self.projectIds,
            "createdAt": self.createdAt,
            "updatedAt": self.updatedAt
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Goal":
        """Creates a Goal object from a dictionary supporting both camelCase and snake_case keys."""
        return cls(
            id=data.get("id"),
            title=data.get("title"),
            description=data.get("description"),
            category=data.get("category", ""),
            priority=data.get("priority", ""),
            status=data.get("status", "pending"),
            progress=int(data.get("progress", 0)),
            targetDate=data.get("targetDate") or data.get("target_date"),
            parentGoalId=data.get("parentGoalId") or data.get("parent_goal_id"),
            projectIds=data.get("projectIds") or data.get("project_ids") or [],
            createdAt=data.get("createdAt") or data.get("created_at"),
            updatedAt=data.get("updatedAt") or data.get("updated_at")
        )
