from datetime import date, time, datetime
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class AppointmentCreate(BaseModel):
    patient_name: str = Field(..., min_length=1, max_length=200)
    phone: str = Field(..., min_length=1, max_length=50)
    appointment_date: date
    appointment_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")  # HH:MM
    reason_for_visit: Optional[str] = None
    notes: Optional[str] = None


class AppointmentResponse(BaseModel):
    id: uuid.UUID
    booking_ref: str
    patient_name: str
    phone: str
    appointment_date: date
    appointment_time: str
    reason_for_visit: Optional[str] = None
    status: str
    google_event_id: Optional[str] = None
    created_at: Optional[datetime] = None
    notes: Optional[str] = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_model(cls, obj):
        return cls(
            id=obj.id,
            booking_ref=obj.booking_ref,
            patient_name=obj.patient_name,
            phone=obj.phone,
            appointment_date=obj.appointment_date,
            appointment_time=obj.appointment_time.strftime("%H:%M"),
            reason_for_visit=obj.reason_for_visit,
            status=obj.status,
            google_event_id=obj.google_event_id,
            created_at=obj.created_at,
            notes=obj.notes,
        )


class AvailabilityResponse(BaseModel):
    date: str
    available_slots: list[str]
    day_of_week: str
    is_open: bool
