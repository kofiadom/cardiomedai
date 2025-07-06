from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime

# User schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: str
    age: int
    gender: str
    height: float
    weight: float
    medical_conditions: Optional[str] = None
    medications: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    medical_conditions: Optional[str] = None
    medications: Optional[str] = None

class User(UserBase):
    id: int

    class Config:
        orm_mode = True

# Blood Pressure schemas
class BloodPressureBase(BaseModel):
    systolic: int
    diastolic: int
    pulse: int
    notes: Optional[str] = None
    device_id: Optional[str] = None
    interpretation: Optional[str] = None

class BloodPressureCreate(BloodPressureBase):
    pass

class BloodPressure(BloodPressureBase):
    id: int
    user_id: int
    reading_time: datetime

    class Config:
        orm_mode = True

# Device Upload schema for future OCR implementation
class DeviceImageUpload(BaseModel):
    image_data: str  # Base64 encoded image

# Health Advisor schemas (Community Health Worker)
class HealthAdvisorRequest(BaseModel):
    user_id: int
    message: str = "Good morning! How am I doing with my blood pressure this week?"

class HealthAdvisorResponse(BaseModel):
    user_id: int
    request_message: str
    advisor_response: str
    agent_id: Optional[str] = None
    thread_id: Optional[str] = None
    status: str = "completed"

# Knowledge Agent schemas (RAG-based hypertension education)
class KnowledgeAgentRequest(BaseModel):
    user_id: Optional[int] = None  # Optional - can be used for personalization
    question: str
    include_user_context: bool = False  # Whether to include user's BP data for context

class KnowledgeAgentResponse(BaseModel):
    question: str
    answer: str
    sources: Optional[List[str]] = None  # File sources used for the answer
    user_id: Optional[int] = None
    agent_id: Optional[str] = None
    thread_id: Optional[str] = None
    vector_store_id: Optional[str] = None
    status: str = "completed"

# Medication Reminder schemas
class MedicationScheduleItem(BaseModel):
    datetime: datetime
    dosage: str

class MedicationReminderBase(BaseModel):
    name: str
    dosage: str
    schedule_datetime: datetime
    schedule_dosage: str
    notes: Optional[str] = None

class MedicationReminderCreate(MedicationReminderBase):
    pass

class MedicationReminderUpdate(BaseModel):
    name: Optional[str] = None
    dosage: Optional[str] = None
    schedule_datetime: Optional[datetime] = None
    schedule_dosage: Optional[str] = None
    is_taken: Optional[bool] = None
    notes: Optional[str] = None

class MedicationReminder(MedicationReminderBase):
    id: int
    user_id: int
    is_taken: bool
    created_at: datetime

    class Config:
        from_attributes = True

# OCR Medication Extraction schemas
class MedicationOCRExtraction(BaseModel):
    """
    Structured model for medication prescription details extracted from images.
    """
    name: str = Field(description="The name of the medication")
    dosage: str = Field(description="The composition or strength of the medication")
    schedule: List[MedicationScheduleItem] = Field(description="List of scheduled doses with datetime and dosage")
    interpretation: str = Field(description="Explanation of what was observed in the image and how the prescription information was interpreted")

class MedicationOCRResponse(BaseModel):
    """Response from OCR extraction with extracted data and approval status."""
    extracted_data: MedicationOCRExtraction
    total_reminders: int
    message: str

# BP Check Reminder schemas
class BPCheckReminderBase(BaseModel):
    reminder_datetime: datetime
    notes: Optional[str] = None

class BPCheckReminderCreate(BPCheckReminderBase):
    bp_category: Optional[str] = "manual"  # Default to "manual" for user-created reminders

class BPCheckReminderUpdate(BaseModel):
    reminder_datetime: Optional[datetime] = None
    bp_category: Optional[str] = None
    notes: Optional[str] = None

class BPCheckReminder(BPCheckReminderBase):
    id: int
    user_id: int
    bp_category: str
    is_completed: bool
    created_at: datetime

    class Config:
        from_attributes = True

# BP Reminder Generation schemas
class BPReminderScheduleRequest(BaseModel):
    user_id: int
    systolic: int
    diastolic: int
    first_check_time: Optional[datetime] = None  # If None, use current time
    preferred_morning_time: Optional[str] = "07:00"  # HH:MM format
    preferred_evening_time: Optional[str] = "19:00"  # HH:MM format

class BPReminderScheduleResponse(BaseModel):
    category: str
    category_description: str
    total_reminders: int
    advice: Optional[str] = None
    reminders: List[BPCheckReminder]

# Doctor Appointment Reminder schemas
class DoctorAppointmentReminderBase(BaseModel):
    appointment_datetime: datetime
    doctor_name: str
    appointment_type: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None

class DoctorAppointmentReminderCreate(DoctorAppointmentReminderBase):
    pass

class DoctorAppointmentReminderUpdate(BaseModel):
    appointment_datetime: Optional[datetime] = None
    doctor_name: Optional[str] = None
    appointment_type: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None

class DoctorAppointmentReminder(DoctorAppointmentReminderBase):
    id: int
    user_id: int
    is_completed: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Workout Reminder schemas
class WorkoutReminderBase(BaseModel):
    workout_datetime: datetime
    workout_type: str
    duration_minutes: Optional[int] = None
    location: Optional[str] = None
    notes: Optional[str] = None

class WorkoutReminderCreate(WorkoutReminderBase):
    pass

class WorkoutReminderUpdate(BaseModel):
    workout_datetime: Optional[datetime] = None
    workout_type: Optional[str] = None
    duration_minutes: Optional[int] = None
    location: Optional[str] = None
    notes: Optional[str] = None

class WorkoutReminder(WorkoutReminderBase):
    id: int
    user_id: int
    is_completed: bool
    created_at: datetime

    class Config:
        from_attributes = True
