from sqlalchemy import Column, ForeignKey, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
import datetime

from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(255))
    full_name = Column(String(100))
    age = Column(Integer)
    gender = Column(String(10))
    height = Column(Float)  # in cm
    weight = Column(Float)  # in kg
    medical_conditions = Column(Text, nullable=True)
    medications = Column(Text, nullable=True)

    blood_pressure_readings = relationship("BloodPressure", back_populates="user")
    medication_reminders = relationship("MedicationReminder", back_populates="user")
    bp_check_reminders = relationship("BPCheckReminder", back_populates="user")
    doctor_appointment_reminders = relationship("DoctorAppointmentReminder", back_populates="user")
    workout_reminders = relationship("WorkoutReminder", back_populates="user")


class BloodPressure(Base):
    __tablename__ = "blood_pressure_readings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    systolic = Column(Integer)
    diastolic = Column(Integer)
    pulse = Column(Integer)
    reading_time = Column(DateTime, default=datetime.datetime.utcnow)
    notes = Column(Text, nullable=True)
    interpretation = Column(String(500), nullable=True)

    user = relationship("User", back_populates="blood_pressure_readings")


class MedicationReminder(Base):
    __tablename__ = "medication_reminders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String(100), nullable=False)  # Medication name
    dosage = Column(String(100), nullable=False)  # Dosage description
    schedule_datetime = Column(DateTime, nullable=False)  # When to take the medication
    schedule_dosage = Column(String(100), nullable=False)  # How much to take at this time
    is_taken = Column(Boolean, default=False)  # Whether this dose has been taken
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    notes = Column(Text, nullable=True)  # Optional notes

    user = relationship("User", back_populates="medication_reminders")


class BPCheckReminder(Base):
    __tablename__ = "bp_check_reminders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    reminder_datetime = Column(DateTime, nullable=False)  # When to check BP
    bp_category = Column(String(20), nullable=False)  # normal, elevated, stage_1, stage_2, crisis
    is_completed = Column(Boolean, default=False)  # Whether BP was checked
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    notes = Column(Text, nullable=True)  # Additional context

    user = relationship("User", back_populates="bp_check_reminders")


class DoctorAppointmentReminder(Base):
    __tablename__ = "doctor_appointment_reminders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    appointment_datetime = Column(DateTime, nullable=False)  # When the appointment is scheduled
    doctor_name = Column(String(100), nullable=False)  # Name of the doctor
    appointment_type = Column(String(50), nullable=True)  # Type of appointment (checkup, consultation, etc.)
    location = Column(String(200), nullable=True)  # Clinic/hospital location
    is_completed = Column(Boolean, default=False)  # Whether appointment was attended
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    notes = Column(Text, nullable=True)  # Additional notes

    user = relationship("User", back_populates="doctor_appointment_reminders")


class WorkoutReminder(Base):
    __tablename__ = "workout_reminders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    workout_datetime = Column(DateTime, nullable=False)  # When to workout
    workout_type = Column(String(50), nullable=False)  # Type of workout (cardio, strength, yoga, etc.)
    duration_minutes = Column(Integer, nullable=True)  # Planned duration in minutes
    location = Column(String(100), nullable=True)  # Gym, home, park, etc.
    is_completed = Column(Boolean, default=False)  # Whether workout was completed
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    notes = Column(Text, nullable=True)  # Additional notes

    user = relationship("User", back_populates="workout_reminders")