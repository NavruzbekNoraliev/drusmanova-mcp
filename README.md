# 🏥 Dr. Usmanova MCP Server + Booking API

ChatGPT MCP integration for [Dr. Mokhinur Usmanova](https://drusmanova.uz) — a Gynecologist & Obstetrician PhD in Tashkent, Uzbekistan.

Patients can book, check, and cancel appointments **directly from ChatGPT mobile** via the MCP protocol.

---

## Architecture

```
ChatGPT Mobile
    ↓  MCP protocol (HTTPS)
MCP Server (FastMCP, port 8090)
    ↓  internal HTTP calls
Booking API (FastAPI, port 8089)
    ↓               ↓
Postgres DB     Google Calendar API
(appointments)  (availability + events)
```

---

## Quick Start

### 1. Clone and configure

```bash
git clone git@github.com:NavruzbekNoraliev/drusmanova-mcp.git
cd drusmanova-mcp
cp .env.example .env
# Edit .env if needed (defaults work for local dev without Google Calendar)
```

### 2. Run with Docker Compose

```bash
docker compose up --build
```

This starts:
- **PostgreSQL** on port 5434
- **Booking API** on port 8089 (auto-runs Alembic migrations)
- **MCP Server** on port 8090

### 3. Verify it's working

```bash
# Health check
curl http://localhost:8089/health

# Check availability
curl "http://localhost:8089/api/availability?date=2026-03-20"

# MCP endpoint
curl http://localhost:8090/mcp
```

---

## Connect to ChatGPT

1. Open ChatGPT → **Settings** → **Apps & Connectors**
2. Click **Create** (or **Add Connector**)
3. Select **MCP**
4. Paste the URL: `http://localhost:8090/mcp`
   - For production, use your public HTTPS URL (e.g., via ngrok or a VPS)
5. ChatGPT will discover the tools automatically

> **For public access**, expose with ngrok:
> ```bash
> ngrok http 8090
> # Use the https://xxxx.ngrok.io/mcp URL in ChatGPT
> ```

---

## MCP Tools Reference

| Tool | Description |
|------|-------------|
| `get_doctor_info()` | Returns Dr. Usmanova's profile, specializations, contact info |
| `check_availability(date)` | Lists available 30-min slots for a given date (YYYY-MM-DD) |
| `book_appointment(patient_name, phone, date, time, reason)` | Books a slot, returns booking ref |
| `get_booking(booking_ref)` | Retrieves appointment details by ref (e.g. DR-7X3K) |
| `cancel_appointment(booking_ref)` | Cancels an appointment |

### Booking Rules
- Working hours: **Monday–Saturday, 09:00–18:00**
- Closed on **Sundays**
- Slot duration: **30 minutes**
- Booking ref format: `DR-XXXX` (e.g., `DR-7X3K`)

---

## Google Calendar Setup (optional)

Without Google Calendar credentials, the app runs in **mock mode** — all slots appear available and no calendar events are created. Perfect for development.

To enable real Google Calendar integration:

### Step 1: Create a Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project (or select existing)
3. Enable the **Google Calendar API**
4. Go to **IAM & Admin → Service Accounts → Create Service Account**
5. Grant it no special roles (not needed)
6. Create a JSON key and download it

### Step 2: Share your calendar with the service account

1. Open [Google Calendar](https://calendar.google.com)
2. Click the three dots next to your calendar → **Settings and sharing**
3. Under **Share with specific people**, add the service account email
4. Grant **Make changes to events** permission
5. Copy the **Calendar ID** from the calendar settings page

### Step 3: Configure credentials

```bash
# Encode credentials as base64
base64 -i service-account.json | tr -d '\n'
```

Add to `.env`:
```
GOOGLE_CREDENTIALS_JSON=<paste base64 here>
GOOGLE_CALENDAR_ID=your-calendar-id@group.calendar.google.com
```

---

## Booking API Endpoints

```
GET  /health
GET  /api/availability?date=YYYY-MM-DD
POST /api/appointments
     Body: { patient_name, phone, appointment_date, appointment_time, reason_for_visit }
GET  /api/appointments/{booking_ref}
PATCH /api/appointments/{booking_ref}/cancel
```

### Example: Create a booking

```bash
curl -X POST http://localhost:8089/api/appointments \
  -H "Content-Type: application/json" \
  -d '{
    "patient_name": "Dilnoza Karimova",
    "phone": "+998901234567",
    "appointment_date": "2026-03-20",
    "appointment_time": "10:00",
    "reason_for_visit": "Prenatal checkup"
  }'
```

Response:
```json
{
  "id": "...",
  "booking_ref": "DR-7X3K",
  "patient_name": "Dilnoza Karimova",
  "appointment_date": "2026-03-20",
  "appointment_time": "10:00",
  "status": "CONFIRMED",
  ...
}
```

---

## Submit to ChatGPT App Directory

To make this available to all ChatGPT users:

1. Deploy to a public server (VPS, Railway, Render, etc.) with HTTPS
2. Ensure your MCP endpoint is at `https://yourdomain.com/mcp`
3. Go to [ChatGPT Plugin Store / App Directory](https://chatgpt.com)
4. Submit your MCP connector for review
5. Provide:
   - Name: "Dr. Usmanova Booking"
   - Description: "Book appointments with Dr. Mokhinur Usmanova, Gynecologist & Obstetrician in Tashkent"
   - MCP URL: your HTTPS endpoint

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_DB` | `drusmanova` | Database name |
| `POSTGRES_USER` | `drusmanova` | Database user |
| `POSTGRES_PASSWORD` | `drusmanova` | Database password |
| `GOOGLE_CREDENTIALS_JSON` | _(empty)_ | Base64-encoded service account JSON |
| `GOOGLE_CALENDAR_ID` | `primary` | Google Calendar ID |
| `BOOKING_API_URL` | `http://booking-api:8089` | Internal URL for MCP → API calls |

---

## Development

Run locally without Docker:

```bash
# Terminal 1: Start Postgres
docker run -p 5434:5432 -e POSTGRES_DB=drusmanova -e POSTGRES_USER=drusmanova -e POSTGRES_PASSWORD=drusmanova postgres:16

# Terminal 2: Booking API
cd booking-api
pip install -r requirements.txt
DATABASE_URL=postgresql://drusmanova:drusmanova@localhost:5434/drusmanova python -m alembic upgrade head
DATABASE_URL=postgresql://drusmanova:drusmanova@localhost:5434/drusmanova uvicorn main:app --port 8089 --reload

# Terminal 3: MCP Server
cd mcp-server
pip install -r requirements.txt
BOOKING_API_URL=http://localhost:8089 python server.py
```

---

## License

MIT — feel free to adapt for other clinics.
