from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from . import models, schemas


class BPReminderService:
    """Service for generating blood pressure check reminders based on clinical guidelines."""
    
    @staticmethod
    def classify_bp(systolic: int, diastolic: int) -> str:
        """
        Classify blood pressure based on AHA/ESC guidelines.
        
        Returns:
            str: BP category (normal, elevated, stage_1, stage_2, hypertensive_crisis)
        """
        if systolic >= 180 or diastolic >= 120:
            return "hypertensive_crisis"
        elif systolic >= 140 or diastolic >= 90:
            return "stage_2"
        elif systolic >= 130 or diastolic >= 80:
            return "stage_1"
        elif systolic >= 120 and diastolic < 80:
            return "elevated"
        else:
            return "normal"
    
    @staticmethod
    def get_category_info(category: str) -> Dict[str, str]:
        """Get description and advice for each BP category."""
        category_info = {
            "normal": {
                "description": "Normal Blood Pressure",
                "advice": "Keep up the good work! Continue healthy lifestyle habits."
            },
            "elevated": {
                "description": "Elevated Blood Pressure",
                "advice": "Focus on lifestyle changes: diet, exercise, and stress management."
            },
            "stage_1": {
                "description": "Hypertension Stage 1",
                "advice": "Consider lifestyle changes and consult your doctor about treatment options."
            },
            "stage_2": {
                "description": "Hypertension Stage 2",
                "advice": "Important to monitor closely. Consult your doctor about medication and lifestyle changes."
            },
            "hypertensive_crisis": {
                "description": "Hypertensive Crisis",
                "advice": "SEEK IMMEDIATE MEDICAL ATTENTION. This requires urgent care."
            }
        }
        return category_info.get(category, {"description": "Unknown", "advice": ""})
    
    @staticmethod
    def generate_reminder_schedule(
        user_id: int,
        systolic: int,
        diastolic: int,
        first_check_time: Optional[datetime] = None,
        preferred_morning_time: str = "07:00",
        preferred_evening_time: str = "19:00",
        db: Session = None
    ) -> Dict:
        """
        Generate BP check reminder schedule based on first reading and clinical guidelines.
        
        Args:
            user_id: User ID
            systolic: Systolic BP reading
            diastolic: Diastolic BP reading
            first_check_time: When the first reading was taken (defaults to now)
            preferred_morning_time: User's preferred morning time (HH:MM)
            preferred_evening_time: User's preferred evening time (HH:MM)
            db: Database session for saving reminders
            
        Returns:
            Dict with category, reminders, and advice
        """
        category = BPReminderService.classify_bp(systolic, diastolic)
        category_info = BPReminderService.get_category_info(category)
        
        if first_check_time is None:
            first_check_time = datetime.now()
        
        # Parse preferred times
        morning_hour, morning_min = map(int, preferred_morning_time.split(':'))
        evening_hour, evening_min = map(int, preferred_evening_time.split(':'))
        
        reminder_times = []
        
        if category == "normal":
            # Every 2 weeks, 4 reminders total
            interval_days = 14
            count = 4
            for i in range(count):
                reminder_time = first_check_time + timedelta(days=i * interval_days)
                reminder_times.append(reminder_time)
                
        elif category == "elevated":
            # Every 3 days, 6 reminders total
            interval_days = 3
            count = 6
            for i in range(count):
                reminder_time = first_check_time + timedelta(days=i * interval_days)
                reminder_times.append(reminder_time)
                
        elif category == "stage_1":
            # Daily for 1 week
            count = 7
            for i in range(count):
                reminder_time = first_check_time.replace(
                    hour=morning_hour, minute=morning_min, second=0, microsecond=0
                ) + timedelta(days=i)
                reminder_times.append(reminder_time)
                
        elif category == "stage_2":
            # Twice daily (morning + evening) for 1 week
            count = 7
            for i in range(count):
                # Morning reminder
                morning_time = first_check_time.replace(
                    hour=morning_hour, minute=morning_min, second=0, microsecond=0
                ) + timedelta(days=i)
                reminder_times.append(morning_time)
                
                # Evening reminder
                evening_time = first_check_time.replace(
                    hour=evening_hour, minute=evening_min, second=0, microsecond=0
                ) + timedelta(days=i)
                reminder_times.append(evening_time)
                
        elif category == "hypertensive_crisis":
            # No automatic reminders - immediate medical attention needed
            return {
                "category": category,
                "category_description": category_info["description"],
                "advice": category_info["advice"],
                "total_reminders": 0,
                "reminders": []
            }
        
        # Sort reminder times
        reminder_times.sort()
        
        # Create reminder objects
        reminders = []
        if db:
            # Save to database
            for reminder_time in reminder_times:
                db_reminder = models.BPCheckReminder(
                    user_id=user_id,
                    reminder_datetime=reminder_time,
                    bp_category=category,
                    notes=f"BP check reminder - {category_info['description']}"
                )
                db.add(db_reminder)
                reminders.append(db_reminder)
            
            db.commit()
            
            # Refresh all reminders
            for reminder in reminders:
                db.refresh(reminder)
        else:
            # Just create schema objects for preview
            for i, reminder_time in enumerate(reminder_times):
                reminder = schemas.BPCheckReminder(
                    id=i + 1,  # Temporary ID for preview
                    user_id=user_id,
                    reminder_datetime=reminder_time,
                    bp_category=category,
                    is_completed=False,
                    created_at=datetime.now(),
                    notes=f"BP check reminder - {category_info['description']}"
                )
                reminders.append(reminder)
        
        return {
            "category": category,
            "category_description": category_info["description"],
            "advice": category_info["advice"],
            "total_reminders": len(reminders),
            "reminders": reminders
        }
    
    @staticmethod
    def get_upcoming_bp_reminders(user_id: int, hours: int = 24, db: Session = None) -> List[models.BPCheckReminder]:
        """Get upcoming BP check reminders for a user within specified hours."""
        if not db:
            return []
            
        now = datetime.now()
        future_time = now + timedelta(hours=hours)
        
        reminders = db.query(models.BPCheckReminder).filter(
            models.BPCheckReminder.user_id == user_id,
            models.BPCheckReminder.is_completed == False,
            models.BPCheckReminder.reminder_datetime >= now,
            models.BPCheckReminder.reminder_datetime <= future_time
        ).order_by(models.BPCheckReminder.reminder_datetime).all()
        
        return reminders
    
    @staticmethod
    def mark_bp_reminder_completed(reminder_id: int, db: Session) -> Optional[models.BPCheckReminder]:
        """Mark a BP check reminder as completed."""
        reminder = db.query(models.BPCheckReminder).filter(
            models.BPCheckReminder.id == reminder_id
        ).first()
        
        if reminder:
            reminder.is_completed = True
            db.commit()
            db.refresh(reminder)
            
        return reminder
