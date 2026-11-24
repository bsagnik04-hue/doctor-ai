from datetime import date
from sqlalchemy.orm import Session
from models import Doctor, Slot
from services.appointments import book, cancel

def check_doctor_availability(db: Session, doctor_name: str = None, speciality: str = None, appointment_date: date = None):
    query = db.query(Doctor)
    if doctor_name: query = query.filter(Doctor.name.ilike("%" + doctor_name + "%"))
    if speciality: query = query.filter(Doctor.speciality.ilike("%" + speciality + "%"))
    doctors = query.all()
    result = []
    for doctor in doctors:
        slots = db.query(Slot).filter_by(doctor_id=doctor.id, is_booked=False)
        if appointment_date: slots = slots.filter(Slot.date == appointment_date)
        result.append({"doctor": doctor, "slots": slots.order_by(Slot.date, Slot.start_time).all()})
    return result

__all__ = ["check_doctor_availability", "book", "cancel"]
