from __future__ import annotations

from datetime import date, datetime
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship, Mapped, mapped_column
from database import Base

class Doctor(Base):
    __tablename__ = "doctors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    speciality: Mapped[str] = mapped_column(String(80), nullable=False)
    experience: Mapped[int] = mapped_column(Integer, nullable=False)
    consultation_fee: Mapped[int] = mapped_column(Integer, nullable=False)
    availability: Mapped[str] = mapped_column(String(30), default="Available")
    slots = relationship("Slot", back_populates="doctor", cascade="all, delete-orphan")

class Slot(Base):
    __tablename__ = "slots"
    __table_args__ = (UniqueConstraint("doctor_id", "date", "start_time", name="uq_doctor_slot"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    start_time: Mapped[str] = mapped_column(String(5), nullable=False)
    end_time: Mapped[str] = mapped_column(String(5), nullable=False)
    is_booked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    doctor = relationship("Doctor", back_populates="slots")

class Appointment(Base):
    __tablename__ = "appointments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_name: Mapped[str] = mapped_column(String(120), nullable=False)
    patient_phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), nullable=False)
    slot_id: Mapped[int] = mapped_column(ForeignKey("slots.id"), nullable=False, unique=True)
    appointment_date: Mapped[date] = mapped_column(Date, nullable=False)
    appointment_time: Mapped[str] = mapped_column(String(5), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="confirmed")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    doctor = relationship("Doctor")
