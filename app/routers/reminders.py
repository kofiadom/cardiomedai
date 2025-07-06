from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import base64
from pydantic import BaseModel

from .. import models, schemas
from ..database import get_db
from ..medication_ocr import MedicationOCRProcessor
from ..bp_reminder_service import BPReminderService

router = APIRouter(
    prefix="/reminders",
    responses={404: {"description": "Not found"}},
)

# Initialize OCR processor
medication_ocr_processor = MedicationOCRProcessor()

@router.post("/", response_model=schemas.MedicationReminder, tags=["Medication Reminders"])
def create_reminder(
    reminder: schemas.MedicationReminderCreate,
    user_id: int,
    db: Session = Depends(get_db)
):
    """Create a new medication reminder manually."""
    # Verify the user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db_reminder = models.MedicationReminder(
        user_id=user_id,
        name=reminder.name,
        dosage=reminder.dosage,
        schedule_datetime=reminder.schedule_datetime,
        schedule_dosage=reminder.schedule_dosage,
        notes=reminder.notes
    )
    db.add(db_reminder)
    db.commit()
    db.refresh(db_reminder)
    return db_reminder

@router.get("/{user_id}", response_model=List[schemas.MedicationReminder], tags=["Medication Reminders"])
def get_user_reminders(
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    include_taken: bool = True,
    db: Session = Depends(get_db)
):
    """Get all medication reminders for a user."""
    # Verify the user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    query = db.query(models.MedicationReminder).filter(models.MedicationReminder.user_id == user_id)
    
    if not include_taken:
        query = query.filter(models.MedicationReminder.is_taken == False)
    
    reminders = query.order_by(models.MedicationReminder.schedule_datetime).offset(skip).limit(limit).all()
    return reminders

@router.get("/reminder/{reminder_id}", response_model=schemas.MedicationReminder, tags=["Medication Reminders"])
def get_reminder(reminder_id: int, db: Session = Depends(get_db)):
    """Get a specific medication reminder by ID."""
    reminder = db.query(models.MedicationReminder).filter(models.MedicationReminder.id == reminder_id).first()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return reminder

@router.put("/reminder/{reminder_id}", response_model=schemas.MedicationReminder, tags=["Medication Reminders"])
def update_reminder(
    reminder_id: int,
    reminder_update: schemas.MedicationReminderUpdate,
    db: Session = Depends(get_db)
):
    """Update a medication reminder."""
    db_reminder = db.query(models.MedicationReminder).filter(models.MedicationReminder.id == reminder_id).first()
    if not db_reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")

    # Update fields if provided
    update_data = reminder_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_reminder, field, value)

    db.commit()
    db.refresh(db_reminder)
    return db_reminder

@router.delete("/reminder/{reminder_id}", tags=["Medication Reminders"])
def delete_reminder(reminder_id: int, db: Session = Depends(get_db)):
    """Delete a medication reminder."""
    db_reminder = db.query(models.MedicationReminder).filter(models.MedicationReminder.id == reminder_id).first()
    if not db_reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")

    db.delete(db_reminder)
    db.commit()
    return {"message": "Reminder deleted successfully"}

@router.post("/upload-prescription", response_model=schemas.MedicationOCRResponse, tags=["Medication Reminders"])
async def upload_prescription_image(
    user_id: int = Form(...),
    image: UploadFile = File(...),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Upload an image of a medication prescription for OCR processing.
    Returns extracted medication data for user approval before saving.
    """
    # Verify the user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate file type
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    try:
        # Read image data
        image_data = await image.read()

        # Process the image with OCR
        prescription_data = medication_ocr_processor.extract_prescription(image_data)

        if not prescription_data.get("name") and not prescription_data.get("schedule"):
            raise HTTPException(
                status_code=400, 
                detail="Could not extract medication information from the image. Please try a clearer image or add the reminder manually."
            )

        # Create the response with extracted data
        extracted_data = schemas.MedicationOCRExtraction(
            name=prescription_data.get("name", ""),
            dosage=prescription_data.get("dosage", ""),
            schedule=[
                schemas.MedicationScheduleItem(
                    datetime=item.get("datetime", ""),
                    dosage=item.get("dosage", "")
                ) for item in prescription_data.get("schedule", [])
            ],
            interpretation=prescription_data.get("interpretation", "")
        )

        return schemas.MedicationOCRResponse(
            extracted_data=extracted_data,
            total_reminders=len(prescription_data.get("schedule", [])),
            message="Medication information extracted successfully. Please review and approve to save."
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing prescription image: {str(e)}"
        )

class SaveOCRRemindersRequest(BaseModel):
    user_id: int
    extracted_data: schemas.MedicationOCRExtraction
    notes: Optional[str] = None

@router.post("/save-ocr-reminders", tags=["Medication Reminders"])
def save_ocr_reminders(
    request: SaveOCRRemindersRequest,
    db: Session = Depends(get_db)
):
    """
    Save the OCR-extracted medication reminders after user approval.
    """
    # Extract data from request
    user_id = request.user_id
    extracted_data = request.extracted_data
    notes = request.notes

    # Verify the user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        saved_reminders = []

        for schedule_item in extracted_data.schedule:
            # Parse the datetime string
            try:
                datetime_str = schedule_item.datetime

                # Handle different datetime formats
                if isinstance(datetime_str, str):
                    if datetime_str.endswith('Z'):
                        datetime_str = datetime_str.replace('Z', '+00:00')
                    # For ISO format without timezone, fromisoformat should work directly
                    schedule_datetime = datetime.fromisoformat(datetime_str)
                else:
                    # If it's already a datetime object, use it directly
                    schedule_datetime = datetime_str

            except (ValueError, AttributeError) as e:
                # If parsing fails, raise an error to help debug
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid datetime format: '{schedule_item.datetime}'. Error: {str(e)}"
                )

            db_reminder = models.MedicationReminder(
                user_id=user_id,
                name=extracted_data.name,
                dosage=extracted_data.dosage,
                schedule_datetime=schedule_datetime,
                schedule_dosage=schedule_item.dosage,
                notes=notes
            )
            db.add(db_reminder)
            saved_reminders.append(db_reminder)

        db.commit()
        
        # Refresh all saved reminders
        for reminder in saved_reminders:
            db.refresh(reminder)

        return {
            "message": f"Successfully saved {len(saved_reminders)} medication reminders",
            "reminders": [schemas.MedicationReminder.model_validate(reminder) for reminder in saved_reminders]
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error saving medication reminders: {str(e)}"
        )

@router.post("/mark-taken/{reminder_id}", tags=["Medication Reminders"])
def mark_reminder_taken(
    reminder_id: int,
    db: Session = Depends(get_db)
):
    """Mark a medication reminder as taken."""
    db_reminder = db.query(models.MedicationReminder).filter(models.MedicationReminder.id == reminder_id).first()
    if not db_reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")

    db_reminder.is_taken = True
    db.commit()
    db.refresh(db_reminder)
    
    return {"message": "Reminder marked as taken", "reminder": schemas.MedicationReminder.model_validate(db_reminder)}

@router.get("/upcoming/{user_id}", tags=["Medication Reminders"])
def get_upcoming_reminders(
    user_id: int,
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """Get upcoming medication reminders for a user within the specified hours."""
    # Verify the user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    from datetime import timedelta
    now = datetime.utcnow()
    future_time = now + timedelta(hours=hours)

    reminders = db.query(models.MedicationReminder).filter(
        models.MedicationReminder.user_id == user_id,
        models.MedicationReminder.is_taken == False,
        models.MedicationReminder.schedule_datetime >= now,
        models.MedicationReminder.schedule_datetime <= future_time
    ).order_by(models.MedicationReminder.schedule_datetime).all()

    return {"upcoming_reminders": [schemas.MedicationReminder.model_validate(reminder) for reminder in reminders]}

# ===== BLOOD PRESSURE CHECK REMINDERS =====

@router.post("/bp-reminder/", response_model=schemas.BPCheckReminder, tags=["BP Check Reminders"])
def create_bp_reminder(
    reminder: schemas.BPCheckReminderCreate,
    user_id: int,
    db: Session = Depends(get_db)
):
    """Create a new BP check reminder manually."""
    # Verify the user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db_reminder = models.BPCheckReminder(
        user_id=user_id,
        reminder_datetime=reminder.reminder_datetime,
        bp_category=reminder.bp_category or "manual",
        notes=reminder.notes
    )
    db.add(db_reminder)
    db.commit()
    db.refresh(db_reminder)
    return schemas.BPCheckReminder.model_validate(db_reminder)

@router.get("/bp-reminder/{reminder_id}", response_model=schemas.BPCheckReminder, tags=["BP Check Reminders"])
def get_bp_reminder(reminder_id: int, db: Session = Depends(get_db)):
    """Get a specific BP check reminder by ID."""
    reminder = db.query(models.BPCheckReminder).filter(models.BPCheckReminder.id == reminder_id).first()
    if not reminder:
        raise HTTPException(status_code=404, detail="BP reminder not found")
    return schemas.BPCheckReminder.model_validate(reminder)

@router.put("/bp-reminder/{reminder_id}", response_model=schemas.BPCheckReminder, tags=["BP Check Reminders"])
def update_bp_reminder(
    reminder_id: int,
    reminder_update: schemas.BPCheckReminderUpdate,
    db: Session = Depends(get_db)
):
    """Update a BP check reminder."""
    db_reminder = db.query(models.BPCheckReminder).filter(models.BPCheckReminder.id == reminder_id).first()
    if not db_reminder:
        raise HTTPException(status_code=404, detail="BP reminder not found")

    # Update fields if provided
    if reminder_update.reminder_datetime is not None:
        db_reminder.reminder_datetime = reminder_update.reminder_datetime
    if reminder_update.bp_category is not None:
        db_reminder.bp_category = reminder_update.bp_category
    if reminder_update.notes is not None:
        db_reminder.notes = reminder_update.notes

    db.commit()
    db.refresh(db_reminder)
    return schemas.BPCheckReminder.model_validate(db_reminder)

@router.delete("/bp-reminder/{reminder_id}", tags=["BP Check Reminders"])
def delete_bp_reminder(reminder_id: int, db: Session = Depends(get_db)):
    """Delete a BP check reminder."""
    db_reminder = db.query(models.BPCheckReminder).filter(models.BPCheckReminder.id == reminder_id).first()
    if not db_reminder:
        raise HTTPException(status_code=404, detail="BP reminder not found")

    db.delete(db_reminder)
    db.commit()
    return {"message": "BP check reminder deleted successfully"}

@router.post("/bp-schedule", response_model=schemas.BPReminderScheduleResponse, tags=["BP Check Reminders"])
def generate_bp_reminder_schedule(
    request: schemas.BPReminderScheduleRequest,
    db: Session = Depends(get_db)
):
    """
    Generate blood pressure check reminder schedule based on first reading and clinical guidelines.

    This endpoint creates personalized BP check reminders based on:
    - Clinical BP categories (Normal, Elevated, Stage 1, Stage 2, Crisis)
    - Evidence-based monitoring frequencies
    - User's preferred timing
    """
    # Verify the user exists
    user = db.query(models.User).filter(models.User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        # Generate the reminder schedule
        result = BPReminderService.generate_reminder_schedule(
            user_id=request.user_id,
            systolic=request.systolic,
            diastolic=request.diastolic,
            first_check_time=request.first_check_time,
            preferred_morning_time=request.preferred_morning_time,
            preferred_evening_time=request.preferred_evening_time,
            db=db
        )

        # Convert to response schema
        return schemas.BPReminderScheduleResponse(
            category=result["category"],
            category_description=result["category_description"],
            total_reminders=result["total_reminders"],
            advice=result.get("advice"),
            reminders=[schemas.BPCheckReminder.model_validate(r) for r in result["reminders"]]
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating BP reminder schedule: {str(e)}"
        )

@router.get("/bp-reminders/{user_id}", response_model=List[schemas.BPCheckReminder], tags=["BP Check Reminders"])
def get_user_bp_reminders(
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    include_completed: bool = True,
    db: Session = Depends(get_db)
):
    """Get all BP check reminders for a user."""
    # Verify the user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    query = db.query(models.BPCheckReminder).filter(models.BPCheckReminder.user_id == user_id)

    if not include_completed:
        query = query.filter(models.BPCheckReminder.is_completed == False)

    reminders = query.order_by(models.BPCheckReminder.reminder_datetime).offset(skip).limit(limit).all()
    return [schemas.BPCheckReminder.model_validate(reminder) for reminder in reminders]

@router.post("/bp-reminder/{reminder_id}/complete", tags=["BP Check Reminders"])
def mark_bp_reminder_completed(
    reminder_id: int,
    db: Session = Depends(get_db)
):
    """Mark a BP check reminder as completed."""
    reminder = BPReminderService.mark_bp_reminder_completed(reminder_id, db)
    if not reminder:
        raise HTTPException(status_code=404, detail="BP reminder not found")

    return {
        "message": "BP check reminder marked as completed",
        "reminder": schemas.BPCheckReminder.model_validate(reminder)
    }

@router.get("/bp-upcoming/{user_id}", tags=["BP Check Reminders"])
def get_upcoming_bp_reminders(
    user_id: int,
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """Get upcoming BP check reminders for a user within the specified hours."""
    # Verify the user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    reminders = BPReminderService.get_upcoming_bp_reminders(user_id, hours, db)
    return {
        "upcoming_bp_reminders": [schemas.BPCheckReminder.model_validate(reminder) for reminder in reminders]
    }

@router.post("/bp-preview", response_model=schemas.BPReminderScheduleResponse, tags=["BP Check Reminders"])
def preview_bp_reminder_schedule(
    request: schemas.BPReminderScheduleRequest
):
    """
    Preview BP reminder schedule without saving to database.
    Useful for showing users what their schedule would look like.
    """
    try:
        # Generate preview without saving to database
        result = BPReminderService.generate_reminder_schedule(
            user_id=request.user_id,
            systolic=request.systolic,
            diastolic=request.diastolic,
            first_check_time=request.first_check_time,
            preferred_morning_time=request.preferred_morning_time,
            preferred_evening_time=request.preferred_evening_time,
            db=None  # No database session = preview mode
        )

        return schemas.BPReminderScheduleResponse(
            category=result["category"],
            category_description=result["category_description"],
            total_reminders=result["total_reminders"],
            advice=result.get("advice"),
            reminders=result["reminders"]  # Already schema objects in preview mode
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error previewing BP reminder schedule: {str(e)}"
        )

# ===== DOCTOR APPOINTMENT REMINDERS =====

@router.post("/doctor-appointment/", response_model=schemas.DoctorAppointmentReminder, tags=["Doctor Appointment Reminders"])
def create_doctor_appointment_reminder(
    reminder: schemas.DoctorAppointmentReminderCreate,
    user_id: int,
    db: Session = Depends(get_db)
):
    """Create a new doctor appointment reminder."""
    # Verify the user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db_reminder = models.DoctorAppointmentReminder(
        user_id=user_id,
        appointment_datetime=reminder.appointment_datetime,
        doctor_name=reminder.doctor_name,
        appointment_type=reminder.appointment_type,
        location=reminder.location,
        notes=reminder.notes
    )
    db.add(db_reminder)
    db.commit()
    db.refresh(db_reminder)
    return schemas.DoctorAppointmentReminder.model_validate(db_reminder)

@router.get("/doctor-appointments/{user_id}", response_model=List[schemas.DoctorAppointmentReminder], tags=["Doctor Appointment Reminders"])
def get_user_doctor_appointments(
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    include_completed: bool = True,
    db: Session = Depends(get_db)
):
    """Get all doctor appointment reminders for a user."""
    # Verify the user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    query = db.query(models.DoctorAppointmentReminder).filter(models.DoctorAppointmentReminder.user_id == user_id)

    if not include_completed:
        query = query.filter(models.DoctorAppointmentReminder.is_completed == False)

    appointments = query.order_by(models.DoctorAppointmentReminder.appointment_datetime).offset(skip).limit(limit).all()
    return [schemas.DoctorAppointmentReminder.model_validate(appointment) for appointment in appointments]

@router.get("/doctor-appointment/{reminder_id}", response_model=schemas.DoctorAppointmentReminder, tags=["Doctor Appointment Reminders"])
def get_doctor_appointment_reminder(reminder_id: int, db: Session = Depends(get_db)):
    """Get a specific doctor appointment reminder by ID."""
    reminder = db.query(models.DoctorAppointmentReminder).filter(models.DoctorAppointmentReminder.id == reminder_id).first()
    if not reminder:
        raise HTTPException(status_code=404, detail="Doctor appointment reminder not found")
    return schemas.DoctorAppointmentReminder.model_validate(reminder)

@router.put("/doctor-appointment/{reminder_id}", response_model=schemas.DoctorAppointmentReminder, tags=["Doctor Appointment Reminders"])
def update_doctor_appointment_reminder(
    reminder_id: int,
    reminder_update: schemas.DoctorAppointmentReminderUpdate,
    db: Session = Depends(get_db)
):
    """Update a doctor appointment reminder."""
    db_reminder = db.query(models.DoctorAppointmentReminder).filter(models.DoctorAppointmentReminder.id == reminder_id).first()
    if not db_reminder:
        raise HTTPException(status_code=404, detail="Doctor appointment reminder not found")

    # Update fields if provided
    if reminder_update.appointment_datetime is not None:
        db_reminder.appointment_datetime = reminder_update.appointment_datetime
    if reminder_update.doctor_name is not None:
        db_reminder.doctor_name = reminder_update.doctor_name
    if reminder_update.appointment_type is not None:
        db_reminder.appointment_type = reminder_update.appointment_type
    if reminder_update.location is not None:
        db_reminder.location = reminder_update.location
    if reminder_update.notes is not None:
        db_reminder.notes = reminder_update.notes

    db.commit()
    db.refresh(db_reminder)
    return schemas.DoctorAppointmentReminder.model_validate(db_reminder)

@router.delete("/doctor-appointment/{reminder_id}", tags=["Doctor Appointment Reminders"])
def delete_doctor_appointment_reminder(reminder_id: int, db: Session = Depends(get_db)):
    """Delete a doctor appointment reminder."""
    db_reminder = db.query(models.DoctorAppointmentReminder).filter(models.DoctorAppointmentReminder.id == reminder_id).first()
    if not db_reminder:
        raise HTTPException(status_code=404, detail="Doctor appointment reminder not found")

    db.delete(db_reminder)
    db.commit()
    return {"message": "Doctor appointment reminder deleted successfully"}

@router.post("/doctor-appointment/{reminder_id}/complete", tags=["Doctor Appointment Reminders"])
def mark_doctor_appointment_completed(
    reminder_id: int,
    db: Session = Depends(get_db)
):
    """Mark a doctor appointment as completed."""
    db_reminder = db.query(models.DoctorAppointmentReminder).filter(models.DoctorAppointmentReminder.id == reminder_id).first()
    if not db_reminder:
        raise HTTPException(status_code=404, detail="Doctor appointment reminder not found")

    db_reminder.is_completed = True
    db.commit()
    db.refresh(db_reminder)

    return {
        "message": "Doctor appointment marked as completed",
        "reminder": schemas.DoctorAppointmentReminder.model_validate(db_reminder)
    }

# ===== WORKOUT REMINDERS =====

@router.post("/workout/", response_model=schemas.WorkoutReminder, tags=["Workout Reminders"])
def create_workout_reminder(
    reminder: schemas.WorkoutReminderCreate,
    user_id: int,
    db: Session = Depends(get_db)
):
    """Create a new workout reminder."""
    # Verify the user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db_reminder = models.WorkoutReminder(
        user_id=user_id,
        workout_datetime=reminder.workout_datetime,
        workout_type=reminder.workout_type,
        duration_minutes=reminder.duration_minutes,
        location=reminder.location,
        notes=reminder.notes
    )
    db.add(db_reminder)
    db.commit()
    db.refresh(db_reminder)
    return schemas.WorkoutReminder.model_validate(db_reminder)

@router.get("/workouts/{user_id}", response_model=List[schemas.WorkoutReminder], tags=["Workout Reminders"])
def get_user_workouts(
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    include_completed: bool = True,
    db: Session = Depends(get_db)
):
    """Get all workout reminders for a user."""
    # Verify the user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    query = db.query(models.WorkoutReminder).filter(models.WorkoutReminder.user_id == user_id)

    if not include_completed:
        query = query.filter(models.WorkoutReminder.is_completed == False)

    workouts = query.order_by(models.WorkoutReminder.workout_datetime).offset(skip).limit(limit).all()
    return [schemas.WorkoutReminder.model_validate(workout) for workout in workouts]

@router.get("/workout/{reminder_id}", response_model=schemas.WorkoutReminder, tags=["Workout Reminders"])
def get_workout_reminder(reminder_id: int, db: Session = Depends(get_db)):
    """Get a specific workout reminder by ID."""
    reminder = db.query(models.WorkoutReminder).filter(models.WorkoutReminder.id == reminder_id).first()
    if not reminder:
        raise HTTPException(status_code=404, detail="Workout reminder not found")
    return schemas.WorkoutReminder.model_validate(reminder)

@router.put("/workout/{reminder_id}", response_model=schemas.WorkoutReminder, tags=["Workout Reminders"])
def update_workout_reminder(
    reminder_id: int,
    reminder_update: schemas.WorkoutReminderUpdate,
    db: Session = Depends(get_db)
):
    """Update a workout reminder."""
    db_reminder = db.query(models.WorkoutReminder).filter(models.WorkoutReminder.id == reminder_id).first()
    if not db_reminder:
        raise HTTPException(status_code=404, detail="Workout reminder not found")

    # Update fields if provided
    if reminder_update.workout_datetime is not None:
        db_reminder.workout_datetime = reminder_update.workout_datetime
    if reminder_update.workout_type is not None:
        db_reminder.workout_type = reminder_update.workout_type
    if reminder_update.duration_minutes is not None:
        db_reminder.duration_minutes = reminder_update.duration_minutes
    if reminder_update.location is not None:
        db_reminder.location = reminder_update.location
    if reminder_update.notes is not None:
        db_reminder.notes = reminder_update.notes

    db.commit()
    db.refresh(db_reminder)
    return schemas.WorkoutReminder.model_validate(db_reminder)

@router.delete("/workout/{reminder_id}", tags=["Workout Reminders"])
def delete_workout_reminder(reminder_id: int, db: Session = Depends(get_db)):
    """Delete a workout reminder."""
    db_reminder = db.query(models.WorkoutReminder).filter(models.WorkoutReminder.id == reminder_id).first()
    if not db_reminder:
        raise HTTPException(status_code=404, detail="Workout reminder not found")

    db.delete(db_reminder)
    db.commit()
    return {"message": "Workout reminder deleted successfully"}

@router.post("/workout/{reminder_id}/complete", tags=["Workout Reminders"])
def mark_workout_completed(
    reminder_id: int,
    db: Session = Depends(get_db)
):
    """Mark a workout as completed."""
    db_reminder = db.query(models.WorkoutReminder).filter(models.WorkoutReminder.id == reminder_id).first()
    if not db_reminder:
        raise HTTPException(status_code=404, detail="Workout reminder not found")

    db_reminder.is_completed = True
    db.commit()
    db.refresh(db_reminder)

    return {
        "message": "Workout marked as completed",
        "reminder": schemas.WorkoutReminder.model_validate(db_reminder)
    }
