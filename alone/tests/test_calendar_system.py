import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.human_memory import database
from core.human_memory.calendar_entity import CalendarEvent
from core.human_memory.calendar_repository import calendar_repository
from core.human_memory.calendar_service import calendar_service
from core.human_memory.calendar_controller import calendar_controller

def test_calendar_event_serialization():
    # Test creation and serialization
    event = CalendarEvent(
        id="test_ev",
        title="Test Event",
        start_time="2026-06-19T09:30:00Z",
        end_time="2026-06-19T10:30:00Z",
        description="A test calendar event",
        location="Room 101",
        attendees=["Rahul", "amit@gmail.com", "Arjun"],
        event_type="meeting",
        status="scheduled"
    )
    
    d = event.to_dict()
    assert d["id"] == "test_ev"
    assert d["title"] == "Test Event"
    assert d["startTime"] == "2026-06-19T09:30:00Z"
    assert d["endTime"] == "2026-06-19T10:30:00Z"
    assert d["description"] == "A test calendar event"
    assert d["location"] == "Room 101"
    assert d["attendees"] == ["Rahul", "amit@gmail.com", "Arjun"]
    assert d["eventType"] == "meeting"
    assert d["status"] == "scheduled"

    # Test deserialization
    event2 = CalendarEvent.from_dict(d)
    assert event2.id == "test_ev"
    assert event2.title == "Test Event"
    assert event2.attendees == ["Rahul", "amit@gmail.com", "Arjun"]

    # Test string serialization of attendees
    d["attendees"] = '["Rahul", "amit@gmail.com"]'
    event3 = CalendarEvent.from_dict(d)
    assert event3.attendees == ["Rahul", "amit@gmail.com"]

def test_timezone_conversions():
    # Test offset timezone conversion to UTC
    # 2026-06-19T15:00:00+05:30 -> 2026-06-19T09:30:00Z
    utc_str = calendar_service.parse_to_utc_iso("2026-06-19T15:00:00+05:30")
    assert utc_str == "2026-06-19T09:30:00Z"

    # Test space instead of T
    utc_str2 = calendar_service.parse_to_utc_iso("2026-06-19 09:30:00")
    assert utc_str2 == "2026-06-19T09:30:00Z"

    # Test trailing Z format
    utc_str3 = calendar_service.parse_to_utc_iso("2026-06-19T09:30:00Z")
    assert utc_str3 == "2026-06-19T09:30:00Z"

def test_calendar_repository_crud():
    database.init_db()
    
    event = CalendarEvent(
        id="c_repo_test",
        title="Repo Test Event",
        start_time="2026-06-19T10:00:00Z",
        end_time="2026-06-19T11:00:00Z",
        description="Desc",
        location="Office",
        attendees=["Rahul"],
        event_type="meeting"
    )
    
    # Create
    calendar_repository.create_event(event)
    
    # Retrieve
    retrieved = calendar_repository.get_event("c_repo_test")
    assert retrieved is not None
    assert retrieved.title == "Repo Test Event"
    assert retrieved.start_time == "2026-06-19T10:00:00Z"
    assert retrieved.attendees == ["Rahul"]
    
    # Update
    retrieved.location = "Remote"
    calendar_repository.update_event(retrieved)
    
    updated = calendar_repository.get_event("c_repo_test")
    assert updated.location == "Remote"
    
    # Search
    results = calendar_repository.search_events("Repo Test")
    assert len(results) >= 1
    
    # Delete
    calendar_repository.delete_event("c_repo_test")
    assert calendar_repository.get_event("c_repo_test") is None

def test_calendar_service_conflict_detection():
    database.init_db()
    
    # Clear any leftover events for clean test run
    events = calendar_repository.find_all()
    for e in events:
        if e.id in ["ev1", "ev2", "ev3"]:
            calendar_repository.delete_event(e.id)

    # Add Event 1: 10:00 to 11:00
    ev1 = CalendarEvent(
        id="ev1",
        title="Event 1",
        start_time="2026-06-19T10:00:00Z",
        end_time="2026-06-19T11:00:00Z"
    )
    res = calendar_service.schedule_event(ev1, force=False)
    assert res["success"] is True

    # Try overlapping event (10:30 to 11:30) with force=False
    ev2 = CalendarEvent(
        id="ev2",
        title="Event 2",
        start_time="2026-06-19T10:30:00Z",
        end_time="2026-06-19T11:30:00Z"
    )
    res2 = calendar_service.schedule_event(ev2, force=False)
    assert res2["success"] is False
    assert res2["conflict"] is True
    assert len(res2["conflicting_events"]) == 1
    assert res2["conflicting_events"][0]["id"] == "ev1"

    # Schedule overlapping event with force=True
    res3 = calendar_service.schedule_event(ev2, force=True)
    assert res3["success"] is True

    # Clean up
    calendar_repository.delete_event("ev1")
    calendar_repository.delete_event("ev2")

@patch('core.human_memory.calendar_controller.calendar_controller.service')
def test_calendar_controller_nlp(mock_service):
    # Mock service responses
    mock_service.parse_to_utc_iso.side_effect = lambda x: x
    mock_service.schedule_event.return_value = {"success": True, "event": {}}

    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = '{"title": "Sync with Rahul", "start_time": "2026-06-19 15:00:00", "end_time": "2026-06-19 16:00:00", "attendees": ["Rahul"], "event_type": "meeting"}'
    mock_llm.invoke.return_value = mock_response

    res = calendar_controller.process_natural_language_event(mock_llm, "Schedule a meeting with Rahul tomorrow at 3 PM")
    assert res["success"] is True
    mock_service.schedule_event.assert_called_once()
