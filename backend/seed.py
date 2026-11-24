from datetime import date, datetime, time, timedelta
from sqlalchemy.orm import Session
from models import Doctor, Slot

DOCTORS = [
    ("Dr. Ananya Sharma", "Cardiologist", 14, 1200),
    ("Dr. Rahul Mehta", "Dermatologist", 11, 900),
    ("Dr. Priya Nair", "Neurologist", 16, 1500),
    ("Dr. Arjun Rao", "Orthopedic", 12, 1100),
    ("Dr. Sneha Kapoor", "Pediatrician", 10, 800),
    ("Dr. Vikram Singh", "General Physician", 18, 600),
    ("Dr. Neha Iyer", "Dentist", 9, 700),
    ("Dr. Karan Malhotra", "ENT Specialist", 13, 950),
]
TIMES = [("09:00", "09:30"), ("10:00", "10:30"), ("11:30", "12:00"), ("14:00", "14:30"), ("15:30", "16:00")]

def seed_database(db: Session):
    if db.query(Doctor).count() == 0:
        db.add_all([Doctor(name=n, speciality=s, experience=e, consultation_fee=f) for n,s,e,f in DOCTORS])
        db.commit()
    if db.query(Slot).count() == 0:
        start = date.today()
        for doctor in db.query(Doctor).all():
            for offset in range(7):
                day = start + timedelta(days=offset)
                if day.weekday() < 6:
                    for begin, finish in TIMES:
                        db.add(Slot(doctor_id=doctor.id, date=day, start_time=begin, end_time=finish))
        db.commit()
