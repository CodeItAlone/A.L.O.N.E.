from dataclasses import dataclass, field
from typing import Optional, Any, Dict, List

@dataclass
class CalendarEvent:
    id: str
    title: str
    start_time: str  # ISO-8601 UTC string (e.g. YYYY-MM-DDTHH:MM:SSZ)
    end_time: str    # ISO-8601 UTC string (e.g. YYYY-MM-DDTHH:MM:SSZ)
    description: Optional[str] = None
    location: Optional[str] = ""
    attendees: List[str] = field(default_factory=list)
    event_type: Optional[str] = "meeting"
    status: str = "scheduled"  # scheduled, cancelled
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the CalendarEvent object into a dictionary supporting camelCase fields."""
        return {
            "id": self.id,
            "title": self.title,
            "startTime": self.start_time,
            "endTime": self.end_time,
            "description": self.description,
            "location": self.location,
            "attendees": self.attendees,
            "eventType": self.event_type,
            "status": self.status,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CalendarEvent":
        """Creates a CalendarEvent object from a dictionary."""
        attendees = data.get("attendees")
        if isinstance(attendees, str):
            import json
            try:
                attendees = json.loads(attendees)
            except Exception:
                attendees = [a.strip() for a in attendees.split(",") if a.strip()]
        elif not isinstance(attendees, list):
            attendees = []

        return cls(
            id=data.get("id"),
            title=data.get("title"),
            start_time=data.get("startTime") or data.get("start_time"),
            end_time=data.get("endTime") or data.get("end_time"),
            description=data.get("description"),
            location=data.get("location", ""),
            attendees=attendees or [],
            event_type=data.get("eventType") or data.get("event_type", "meeting"),
            status=data.get("status", "scheduled"),
            created_at=data.get("createdAt") or data.get("created_at"),
            updated_at=data.get("updatedAt") or data.get("updated_at")
        )
