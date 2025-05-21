from sqlalchemy import Column, ForeignKey, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import relationship
import datetime

from .database import Base

class User(Base):
    __tablename__ = "users"

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

    blood_pressure_readings = relationship("BloodPressure", back_populates="user")


class BloodPressure(Base):
    __tablename__ = "blood_pressure_readings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    systolic = Column(Integer)
    diastolic = Column(Integer)
    pulse = Column(Integer)
    reading_time = Column(DateTime, default=datetime.datetime.utcnow)
    notes = Column(Text, nullable=True)
    device_id = Column(String, nullable=True)
    interpretation = Column(String, nullable=True)

    user = relationship("User", back_populates="blood_pressure_readings")