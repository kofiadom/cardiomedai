from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import sys
import os

# Add the parent directory to the path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    # Try relative imports first (when run as module)
    from .. import models, schemas
    from ..database import get_db
    from ..advisor_agent.health_advisor_service import HealthAdvisorService
except ImportError:
    # Fall back to absolute imports (when run directly)
    from app import models, schemas
    from app.database import get_db
    from app.advisor_agent.health_advisor_service import HealthAdvisorService

router = APIRouter(
    prefix="/health-advisor",
    tags=["health advisor"],
    responses={404: {"description": "Not found"}},
)

# Global service instance (will be initialized on first use)
_health_advisor_service: HealthAdvisorService = None

async def get_health_advisor_service() -> HealthAdvisorService:
    """Get or create the health advisor service instance."""
    global _health_advisor_service
    if _health_advisor_service is None:
        _health_advisor_service = HealthAdvisorService()
        await _health_advisor_service.initialize()
    return _health_advisor_service


@router.post("/advice", response_model=schemas.HealthAdvisorResponse)
async def get_health_advice(
    request: schemas.HealthAdvisorRequest,
    db: Session = Depends(get_db)
):
    """
    Get a friendly daily check-in from your community health worker.

    **What you'll get:**
    - Short, encouraging message (3-4 sentences)
    - Personal feedback on your recent BP progress
    - One simple daily tip or reminder
    - Motivational support like a caring friend

    **Perfect for:**
    - Daily morning check-ins
    - Quick progress updates
    - Motivation and encouragement
    - Simple health reminders

    **Example responses:**
    - "Great job! Your BP dropped to 125/82 yesterday. Try a 10-minute walk after lunch today! 🚶‍♂️"
    - "Your 118/75 reading this morning is excellent! Remember to drink 8 glasses of water today! 💧"

    **Note:** For detailed medical information, use the Knowledge Agent instead.
    """
    # Verify the user exists
    user = db.query(models.User).filter(models.User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        # Get the health advisor service
        service = await get_health_advisor_service()

        # Process the health advice request
        result = await service.process_health_advice_request(
            user_id=request.user_id,
            message=request.message
        )

        # Return the response
        return schemas.HealthAdvisorResponse(
            user_id=request.user_id,
            request_message=request.message,
            advisor_response=result.get("response", "No response generated"),
            agent_id=result.get("agent_id"),
            thread_id=result.get("thread_id"),
            status=result.get("status", "unknown")
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get health advice: {str(e)}"
        )


@router.get("/advice/{user_id}")
async def get_quick_health_advice(
    user_id: int,
    message: str = "Good morning! How am I doing with my blood pressure this week?",
    db: Session = Depends(get_db)
):
    """
    Quick daily check-in with your community health worker.

    **Parameters:**
    - user_id: The ID of the user requesting check-in
    - message: Optional custom message (defaults to morning check-in)

    **Perfect for daily use:**
    ```
    GET /health-advisor/advice/1
    GET /health-advisor/advice/1?message=How did I do yesterday?
    GET /health-advisor/advice/1?message=Any tips for today?
    ```

    **Returns:** Short, encouraging message with personal feedback and daily tip.
    """
    # Create request object
    request = schemas.HealthAdvisorRequest(
        user_id=user_id,
        message=message
    )

    # Use the main advice endpoint
    return await get_health_advice(request, db)


@router.get("/status")
async def get_service_status():
    """
    Check the health advisor service status and configuration.
    """
    try:
        global _health_advisor_service
        if _health_advisor_service is None:
            return {
                "status": "not_initialized",
                "message": "Health advisor service not yet initialized"
            }

        return {
            "status": "ready",
            "message": "Health advisor service is ready",
            "project_endpoint": _health_advisor_service.project_endpoint,
            "toolbox_url": _health_advisor_service.toolbox_url,
            "tools_loaded": len(_health_advisor_service.tool_definitions)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Service status check failed: {str(e)}"
        }


@router.post("/initialize")
async def initialize_service():
    """
    Manually initialize the health advisor service.
    Useful for warming up the service or troubleshooting.
    """
    try:
        global _health_advisor_service
        _health_advisor_service = HealthAdvisorService()
        await _health_advisor_service.initialize()

        return {
            "status": "initialized",
            "message": "Health advisor service initialized successfully",
            "tools_loaded": len(_health_advisor_service.tool_definitions)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize service: {str(e)}"
        )
