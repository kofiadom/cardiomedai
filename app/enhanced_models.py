from sqlalchemy import Column, ForeignKey, Integer, String, Float, DateTime, Text, Boolean, Date
from sqlalchemy.orm import relationship
import datetime

from .database import Base

class EnhancedUser(Base):
    __tablename__ = "users"

    # Existing fields
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    age = Column(Integer)
    gender = Column(String)
    height = Column(Float)  # in cm
    weight = Column(Float)  # in kg
    medical_conditions = Column(Text, nullable=True)
    medications = Column(Text, nullable=True)

    # Enhanced health profile fields
    target_systolic = Column(Integer, default=120)  # Target BP goals
    target_diastolic = Column(Integer, default=80)
    
    # Lifestyle factors
    smoking_status = Column(String, nullable=True)  # Never/Former/Current
    alcohol_consumption = Column(String, nullable=True)  # None/Light/Moderate/Heavy
    exercise_frequency = Column(String, nullable=True)  # Daily/Weekly/Rarely/Never
    stress_level = Column(Integer, nullable=True)  # 1-10 scale
    sleep_hours = Column(Float, nullable=True)  # Average hours per night
    
    # Family history
    family_history_hypertension = Column(Boolean, default=False)
    family_history_heart_disease = Column(Boolean, default=False)
    family_history_stroke = Column(Boolean, default=False)
    family_history_diabetes = Column(Boolean, default=False)
    
    # Emergency contacts
    emergency_contact_name = Column(String, nullable=True)
    emergency_contact_phone = Column(String, nullable=True)
    emergency_contact_relationship = Column(String, nullable=True)
    
    # Healthcare provider info
    doctor_name = Column(String, nullable=True)
    doctor_phone = Column(String, nullable=True)
    last_checkup_date = Column(Date, nullable=True)
    next_appointment_date = Column(Date, nullable=True)
    
    # Preferences and settings
    preferred_measurement_time = Column(String, nullable=True)  # Morning/Evening/Both
    reminder_frequency = Column(String, default="Daily")  # Daily/Weekly/Custom
    notification_preferences = Column(Text, nullable=True)  # JSON string
    language_preference = Column(String, default="en")
    timezone = Column(String, nullable=True)
    
    # Risk factors
    diabetes_status = Column(Boolean, default=False)
    kidney_disease = Column(Boolean, default=False)
    heart_disease = Column(Boolean, default=False)
    previous_stroke = Column(Boolean, default=False)
    
    # Calculated fields (updated automatically)
    bmi = Column(Float, nullable=True)  # Calculated from height/weight
    risk_score = Column(Integer, nullable=True)  # Calculated risk assessment
    last_reading_date = Column(DateTime, nullable=True)
    
    # Account metadata
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    is_active = Column(Boolean, default=True)

    blood_pressure_readings = relationship("BloodPressure", back_populates="user")