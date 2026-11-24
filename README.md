# MediCare AI

A healthcare appointment dashboard with a FastAPI + SQLite backend, a Pipecat WebRTC voice worker, and a React/TypeScript frontend. Voice keys are server-side only. The dashboard includes demo text mode and a direct booking form so the appointment workflow can be demonstrated without paid AI credentials.

## Build status

- Backend APIs, seeded doctors/slots, booking, cancellation, validation, and conflict prevention are implemented and smoke checked.
- The React dashboard builds successfully and consumes the live API.
- Pipecat 1.17.0, provider packages, SmallWebRTC, and Silero install under Python 3.11. Worker/provider imports and all three function tool schemas are verified.
- A live provider call still requires Gemini and ElevenLabs credentials in `backend/.env`; the voice path has not been tested against external provider accounts.

## Run locally

Prerequisites: Node.js 20.19+ or 22.12+, Python 3.11+ (Pipecat requires Python 3.11+). Python 3.11.18 is installed in the workspace environment.

```bash
# Terminal 1 — backend API
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --port 8000

# Terminal 2 — dashboard
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. SQLite data is stored in `backend/medicare.db`; eight doctors and a week of weekday slots are seeded on startup. API docs: http://localhost:8000/docs.

For API test tooling, install `pip install -r requirements-dev.txt` in the backend environment.

## Enable Pipecat voice

Use Python 3.11 or newer. Add these to `backend/.env`:

```dotenv
GEMINI_API_KEY=...
ELEVENLABS_API_KEY=...
ELEVENLABS_VOICE_ID=...
```

Install the pinned Pipecat 1.17.0 voice dependencies and run the Pipecat SmallWebRTC worker:

```bash
cd backend
python -m pip install -r requirements-voice.txt
python -m pipeline.bot -t webrtc
```

The browser uses Pipecat's matching `@pipecat-ai/client-js` and `@pipecat-ai/small-webrtc-transport` packages. SmallWebRTC's runner serves the bot on port 7860. Keys remain on the server. Voice calls use ElevenLabs real-time STT and TTS, Gemini, and Silero VAD. `GEMINI_API_KEY`, `ELEVENLABS_API_KEY`, and `ELEVENLABS_VOICE_ID` are required. Without credentials and the worker, the app displays demo text mode and never claims an audio connection.

## API

- `GET /api/doctors`
- `GET /api/doctors/{doctor_id}/availability`
- `GET /api/appointments` and `GET /api/appointments/phone/{phone_number}`
- `POST /api/appointments/book` and `POST /api/appointments/cancel`
- `GET /api/dashboard/stats`, `GET /api/health`

Bookings validate phone numbers and reference an actual unbooked slot. The database enforces unique slot use; the appointment table also has a unique slot ID to reject concurrent bookings. Cancellation looks up by the provided number and appointment ID, and refuses a mismatch.

## Voice safety behavior

The voice system prompt requires the receptionist to repeat and obtain verbal confirmation of the phone number. The tool signatures also require `phone_confirmed=true` before any booking or cancellation can proceed. Appointment tools only return success after the database commit. The assistant does not use login, OTP, browser identity, or caller ID.

## Demo recording outline (3 minutes)

1. Show the dashboard, live doctor directory, availability count, and appointment list.
2. Use the booking form: enter patient details, select a doctor and real slot, confirm, and show the new row and updated counts.
3. Cancel that appointment from its row, supply the same phone number, and show the cancelled status and released availability.
4. Open Try call and show demo text mode when keys are not set. If credentials are set, start the Pipecat worker first and demo the spoken confirmation and live voice conversation.

## Pipeline

Browser microphone → Pipecat SmallWebRTC → ElevenLabs real-time STT → Gemini with database-backed availability/booking/cancellation tools → ElevenLabs streaming TTS → browser audio. Demo text and booking form both call the same FastAPI/SQLite business logic.
