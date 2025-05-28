from pydantic import BaseModel, EmailStr
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