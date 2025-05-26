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
    Get personalized health advice from the AI health advisor agent.

    The agent will:
    1. Review the user's profile and medical information
    2. Analyze their blood pressure history and trends
    3. Provide personalized recommendations and lifestyle tips
    4. Alert about readings outside target ranges
    5. Consider notes about lifestyle factors

    **Blood Pressure Categories:**
    - Normal: <120/80
    - Elevated: 120-129/<80
    - Stage 1: 130-139/80-89
    - Stage 2: ≥140/≥90
    - Crisis: >180/>120 (immediate medical attention advised)
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
    message: str = "Good morning! Can you check my blood pressure readings from the past week and give me some advice?",
    db: Session = Depends(get_db)
):
    """
    Quick endpoint to get health advice with a simple GET request.

    **Parameters:**
    - user_id: The ID of the user requesting advice
    - message: Optional custom message (defaults to morning health check)

    **Example usage:**
    ```
    GET /health-advisor/advice/1?message=How are my blood pressure trends this month?
    ```
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
