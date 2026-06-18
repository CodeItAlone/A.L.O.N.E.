import uuid
import json
import re
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from core.human_memory.calendar_entity import CalendarEvent
from core.human_memory.calendar_service import calendar_service

class CalendarController:
    def __init__(self, service=None):
        self.service = service or calendar_service

    def create_event(self, title: str, start_time: str, end_time: str,
                     description: Optional[str] = None, location: Optional[str] = "",
                     attendees: Optional[List[str]] = None, event_type: Optional[str] = "meeting",
                     status: str = "scheduled", force: bool = False) -> Dict[str, Any]:
        try:
            event_id = str(uuid.uuid4())[:8]
            event = CalendarEvent(
                id=event_id,
                title=title,
                start_time=start_time,
                end_time=end_time,
                description=description,
                location=location,
                attendees=attendees or [],
                event_type=event_type,
                status=status
            )
            return self.service.schedule_event(event, force=force)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_event(self, event_id: str) -> Dict[str, Any]:
        try:
            event = self.service.calendar_repository.get_event(event_id)
            if not event:
                return {"success": False, "error": f"Event with ID {event_id} not found."}
            return {"success": True, "event": event.to_dict()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_events(self, start_time: Optional[str] = None, end_time: Optional[str] = None) -> Dict[str, Any]:
        try:
            events = self.service.list_events(start_time, end_time)
            return {"success": True, "events": [e.to_dict() for e in events]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def update_event(self, event_id: str, title: str, start_time: str, end_time: str,
                     description: Optional[str] = None, location: Optional[str] = "",
                     attendees: Optional[List[str]] = None, event_type: Optional[str] = "meeting",
                     status: str = "scheduled") -> Dict[str, Any]:
        try:
            # We can use update_calendar_event in database via repository
            event = self.service.calendar_repository.get_event(event_id)
            if not event:
                return {"success": False, "error": "Event not found"}
            event.title = title
            event.start_time = self.service.parse_to_utc_iso(start_time)
            event.end_time = self.service.parse_to_utc_iso(end_time)
            event.description = description
            event.location = location
            event.attendees = attendees or []
            event.event_type = event_type
            event.status = status
            self.service.calendar_repository.update_event(event)
            return {"success": True, "event": event.to_dict()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_event(self, event_id: str) -> Dict[str, Any]:
        try:
            success = self.service.delete_event(event_id)
            return {"success": success}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def process_natural_language_event(self, llm, user_message: str, force: bool = False) -> Dict[str, Any]:
        """Extracts event attributes from natural language instructions and schedules/updates the event."""
        try:
            now_local = datetime.now()
            # Calculate standard format local time context to help LLM resolve relative days
            local_time_context = now_local.strftime("%Y-%m-%d %H:%M:%S")
            
            prompt = (
                "You are an NLP calendar event extractor.\n"
                "Given the following user instruction, extract a clean JSON dictionary representing a calendar event.\n"
                f"Current Local Reference Time: {local_time_context}\n\n"
                "Fields to extract:\n"
                "- title: The short meeting name or event title (required, e.g. 'Sync with Rahul')\n"
                "- description: Optional context details (or null)\n"
                "- start_time: ISO-8601 string or date time string. Resolve relative terms (e.g. 'tomorrow at 3 PM' becomes '2026-06-19 15:00:00' based on the local reference time)\n"
                "- end_time: ISO-8601 string or date time string. If not explicitly specified, default to 1 hour after start_time\n"
                "- location: Location or meeting link (or null)\n"
                "- attendees: A JSON array of string names or emails (e.g. ['Rahul', 'amit@gmail.com'])\n"
                "- event_type: 'meeting', 'reminder', 'personal', or 'deadline' (default 'meeting')\n\n"
                "Respond with ONLY the valid JSON block and no other text.\n\n"
                f"Instruction: '{user_message}'\n"
                "JSON:"
            )
            
            from langchain_core.messages import SystemMessage, HumanMessage
            messages = [
                SystemMessage(content="You only output valid JSON representing the extracted calendar event metadata."),
                HumanMessage(content=prompt)
            ]
            response = llm.invoke(messages)
            clean_res = response.content.strip()
            
            # Extract JSON block
            match = re.search(r"\{.*\}", clean_res, re.DOTALL)
            if match:
                extracted = json.loads(match.group(0))
            else:
                extracted = json.loads(clean_res)
                
            if not extracted or "title" not in extracted or not extracted["title"]:
                return {"success": False, "error": "No event title could be extracted."}
                
            if "start_time" not in extracted or not extracted["start_time"]:
                return {"success": False, "error": "No start time could be extracted."}
                
            start_time = extracted["start_time"]
            end_time = extracted.get("end_time")
            if not end_time:
                # Default to 1 hour after start_time
                try:
                    # Let's parse and add 1 hour
                    dt = datetime.fromisoformat(start_time.replace("Z", ""))
                    end_dt = dt.replace(hour=dt.hour + 1) if dt.hour < 23 else dt
                    end_time = end_dt.isoformat()
                except Exception:
                    end_time = start_time # Fallback to same time

            return self.create_event(
                title=extracted["title"],
                start_time=start_time,
                end_time=end_time,
                description=extracted.get("description"),
                location=extracted.get("location", ""),
                attendees=extracted.get("attendees", []),
                event_type=extracted.get("event_type", "meeting"),
                force=force
            )
        except Exception as e:
            return {"success": False, "error": str(e)}

# Singleton instance
calendar_controller = CalendarController()
