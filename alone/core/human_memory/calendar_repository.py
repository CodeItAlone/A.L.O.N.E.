import json
from datetime import datetime
from typing import List, Optional
from core.human_memory.calendar_entity import CalendarEvent

class CalendarRepository:
    def create_event(self, event: CalendarEvent) -> CalendarEvent:
        from core.human_memory import database
        
        attendees_str = json.dumps(event.attendees)
        database.add_calendar_event(
            event_id=event.id,
            title=event.title,
            description=event.description,
            start_time=event.start_time,
            end_time=event.end_time,
            location=event.location,
            attendees=attendees_str,
            event_type=event.event_type,
            status=event.status
        )
        return event

    def update_event(self, event: CalendarEvent) -> CalendarEvent:
        from core.human_memory import database
        
        attendees_str = json.dumps(event.attendees)
        database.update_calendar_event(
            event_id=event.id,
            title=event.title,
            description=event.description,
            start_time=event.start_time,
            end_time=event.end_time,
            location=event.location,
            attendees=attendees_str,
            event_type=event.event_type,
            status=event.status
        )
        return event

    def delete_event(self, event_id: str) -> bool:
        from core.human_memory import database
        database.delete_calendar_event(event_id)
        return True

    def get_event(self, event_id: str) -> Optional[CalendarEvent]:
        all_events = self.find_all()
        for e in all_events:
            if e.id == event_id:
                return e
        return None

    def find_all(self) -> List[CalendarEvent]:
        from core.human_memory import database
        rows = database.get_calendar_events()
        return [CalendarEvent.from_dict(row) for row in rows]

    def get_events_for_day(self, date_str: str) -> List[CalendarEvent]:
        """date_str in YYYY-MM-DD format."""
        events = self.find_all()
        day_events = []
        for e in events:
            # Check if start_time date matches date_str
            # start_time is ISO format like 2026-06-19T09:30:00Z
            if e.start_time.startswith(date_str):
                day_events.append(e)
        return day_events

    def get_events_for_range(self, start_iso: str, end_iso: str) -> List[CalendarEvent]:
        events = self.find_all()
        range_events = []
        for e in events:
            if start_iso <= e.start_time <= end_iso:
                range_events.append(e)
        return range_events

    def search_events(self, query: str) -> List[CalendarEvent]:
        query_lower = query.lower()
        events = self.find_all()
        matched = []
        for e in events:
            if (query_lower in e.title.lower() or 
                (e.description and query_lower in e.description.lower()) or 
                (e.location and query_lower in e.location.lower()) or
                any(query_lower in a.lower() for a in e.attendees)):
                matched.append(e)
        return matched

# Singleton instance
calendar_repository = CalendarRepository()
