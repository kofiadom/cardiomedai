from pydantic import BaseModel, EmailStr, validator
from typing import List, Optional
from datetime import datetime, date

# Enhanced User schemas
class EnhancedUserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: str
    age: int
    gender: str
    height: float
    weight: float
    
    # Medical information
    medical_conditions: Optional[str] = None
    medications: Optional[str] = None
    
    # BP targets
    target_systolic: Optional[int] = 120
    target_diastolic: Optional[int] = 80
    
    # Lifestyle factors
    smoking_status: Optional[str] = None
    alcohol_consumption: Optional[str] = None
    exercise_frequency: Optional[str] = None
    stress_level: Optional[int] = None
    sleep_hours: Optional[float] = None
    
    # Family history
    family_history_hypertension: Optional[bool] = False
    family_history_heart_disease: Optional[bool] = False
    family_history_stroke: Optional[bool] = False
    family_history_diabetes: Optional[bool] = False
    
    # Emergency contacts
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None
    
    # Healthcare provider
    doctor_name: Optional[str] = None
    doctor_phone: Optional[str] = None
    last_checkup_date: Optional[date] = None
    next_appointment_date: Optional[date] = None
    
    # Preferences
    preferred_measurement_time: Optional[str] = None
    reminder_frequency: Optional[str] = "Daily"
    language_preference: Optional[str] = "en"
    timezone: Optional[str] = None
    
    # Risk factors
    diabetes_status: Optional[bool] = False
    kidney_disease: Optional[bool] = False
    heart_disease: Optional[bool] = False
    previous_stroke: Optional[bool] = False

    @validator('age')
    def validate_age(cls, v):
        if v < 1 or v > 120:
            raise ValueError('Age must be between 1 and 120')
        return v

    @validator('height')
    def validate_height(cls, v):
        if v < 50 or v > 250:
            raise ValueError('Height must be between 50 and 250 cm')
        return v

    @validator('weight')
    def validate_weight(cls, v):
        if v < 20 or v > 500:
            raise ValueError('Weight must be between 20 and 500 kg')
        return v

    @validator('stress_level')
    def validate_stress_level(cls, v):
        if v is not None and (v < 1 or v > 10):
            raise ValueError('Stress level must be between 1 and 10')
        return v

class EnhancedUserCreate(EnhancedUserBase):
    password: str

class EnhancedUserUpdate(BaseModel):
    full_name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    medical_conditions: Optional[str] = None
    medications: Optional[str] = None
    target_systolic: Optional[int] = None
    target_diastolic: Optional[int] = None
    smoking_status: Optional[str] = None
    alcohol_consumption: Optional[str] = None
    exercise_frequency: Optional[str] = None
    stress_level: Optional[int] = None
    sleep_hours: Optional[float] = None
    family_history_hypertension: Optional[bool] = None
    family_history_heart_disease: Optional[bool] = None
    family_history_stroke: Optional[bool] = None
    family_history_diabetes: Optional[bool] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None
    doctor_name: Optional[str] = None
    doctor_phone: Optional[str] = None
    last_checkup_date: Optional[date] = None
    next_appointment_date: Optional[date] = None
    preferred_measurement_time: Optional[str] = None
    reminder_frequency: Optional[str] = None
    language_preference: Optional[str] = None
    timezone: Optional[str] = None
    diabetes_status: Optional[bool] = None
    kidney_disease: Optional[bool] = None
    heart_disease: Optional[bool] = None
    previous_stroke: Optional[bool] = None

class EnhancedUser(EnhancedUserBase):
    id: int
    bmi: Optional[float] = None
    risk_score: Optional[int] = None
    last_reading_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        orm_mode = True

# Risk Assessment Schema
class RiskAssessment(BaseModel):
    user_id: int
    risk_score: int  # 1-100
    risk_level: str  # Low/Moderate/High/Very High
    risk_factors: List[str]
    recommendations: List[str]
    next_assessment_date: date

# Health Goals Schema
class HealthGoal(BaseModel):
    goal_type: str  # BP_Target/Weight_Loss/Exercise/Medication_Adherence
    target_value: float
    current_value: float
    target_date: date
    progress_percentage: float
    is_achieved: bool