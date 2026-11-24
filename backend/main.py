from datetime import date
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from config import settings
from database import Base, engine, get_db
from models import Appointment, Doctor, Slot
from seed import seed_database
from services.appointments import book, cancel, normalize_phone

Base.metadata.create_all(bind=engine)
app = FastAPI(title="MediCare AI", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=list({settings.frontend_origin, "http://localhost:5173", "http://127.0.0.1:5173"}), allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
with next(get_db()) as db: seed_database(db)

class BookingRequest(BaseModel):
    patient_name: str = Field(min_length=2, max_length=120)
    patient_phone: str
    doctor_id: int
    appointment_date: date
    appointment_time: str = Field(pattern=r"^\d{2}:\d{2}$")

class CancelRequest(BaseModel):
    patient_phone: str
    appointment_id: Optional[int] = None

def appointment_json(a):
    return {"id": a.id, "patient_name": a.patient_name, "patient_phone": a.patient_phone, "doctor_id": a.doctor_id, "doctor_name": a.doctor.name, "speciality": a.doctor.speciality, "appointment_date": a.appointment_date.isoformat(), "appointment_time": a.appointment_time, "status": a.status, "created_at": a.created_at.isoformat()}

@app.get("/api/health")
def health():
    return {"status": "ok", "voice_configured": bool(settings.gemini_api_key and settings.elevenlabs_api_key and settings.elevenlabs_voice_id)}

@app.get("/api/doctors")
def doctors(db: Session = Depends(get_db)):
    return [{"id": d.id, "name": d.name, "speciality": d.speciality, "experience": d.experience, "consultation_fee": d.consultation_fee, "availability": d.availability, "next_available": (db.query(Slot).filter_by(doctor_id=d.id, is_booked=False).order_by(Slot.date, Slot.start_time).first().date.isoformat() if db.query(Slot).filter_by(doctor_id=d.id, is_booked=False).first() else None)} for d in db.query(Doctor).all()]

@app.get("/api/doctors/{doctor_id}/availability")
def doctor_availability(doctor_id: int, appointment_date: Optional[date] = None, db: Session = Depends(get_db)):
    doctor = db.get(Doctor, doctor_id)
    if not doctor: raise HTTPException(404, "Doctor not found")
    q = db.query(Slot).filter_by(doctor_id=doctor_id, is_booked=False)
    if appointment_date: q = q.filter(Slot.date == appointment_date)
    return {"doctor": {"id": doctor.id, "name": doctor.name, "speciality": doctor.speciality}, "slots": [{"id": s.id, "date": s.date.isoformat(), "start_time": s.start_time, "end_time": s.end_time} for s in q.order_by(Slot.date, Slot.start_time).all()]}

@app.get("/api/appointments")
def appointments(status: Optional[str] = None, search: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Appointment)
    if status: q = q.filter(Appointment.status == status)
    if search: q = q.filter(Appointment.patient_name.ilike("%" + search + "%"))
    return [appointment_json(a) for a in q.order_by(Appointment.created_at.desc()).all()]

@app.get("/api/appointments/phone/{phone_number}")
def appointments_by_phone(phone_number: str, db: Session = Depends(get_db)):
    try: phone = normalize_phone(phone_number)
    except ValueError as e: raise HTTPException(422, str(e))
    return [appointment_json(a) for a in db.query(Appointment).filter_by(patient_phone=phone).order_by(Appointment.appointment_date).all()]

@app.post("/api/appointments/book", status_code=201)
def book_api(payload: BookingRequest, db: Session = Depends(get_db)):
    if not db.get(Doctor, payload.doctor_id): raise HTTPException(404, "Doctor not found")
    try: payload.patient_phone = normalize_phone(payload.patient_phone)
    except ValueError as e: raise HTTPException(422, str(e))
    try: return appointment_json(book(db, **payload.model_dump()))
    except ValueError as e: raise HTTPException(409, str(e))

@app.post("/api/appointments/cancel")
def cancel_api(payload: CancelRequest, db: Session = Depends(get_db)):
    try: payload.patient_phone = normalize_phone(payload.patient_phone)
    except ValueError as e: raise HTTPException(422, str(e))
    try: result = cancel(db, payload.patient_phone, payload.appointment_id)
    except ValueError as e: raise HTTPException(404, str(e))
    if isinstance(result, dict): return {"needs_selection": True, "appointments": [appointment_json(a) for a in result["appointments"]]}
    return appointment_json(result)

@app.get("/api/dashboard/stats")
def stats(db: Session = Depends(get_db)):
    today = date.today()
    return {"total_doctors": db.query(Doctor).count(), "available_slots": db.query(Slot).filter_by(is_booked=False).count(), "todays_appointments": db.query(Appointment).filter_by(appointment_date=today, status="confirmed").count(), "confirmed_bookings": db.query(Appointment).filter_by(status="confirmed").count()}

@app.get("/api/voice/config")
def voice_config():
    ready = bool(settings.gemini_api_key and settings.elevenlabs_api_key and settings.elevenlabs_voice_id)
    return {"configured": ready, "transport": "small-webrtc", "message": "Voice requires Gemini and ElevenLabs credentials." if not ready else "Voice provider configured; start the Pipecat service."}
