import re
from datetime import date
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from models import Appointment, Doctor, Slot

def normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    if not 10 <= len(digits) <= 15:
        raise ValueError("Enter a valid phone number with 10 to 15 digits.")
    return digits

def book(db: Session, patient_name: str, patient_phone: str, doctor_id: int, appointment_date: date, appointment_time: str):
    phone = normalize_phone(patient_phone)
    if not patient_name.strip(): raise ValueError("Patient name is required.")
    slot = db.query(Slot).filter_by(doctor_id=doctor_id, date=appointment_date, start_time=appointment_time, is_booked=False).with_for_update().first()
    if slot is None: raise ValueError("That slot is no longer available. Please choose another time.")
    slot.is_booked = True
    appt = Appointment(patient_name=patient_name.strip(), patient_phone=phone, doctor_id=doctor_id, slot_id=slot.id, appointment_date=slot.date, appointment_time=slot.start_time, status="confirmed")
    db.add(appt)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("That slot was just booked. Please choose another time.")
    db.refresh(appt)
    return appt

def cancel(db: Session, patient_phone: str, appointment_id: int = None):
    phone = normalize_phone(patient_phone)
    query = db.query(Appointment).filter_by(patient_phone=phone, status="confirmed")
    if appointment_id is not None: query = query.filter_by(id=appointment_id)
    matches = query.order_by(Appointment.appointment_date, Appointment.appointment_time).all()
    if len(matches) == 0: raise ValueError("No confirmed appointment was found for that phone number.")
    if len(matches) > 1 and appointment_id is None: return {"needs_selection": True, "appointments": matches}
    appt = matches[0]
    appt.status = "cancelled"
    slot = db.query(Slot).filter_by(id=appt.slot_id).first()
    if slot: slot.is_booked = False
    db.commit()
    db.refresh(appt)
    return appt
