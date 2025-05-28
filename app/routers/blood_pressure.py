from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import base64

from .. import models, schemas
from ..database import get_db
from ..ocr import OCRProcessor

router = APIRouter(
    prefix="/bp",
    tags=["blood pressure"],
    responses={404: {"description": "Not found"}},
)

# Initialize OCR processor
ocr_processor = OCRProcessor()

def interpret_blood_pressure(systolic: int, diastolic: int) -> str:
    """
    Interpret blood pressure readings based on standardized categories from
    the American Heart Association and National Heart, Lung, and Blood Institute.

    Categories:
    - Normal: Systolic < 120 AND Diastolic < 80
    - Elevated: Systolic 120-129 AND Diastolic < 80
    - Hypertension Stage 1: Systolic 130-139 OR Diastolic 80-89
    - Hypertension Stage 2: Systolic ≥ 140 OR Diastolic ≥ 90
    - Hypertensive Crisis: Systolic > 180 OR Diastolic > 120

    Returns a string with the interpretation.
    """
    if systolic > 180 or diastolic > 120:
        return "Hypertensive Crisis (Consult your doctor immediately)"
    elif systolic >= 140 or diastolic >= 90:
        return "Hypertension Stage 2"
    elif (systolic >= 130 and systolic <= 139) or (diastolic >= 80 and diastolic <= 89):
        return "Hypertension Stage 1"
    elif (systolic >= 120 and systolic <= 129) and diastolic < 80:
        return "Elevated Blood Pressure"
    elif systolic < 120 and diastolic < 80:
        return "Normal Blood Pressure"
    else:
        return "Invalid Reading"

@router.post("/readings/", response_model=schemas.BloodPressure)
def create_reading(
    reading: schemas.BloodPressureCreate,
    user_id: int,
    db: Session = Depends(get_db)
):
    # Verify the user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate blood pressure readings
    if reading.systolic < 70 or reading.systolic > 250:
        raise HTTPException(status_code=400, detail="Invalid systolic reading")
    if reading.diastolic < 40 or reading.diastolic > 150:
        raise HTTPException(status_code=400, detail="Invalid diastolic reading")
    if reading.pulse < 30 or reading.pulse > 220:
        raise HTTPException(status_code=400, detail="Invalid pulse reading")

    # Get interpretation of blood pressure
    interpretation = interpret_blood_pressure(reading.systolic, reading.diastolic)

    db_reading = models.BloodPressure(
        user_id=user_id,
        systolic=reading.systolic,
        diastolic=reading.diastolic,
        pulse=reading.pulse,
        notes=reading.notes,
        device_id=reading.device_id,
        interpretation=interpretation
    )
    db.add(db_reading)
    db.commit()
    db.refresh(db_reading)
    return db_reading

@router.get("/readings/{user_id}", response_model=List[schemas.BloodPressure])
def get_readings(
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    # Verify the user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    readings = db.query(models.BloodPressure).filter(
        models.BloodPressure.user_id == user_id
    ).order_by(
        models.BloodPressure.reading_time.desc()
    ).offset(skip).limit(limit).all()

    return readings

@router.post("/ocr-preview/")
async def preview_bp_image(
    user_id: int = Form(...),
    image: UploadFile = File(...),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Process BP image with OCR and return extracted data for user approval.
    Does NOT save to database - only extracts and returns the readings.
    """
    # Verify the user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Read the uploaded image file
    image_data = await image.read()

    # Process the image with OCR
    try:
        systolic, diastolic, pulse = ocr_processor.extract_readings(image_data)

        # Get interpretation of blood pressure
        interpretation = interpret_blood_pressure(systolic, diastolic)

        # Return extracted data without saving to database
        return {
            "systolic": systolic,
            "diastolic": diastolic,
            "pulse": pulse,
            "notes": notes,
            "device_id": f"Image Upload: {image.filename}",
            "interpretation": interpretation,
            "user_id": user_id,
            "preview": True  # Indicates this is preview data, not saved
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing image: {str(e)}"
        )

@router.post("/upload/", response_model=schemas.BloodPressure)
async def upload_bp_image(
    user_id: int = Form(...),
    image: UploadFile = File(...),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    # Verify the user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Read the uploaded image file
    image_data = await image.read()

    # Process the image with OCR
    try:
        systolic, diastolic, pulse = ocr_processor.extract_readings(image_data)

        # Get interpretation of blood pressure
        interpretation = interpret_blood_pressure(systolic, diastolic)

        # Create record with extracted readings
        db_reading = models.BloodPressure(
            user_id=user_id,
            systolic=systolic,
            diastolic=diastolic,
            pulse=pulse,
            notes=notes,  # Keep notes as provided by user (can be None)
            device_id=f"Image Upload: {image.filename}",
            interpretation=interpretation
        )

        # If all values are 0, it might be an OCR failure
        if systolic == 0 and diastolic == 0 and pulse == 0:
            db_reading.notes = "Warning: OCR may have failed to extract values"

        db.add(db_reading)
        db.commit()
        db.refresh(db_reading)

        return db_reading

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing image: {str(e)}"
        )

@router.post("/save-ocr/", response_model=schemas.BloodPressure)
async def save_ocr_reading(
    reading_data: dict,
    db: Session = Depends(get_db)
):
    """
    Save OCR reading data that has been approved by the user.
    """
    try:
        # Extract data from the request
        user_id = reading_data.get("user_id")
        systolic = reading_data.get("systolic")
        diastolic = reading_data.get("diastolic")
        pulse = reading_data.get("pulse")
        notes = reading_data.get("notes")
        device_id = reading_data.get("device_id")
        interpretation = reading_data.get("interpretation")

        # Verify the user exists
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Create record with approved readings
        db_reading = models.BloodPressure(
            user_id=user_id,
            systolic=systolic,
            diastolic=diastolic,
            pulse=pulse,
            notes=notes,
            device_id=device_id,
            interpretation=interpretation
        )

        db.add(db_reading)
        db.commit()
        db.refresh(db_reading)

        return db_reading

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error saving OCR reading: {str(e)}"
        )

@router.get("/readings/stats/{user_id}")
def get_reading_stats(user_id: int, db: Session = Depends(get_db)):
    """Get statistics about a user's blood pressure readings."""
    # Verify the user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get all readings for the user
    readings = db.query(models.BloodPressure).filter(
        models.BloodPressure.user_id == user_id
    ).all()

    if not readings:
        return {
            "total_readings": 0,
            "message": "No readings found for this user"
        }

    # Calculate statistics
    total = len(readings)
    avg_systolic = sum(r.systolic for r in readings) / total if total > 0 else 0
    avg_diastolic = sum(r.diastolic for r in readings) / total if total > 0 else 0
    avg_pulse = sum(r.pulse for r in readings) / total if total > 0 else 0

    # Find min and max
    min_systolic = min((r.systolic for r in readings), default=0)
    max_systolic = max((r.systolic for r in readings), default=0)
    min_diastolic = min((r.diastolic for r in readings), default=0)
    max_diastolic = max((r.diastolic for r in readings), default=0)

    # Add interpretation to any readings that don't have it
    for reading in readings:
        if not reading.interpretation:
            reading.interpretation = interpret_blood_pressure(reading.systolic, reading.diastolic)
            db.add(reading)

    # Commit any changes
    db.commit()

    # Count readings by category
    normal_count = sum(1 for r in readings if r.interpretation == "Normal Blood Pressure")
    elevated_count = sum(1 for r in readings if r.interpretation == "Elevated Blood Pressure")
    hypertension1_count = sum(1 for r in readings if r.interpretation == "Hypertension Stage 1")
    hypertension2_count = sum(1 for r in readings if r.interpretation == "Hypertension Stage 2")
    crisis_count = sum(1 for r in readings if "Crisis" in r.interpretation)

    return {
        "total_readings": total,
        "averages": {
            "systolic": round(avg_systolic, 1),
            "diastolic": round(avg_diastolic, 1),
            "pulse": round(avg_pulse, 1)
        },
        "ranges": {
            "systolic": {"min": min_systolic, "max": max_systolic},
            "diastolic": {"min": min_diastolic, "max": max_diastolic}
        },
        "categories": {
            "normal": normal_count,
            "elevated": elevated_count,
            "hypertension_stage1": hypertension1_count,
            "hypertension_stage2": hypertension2_count,
            "hypertensive_crisis": crisis_count
        }
    }
