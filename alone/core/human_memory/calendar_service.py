from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from core.human_memory.calendar_entity import CalendarEvent
from core.human_memory.calendar_repository import calendar_repository

class CalendarService:
    @staticmethod
    def parse_to_utc_iso(time_str: str) -> str:
        """Parses a datetime string (with or without timezone offset) and converts it to UTC ISO-8601 string.
        Supported format examples:
        - 2026-06-19T15:00:00+05:30
        - 2026-06-19 15:00:00
        - 2026-06-19T09:30:00Z
        """
        # Replace space with T
        clean_str = time_str.strip().replace(" ", "T")
        
        # Handle trailing Z
        if clean_str.endswith("Z"):
            # Already UTC, normalize representation
            clean_str = clean_str[:-1]
            try:
                dt = datetime.fromisoformat(clean_str).replace(tzinfo=timezone.utc)
            except Exception:
                dt = datetime.strptime(clean_str, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            
        try:
            dt = datetime.fromisoformat(clean_str)
            if dt.tzinfo is None:
                # If no timezone offset, assume UTC (or local system default if needed, but UTC is safer)
                dt = dt.replace(tzinfo=timezone.utc)
        except Exception:
            # Try parsing standard formats without T
            try:
                dt = datetime.strptime(clean_str, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
            except Exception:
                dt = datetime.strptime(clean_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        
        # Convert to UTC and format
        utc_dt = dt.astimezone(timezone.utc)
        return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    def find_conflicts(self, event: CalendarEvent) -> List[CalendarEvent]:
        start = self.parse_to_utc_iso(event.start_time)
        end = self.parse_to_utc_iso(event.end_time)
        
        all_events = calendar_repository.find_all()
        conflicts = []
        for e in all_events:
            # Only conflict with active scheduled events, ignore cancelled
            if e.status != "scheduled":
                continue
            # Exclude self
            if e.id == event.id:
                continue
                
            e_start = self.parse_to_utc_iso(e.start_time)
            e_end = self.parse_to_utc_iso(e.end_time)
            
            # Overlap condition: start1 < end2 AND end1 > start2
            if start < e_end and end > e_start:
                conflicts.append(e)
                
        return conflicts

    def schedule_event(self, event: CalendarEvent, force: bool = False) -> Dict[str, Any]:
        # Normalize times to UTC ISO strings
        event.start_time = self.parse_to_utc_iso(event.start_time)
        event.end_time = self.parse_to_utc_iso(event.end_time)
        
        conflicts = self.find_conflicts(event)
        if conflicts and not force:
            print(f"[CALENDAR CONFLICT] Event '{event.title}' conflicts with: {[c.title for c in conflicts]}")
            return {
                "success": False,
                "conflict": True,
                "conflicting_events": [c.to_dict() for c in conflicts],
                "event": event.to_dict()
            }
            
        calendar_repository.create_event(event)
        return {
            "success": True,
            "event": event.to_dict()
        }

    def cancel_event(self, event_id: str) -> bool:
        event = calendar_repository.get_event(event_id)
        if not event:
            return False
        event.status = "cancelled"
        calendar_repository.update_event(event)
        return True

    def reschedule_event(self, event_id: str, start_time: str, end_time: str, force: bool = False) -> Dict[str, Any]:
        event = calendar_repository.get_event(event_id)
        if not event:
            return {"success": False, "error": "Event not found"}
            
        # Create temporary event to check conflicts
        temp_event = CalendarEvent(
            id=event.id,
            title=event.title,
            start_time=self.parse_to_utc_iso(start_time),
            end_time=self.parse_to_utc_iso(end_time),
            description=event.description,
            location=event.location,
            attendees=event.attendees,
            event_type=event.event_type,
            status=event.status
        )
        
        conflicts = self.find_conflicts(temp_event)
        if conflicts and not force:
            print(f"[CALENDAR CONFLICT] Rescheduled event '{event.title}' conflicts with: {[c.title for c in conflicts]}")
            return {
                "success": False,
                "conflict": True,
                "conflicting_events": [c.to_dict() for c in conflicts],
                "event": temp_event.to_dict()
            }
            
        event.start_time = temp_event.start_time
        event.end_time = temp_event.end_time
        calendar_repository.update_event(event)
        return {
            "success": True,
            "event": event.to_dict()
        }

    def list_events(self, start_time: Optional[str] = None, end_time: Optional[str] = None) -> List[CalendarEvent]:
        events = calendar_repository.find_all()
        if start_time or end_time:
            filtered = []
            for e in events:
                if start_time and e.start_time < self.parse_to_utc_iso(start_time):
                    continue
                if end_time and e.end_time > self.parse_to_utc_iso(end_time):
                    continue
                filtered.append(e)
            return filtered
        return events

# Singleton instance
calendar_service = CalendarService()
