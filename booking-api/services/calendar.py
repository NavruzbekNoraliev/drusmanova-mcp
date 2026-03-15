import os
import base64
import json
import logging
from datetime import datetime, date, time, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON", "")
GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")


def _is_mock_mode() -> bool:
    return not bool(GOOGLE_CREDENTIALS_JSON.strip())


def _get_service():
    """Build Google Calendar service from base64-encoded service account JSON."""
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds_json = base64.b64decode(GOOGLE_CREDENTIALS_JSON).decode("utf-8")
    creds_info = json.loads(creds_json)
    credentials = service_account.Credentials.from_service_account_info(
        creds_info,
        scopes=["https://www.googleapis.com/auth/calendar"],
    )
    return build("calendar", "v3", credentials=credentials)


def get_busy_slots(target_date: date) -> list[tuple[datetime, datetime]]:
    """
    Query Google Calendar freebusy for the given date.
    Returns list of (start, end) datetime tuples in UTC.
    In mock mode, returns empty list (all slots free).
    """
    if _is_mock_mode():
        logger.info("Google Calendar mock mode: returning no busy slots")
        return []

    try:
        service = _get_service()
        tz_offset = "+05:00"  # Tashkent timezone (UTC+5)
        time_min = f"{target_date.isoformat()}T00:00:00{tz_offset}"
        time_max = f"{target_date.isoformat()}T23:59:59{tz_offset}"

        body = {
            "timeMin": time_min,
            "timeMax": time_max,
            "timeZone": "Asia/Tashkent",
            "items": [{"id": GOOGLE_CALENDAR_ID}],
        }
        result = service.freebusy().query(body=body).execute()
        busy_periods = result.get("calendars", {}).get(GOOGLE_CALENDAR_ID, {}).get("busy", [])

        busy_slots = []
        for period in busy_periods:
            start = datetime.fromisoformat(period["start"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(period["end"].replace("Z", "+00:00"))
            busy_slots.append((start, end))

        return busy_slots
    except Exception as e:
        logger.error(f"Failed to fetch Google Calendar busy slots: {e}")
        return []


def create_calendar_event(
    patient_name: str,
    appointment_date: date,
    appointment_time_str: str,  # HH:MM
    reason_for_visit: Optional[str] = None,
) -> Optional[str]:
    """
    Create a Google Calendar event for the appointment.
    Returns the event ID, or None in mock mode / on error.
    """
    if _is_mock_mode():
        logger.info("Google Calendar mock mode: skipping event creation")
        return None

    try:
        service = _get_service()
        hour, minute = map(int, appointment_time_str.split(":"))
        start_dt = datetime(
            appointment_date.year,
            appointment_date.month,
            appointment_date.day,
            hour,
            minute,
            tzinfo=None,
        )
        end_dt = start_dt + timedelta(minutes=30)

        event = {
            "summary": f"Dr. Usmanova - {patient_name}",
            "location": "drusmanova.uz",
            "description": reason_for_visit or "Appointment",
            "start": {
                "dateTime": start_dt.strftime("%Y-%m-%dT%H:%M:00"),
                "timeZone": "Asia/Tashkent",
            },
            "end": {
                "dateTime": end_dt.strftime("%Y-%m-%dT%H:%M:00"),
                "timeZone": "Asia/Tashkent",
            },
        }

        created = service.events().insert(calendarId=GOOGLE_CALENDAR_ID, body=event).execute()
        return created.get("id")
    except Exception as e:
        logger.error(f"Failed to create Google Calendar event: {e}")
        return None


def cancel_calendar_event(event_id: str) -> bool:
    """Delete a Google Calendar event by ID. Returns True on success."""
    if _is_mock_mode() or not event_id:
        return True

    try:
        service = _get_service()
        service.events().delete(calendarId=GOOGLE_CALENDAR_ID, eventId=event_id).execute()
        return True
    except Exception as e:
        logger.error(f"Failed to delete Google Calendar event {event_id}: {e}")
        return False
