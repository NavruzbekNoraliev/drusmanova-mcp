import random
import string
import logging
from datetime import date, time, datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Appointment
from schemas import AppointmentCreate, AppointmentResponse, AvailabilityResponse
from services.calendar import get_busy_slots, create_calendar_event, cancel_calendar_event

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

WORK_START = time(9, 0)
WORK_END = time(18, 0)
SLOT_MINUTES = 30


def generate_booking_ref(db: Session) -> str:
    """Generate a unique DR-XXXX booking reference."""
    for _ in range(20):
        chars = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
        ref = f"DR-{chars}"
        exists = db.query(Appointment).filter(Appointment.booking_ref == ref).first()
        if not exists:
            return ref
    raise RuntimeError("Could not generate a unique booking reference after 20 attempts")


def generate_all_slots() -> List[str]:
    """Return all 30-min slots from 09:00 to 17:30 (last slot starts at 17:30, ends 18:00)."""
    slots = []
    current = datetime.combine(date.today(), WORK_START)
    end = datetime.combine(date.today(), WORK_END)
    while current < end:
        slots.append(current.strftime("%H:%M"))
        current += timedelta(minutes=SLOT_MINUTES)
    return slots


@router.get("/availability", response_model=AvailabilityResponse)
def get_availability(date_str: str = Query(..., alias="date"), db: Session = Depends(get_db)):
    try:
        target_date = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    day_name = target_date.strftime("%A")  # Monday, Tuesday, etc.
    is_sunday = target_date.weekday() == 6

    if is_sunday:
        return AvailabilityResponse(
            date=date_str,
            available_slots=[],
            day_of_week=day_name,
            is_open=False,
        )

    all_slots = generate_all_slots()

    # Get booked slots from DB
    booked = db.query(Appointment).filter(
        Appointment.appointment_date == target_date,
        Appointment.status == "CONFIRMED",
    ).all()
    booked_times = {a.appointment_time.strftime("%H:%M") for a in booked}

    # Get busy slots from Google Calendar
    busy_periods = get_busy_slots(target_date)

    # Filter out slots that overlap with Google Calendar busy periods
    def is_busy_in_calendar(slot_str: str) -> bool:
        hour, minute = map(int, slot_str.split(":"))
        slot_start = datetime(
            target_date.year, target_date.month, target_date.day, hour, minute
        )
        slot_end = slot_start + timedelta(minutes=SLOT_MINUTES)
        for busy_start, busy_end in busy_periods:
            # Convert to naive UTC+5 for simple overlap check
            # We just do string/naive overlap — Google returns UTC, Tashkent = UTC+5
            bs = busy_start.replace(tzinfo=None) + timedelta(hours=5)
            be = busy_end.replace(tzinfo=None) + timedelta(hours=5)
            if slot_start < be and slot_end > bs:
                return True
        return False

    available = [
        s for s in all_slots
        if s not in booked_times and not is_busy_in_calendar(s)
    ]

    return AvailabilityResponse(
        date=date_str,
        available_slots=available,
        day_of_week=day_name,
        is_open=True,
    )


@router.post("/appointments", response_model=AppointmentResponse, status_code=201)
def create_appointment(payload: AppointmentCreate, db: Session = Depends(get_db)):
    target_date = payload.appointment_date
    time_str = payload.appointment_time

    # Check Sunday
    if target_date.weekday() == 6:
        raise HTTPException(status_code=400, detail="Clinic is closed on Sundays.")

    # Check past date
    if target_date < date.today():
        raise HTTPException(status_code=400, detail="Cannot book appointments in the past.")

    # Validate slot is in working hours
    hour, minute = map(int, time_str.split(":"))
    slot_time = time(hour, minute)
    if slot_time < WORK_START or slot_time >= WORK_END:
        raise HTTPException(
            status_code=400,
            detail=f"Time {time_str} is outside working hours (09:00–18:00).",
        )
    if minute not in (0, 30):
        raise HTTPException(status_code=400, detail="Appointments must start on the hour or half-hour.")

    # Check slot availability in DB
    existing = db.query(Appointment).filter(
        Appointment.appointment_date == target_date,
        Appointment.appointment_time == slot_time,
        Appointment.status == "CONFIRMED",
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Slot {time_str} on {target_date} is already booked.")

    booking_ref = generate_booking_ref(db)

    # Create Google Calendar event
    google_event_id = create_calendar_event(
        patient_name=payload.patient_name,
        appointment_date=target_date,
        appointment_time_str=time_str,
        reason_for_visit=payload.reason_for_visit,
    )

    appointment = Appointment(
        booking_ref=booking_ref,
        patient_name=payload.patient_name,
        phone=payload.phone,
        appointment_date=target_date,
        appointment_time=slot_time,
        reason_for_visit=payload.reason_for_visit,
        status="CONFIRMED",
        google_event_id=google_event_id,
        notes=payload.notes,
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)

    logger.info(f"Appointment created: {booking_ref} for {payload.patient_name} on {target_date} at {time_str}")
    return AppointmentResponse.from_orm_model(appointment)


@router.get("/appointments/{booking_ref}", response_model=AppointmentResponse)
def get_appointment(booking_ref: str, db: Session = Depends(get_db)):
    appointment = db.query(Appointment).filter(
        Appointment.booking_ref == booking_ref.upper()
    ).first()
    if not appointment:
        raise HTTPException(status_code=404, detail=f"Appointment {booking_ref} not found.")
    return AppointmentResponse.from_orm_model(appointment)


@router.patch("/appointments/{booking_ref}/cancel", response_model=AppointmentResponse)
def cancel_appointment(booking_ref: str, db: Session = Depends(get_db)):
    appointment = db.query(Appointment).filter(
        Appointment.booking_ref == booking_ref.upper()
    ).first()
    if not appointment:
        raise HTTPException(status_code=404, detail=f"Appointment {booking_ref} not found.")
    if appointment.status == "CANCELLED":
        raise HTTPException(status_code=400, detail="Appointment is already cancelled.")
    if appointment.status == "COMPLETED":
        raise HTTPException(status_code=400, detail="Cannot cancel a completed appointment.")

    # Cancel Google Calendar event
    if appointment.google_event_id:
        cancel_calendar_event(appointment.google_event_id)

    appointment.status = "CANCELLED"
    db.commit()
    db.refresh(appointment)

    logger.info(f"Appointment cancelled: {booking_ref}")
    return AppointmentResponse.from_orm_model(appointment)
