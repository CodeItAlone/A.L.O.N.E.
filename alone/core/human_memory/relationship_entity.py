from dataclasses import dataclass, field
from typing import Optional, Any, Dict

@dataclass
class Relationship:
    id: str
    name: str
    relationship_type: str = "OTHER"
    description: Optional[str] = None
    preferences: Optional[str] = None
    notes: Optional[str] = None
    importance_score: int = 20
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the Relationship object into a dictionary with camelCase fields."""
        return {
            "id": self.id,
            "name": self.name,
            "relationshipType": self.relationship_type,
            "description": self.description,
            "preferences": self.preferences,
            "notes": self.notes,
            "importanceScore": self.importance_score,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Relationship":
        """Creates a Relationship object from a dictionary supporting both camelCase and snake_case keys."""
        return cls(
            id=data.get("id"),
            name=data.get("name"),
            relationship_type=data.get("relationshipType") or data.get("relationship_type") or data.get("relation_type") or "OTHER",
            description=data.get("description"),
            preferences=data.get("preferences"),
            notes=data.get("notes"),
            importance_score=int(data.get("importanceScore") or data.get("importance_score") or 20),
            created_at=data.get("createdAt") or data.get("created_at"),
            updated_at=data.get("updatedAt") or data.get("updated_at")
        )
