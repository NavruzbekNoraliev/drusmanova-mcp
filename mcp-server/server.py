"""
Dr. Usmanova MCP Server
Exposes booking tools for ChatGPT integration via FastMCP.
"""
import os
from datetime import date, datetime
from typing import Optional

import httpx
from fastmcp import FastMCP

BOOKING_API = os.getenv("BOOKING_API_URL", "http://booking-api:8089")

mcp = FastMCP(
    name="Dr. Usmanova Booking",
    instructions="""You help patients book appointments with Dr. Mokhinur Usmanova, 
a Gynecologist & Obstetrician PhD based in Tashkent, Uzbekistan. 
Always check availability before booking. Collect: full name, phone number, 
preferred date (YYYY-MM-DD), and reason for visit.
Working hours: Monday–Saturday, 09:00–18:00. Closed Sundays.""",
)


@mcp.tool()
def get_doctor_info() -> dict:
    """Get information about Dr. Mokhinur Usmanova, her specializations, contact details, and working hours."""
    return {
        "name": "Dr. Mokhinur Usmanova",
        "title": "Gynecologist & Obstetrician, PhD",
        "specializations": [
            "Prenatal Care",
            "High-Risk Pregnancy",
            "Labor & Delivery",
            "Postpartum Care",
            "Gynecological Exams",
            "Contraception Counseling",
            "Menstrual Disorders",
            "Menopause Management",
            "Infertility Evaluation",
            "PCOS",
            "Uterine Fibroids",
            "Colposcopy & Cervical Procedures",
        ],
        "languages": ["Uzbek", "Russian", "English"],
        "location": "Tashkent, Uzbekistan",
        "website": "https://drusmanova.uz",
        "working_hours": "Monday–Saturday, 09:00–18:00",
        "contact": "+998 90 802 12 21",
        "telegram": "https://t.me/drusmanova",
        "booking_note": "Appointments are 30 minutes. Please arrive 5 minutes early.",
    }


@mcp.tool()
def check_availability(date: str) -> str:
    """
    Check available appointment slots for a given date.
    
    Args:
        date: Date in ISO format YYYY-MM-DD (e.g., 2026-03-20)
    
    Returns:
        A message listing available time slots or explaining why none are available.
    """
    # Validate date format
    try:
        target = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        return f"❌ Invalid date format '{date}'. Please use YYYY-MM-DD (e.g., 2026-03-20)."

    # Check if date is in the past
    if target < datetime.now().date():
        return f"❌ {date} is in the past. Please choose a future date."

    # Check if Sunday
    if target.weekday() == 6:
        return f"🚫 Dr. Usmanova's clinic is closed on Sundays. Please choose a Monday–Saturday date."

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(f"{BOOKING_API}/api/availability", params={"date": date})
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as e:
        return f"❌ Could not fetch availability: {e.response.text}"
    except Exception as e:
        return f"❌ Could not connect to booking service: {str(e)}"

    slots = data.get("available_slots", [])
    day_name = data.get("day_of_week", target.strftime("%A"))
    is_open = data.get("is_open", True)

    if not is_open:
        return f"🚫 The clinic is closed on {day_name}s."

    if not slots:
        return f"😔 No available slots for {date} ({day_name}). All appointments are booked. Please try another date."

    slots_str = ", ".join(slots)
    return (
        f"📅 Available slots for {date} ({day_name}):\n"
        f"{slots_str}\n\n"
        f"To book, provide your full name, phone number, preferred time, and reason for visit."
    )


@mcp.tool()
def book_appointment(
    patient_name: str,
    phone: str,
    date: str,
    time: str,
    reason: str,
) -> str:
    """
    Book an appointment with Dr. Usmanova.
    
    Args:
        patient_name: Full name of the patient
        phone: Patient's phone number (with country code if possible)
        date: Appointment date in YYYY-MM-DD format
        time: Appointment time in HH:MM 24-hour format (e.g., 09:00, 14:30)
        reason: Reason for the visit / chief complaint
    
    Returns:
        Confirmation message with booking reference, or error details.
    """
    payload = {
        "patient_name": patient_name,
        "phone": phone,
        "appointment_date": date,
        "appointment_time": time,
        "reason_for_visit": reason,
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(f"{BOOKING_API}/api/appointments", json=payload)
            if response.status_code == 409:
                return (
                    f"⚠️ Sorry, the slot at {time} on {date} was just taken. "
                    f"Please check availability again and choose another time."
                )
            if response.status_code == 400:
                detail = response.json().get("detail", "Invalid request")
                return f"❌ Booking failed: {detail}"
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as e:
        return f"❌ Booking error: {e.response.text}"
    except Exception as e:
        return f"❌ Could not connect to booking service: {str(e)}"

    booking_ref = data["booking_ref"]
    appt_date = data["appointment_date"]
    appt_time = data["appointment_time"]
    name = data["patient_name"]

    return (
        f"✅ Appointment confirmed!\n\n"
        f"📋 Booking Reference: **{booking_ref}**\n"
        f"👤 Patient: {name}\n"
        f"📅 Date: {appt_date}\n"
        f"🕐 Time: {appt_time}\n"
        f"📞 Phone: {data['phone']}\n"
        f"🩺 Reason: {data.get('reason_for_visit', 'N/A')}\n\n"
        f"Please save your booking reference **{booking_ref}** — you'll need it to view or cancel your appointment.\n"
        f"Please arrive 5 minutes early. Dr. Usmanova's clinic: https://drusmanova.uz"
    )


@mcp.tool()
def get_booking(booking_ref: str) -> str:
    """
    Retrieve details of an existing appointment by booking reference.
    
    Args:
        booking_ref: The booking reference code (e.g., DR-7X3K)
    
    Returns:
        Full appointment details or an error message if not found.
    """
    ref = booking_ref.upper().strip()

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(f"{BOOKING_API}/api/appointments/{ref}")
            if response.status_code == 404:
                return f"❌ No appointment found with reference {ref}. Please double-check the code."
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as e:
        return f"❌ Error fetching booking: {e.response.text}"
    except Exception as e:
        return f"❌ Could not connect to booking service: {str(e)}"

    status_emoji = {"CONFIRMED": "✅", "CANCELLED": "❌", "COMPLETED": "🏥"}.get(data["status"], "📋")

    return (
        f"📋 Appointment Details\n\n"
        f"🔖 Booking Ref: {data['booking_ref']}\n"
        f"{status_emoji} Status: {data['status']}\n"
        f"👤 Patient: {data['patient_name']}\n"
        f"📞 Phone: {data['phone']}\n"
        f"📅 Date: {data['appointment_date']}\n"
        f"🕐 Time: {data['appointment_time']}\n"
        f"🩺 Reason: {data.get('reason_for_visit') or 'N/A'}\n"
        f"🗓️ Booked on: {data.get('created_at', 'N/A')[:10] if data.get('created_at') else 'N/A'}"
    )


@mcp.tool()
def cancel_appointment(booking_ref: str) -> str:
    """
    Cancel an existing appointment by booking reference.
    
    Args:
        booking_ref: The booking reference code (e.g., DR-7X3K)
    
    Returns:
        Confirmation of cancellation or an error message.
    """
    ref = booking_ref.upper().strip()

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.patch(f"{BOOKING_API}/api/appointments/{ref}/cancel")
            if response.status_code == 404:
                return f"❌ No appointment found with reference {ref}."
            if response.status_code == 400:
                detail = response.json().get("detail", "Cannot cancel.")
                return f"⚠️ {detail}"
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as e:
        return f"❌ Error cancelling booking: {e.response.text}"
    except Exception as e:
        return f"❌ Could not connect to booking service: {str(e)}"

    return (
        f"✅ Appointment {data['booking_ref']} has been cancelled.\n\n"
        f"👤 Patient: {data['patient_name']}\n"
        f"📅 Was scheduled for: {data['appointment_date']} at {data['appointment_time']}\n\n"
        f"If you'd like to rebook, please check availability for another date."
    )


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8090, path="/mcp")
