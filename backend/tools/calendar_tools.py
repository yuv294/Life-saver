"""
Typed wrappers around CalendarService used by the Gemini function calling router.
These mirror the function_declarations in gemini_service.py exactly.
"""

from services.calendar_service import CalendarService
from typing import List, Dict, Any


async def get_calendar_events(
    calendar_service: CalendarService,
    start_date: str,
    end_date: str,
) -> List[Dict[str, Any]]:
    return await calendar_service.get_events(start_date, end_date)


async def create_calendar_event(
    calendar_service: CalendarService,
    title: str,
    start_time: str,
    end_time: str,
    description: str = "",
) -> Dict[str, Any]:
    return await calendar_service.create_event(title, start_time, end_time, description)
