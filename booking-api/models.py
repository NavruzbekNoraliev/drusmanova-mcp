import uuid
from sqlalchemy import Column, String, Date, Time, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from database import Base


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_ref = Column(String(10), unique=True, nullable=False)
    patient_name = Column(String(200), nullable=False)
    phone = Column(String(50), nullable=False)
    appointment_date = Column(Date, nullable=False)
    appointment_time = Column(Time, nullable=False)
    reason_for_visit = Column(Text, nullable=True)
    status = Column(String(20), default="CONFIRMED", nullable=False)
    google_event_id = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(Text, nullable=True)
