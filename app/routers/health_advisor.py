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
    from ..translation_service import TranslationService, SUPPORTED_LANGUAGES
except ImportError:
    # Fall back to absolute imports (when run directly)
    from app import models, schemas
    from app.database import get_db
    from app.advisor_agent.health_advisor_service import HealthAdvisorService
    from app.translation_service import TranslationService, SUPPORTED_LANGUAGES

router = APIRouter(
    prefix="/health-advisor",
    tags=["health advisor"],
    responses={404: {"description": "Not found"}},
)

# Global service instances (will be initialized on first use)
_health_advisor_service: HealthAdvisorService = None
_translation_service: TranslationService = None

async def get_health_advisor_service() -> HealthAdvisorService:
    """Get or create the health advisor service instance."""
    global _health_advisor_service
    if _health_advisor_service is None:
        _health_advisor_service = HealthAdvisorService()
        await _health_advisor_service.initialize()
    return _health_advisor_service


def get_translation_service() -> TranslationService:
    """Get or create the translation service instance."""
    global _translation_service
    if _translation_service is None:
        try:
            _translation_service = TranslationService()
        except ValueError as e:
            print(f"⚠️ Translation service initialization failed: {e}")
            return None
    return _translation_service


@router.post("/advice", response_model=schemas.HealthAdvisorResponse)
async def get_health_advice(
    request: schemas.HealthAdvisorRequest,
    db: Session = Depends(get_db)
):
    """
    Get a friendly daily check-in from your community health worker with optional translation.

    **What you'll get:**
    - Short, encouraging message (3-4 sentences)
    - Personal feedback on your recent BP progress
    - One simple daily tip or reminder
    - Motivational support like a caring friend
    - Optional translation to African languages (Twi, Ga, Ewe, Fante, Dagbani)

    **Perfect for:**
    - Daily morning check-ins
    - Quick progress updates
    - Motivation and encouragement
    - Simple health reminders

    **Example responses:**
    - "Great job! Your BP dropped to 125/82 yesterday. Try a 10-minute walk after lunch today! 🚶‍♂️"
    - "Your 118/75 reading this morning is excellent! Remember to drink 8 glasses of water today! 💧"

    **Supported Languages for Translation:**
    - "en" - English (default)
    - "tw" - Twi
    - "gaa" - Ga
    - "ee" - Ewe
    - "fat" - Fante
    - "dag" - Dagbani

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

        advisor_response = result.get("response", "No response generated")
        translated_response = None
        target_language = request.language.lower() if request.language else "en"

        # Translate if language is not English
        if target_language != "en":
            translation_service = get_translation_service()
            if translation_service:
                translation_result = await translation_service.translate_health_advice(
                    advice_text=advisor_response,
                    target_language=target_language
                )
                if translation_result.get("success"):
                    translated_response = translation_result.get("translated")
                    print(f"✅ Successfully translated health advice to {target_language}")
                else:
                    print(f"⚠️ Translation to {target_language} failed, returning original text")
            else:
                print(f"⚠️ Translation service not available, returning original text")

        # Return the response
        return schemas.HealthAdvisorResponse(
            user_id=request.user_id,
            request_message=request.message,
            advisor_response=advisor_response,
            translated_response=translated_response,
            language=target_language,
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
    message: str = """Good morning! How am I doing with my health today? Can you check all my health data and give me a friendly update on my blood pressure readings and trends, medication schedule and what I haven't taken yet, my workout routine and any pending exercises, upcoming doctor appointments, BP check reminders, and any other health reminders I have coming up? Are there any health risks I should be aware of based on my current data, and what encouraging progress or simple tips do you have for me? Please be very precise and thorough - make sure to mention every important detail from all my data you collect.""",
    language: str = "en",
    db: Session = Depends(get_db)
):
    """
    Quick daily check-in with your community health worker with optional translation.

    **Parameters:**
    - user_id: The ID of the user requesting check-in
    - message: Optional custom message (defaults to morning check-in)
    - language: Optional language code for translation (default: "en" for English)

    **Supported Languages:**
    - "en" - English (default)
    - "tw" - Twi
    - "gaa" - Ga
    - "ee" - Ewe
    - "fat" - Fante
    - "dag" - Dagbani

    **Perfect for daily use:**
    ```
    GET /health-advisor/advice/1
    GET /health-advisor/advice/1?message=How did I do yesterday?
    GET /health-advisor/advice/1?language=tw
    GET /health-advisor/advice/1?message=Any tips for today?&language=tw
    ```

    **Returns:** Short, encouraging message with personal feedback, daily tip, and optional translation.
    """
    # Create request object
    request = schemas.HealthAdvisorRequest(
        user_id=user_id,
        message=message,
        language=language
    )

    # Use the main advice endpoint
    return await get_health_advice(request, db)


@router.get("/languages")
async def get_supported_languages():
    """
    Get the list of languages supported for health advisor response translation.

    **Returns:** Dictionary of language codes and their names.
    """
    return {
        "languages": SUPPORTED_LANGUAGES,
        "description": "Supported languages for translating health advisor responses"
    }


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
                "message": "Health advisor service not yet initialized",
                "agent_id": None,
                "env_agent_id": os.getenv("HEALTH_ADVISOR_AGENT_ID"),
                "fallback_agent_id": "asst_phjVsezosQqDE3XCufhu1oZd"
            }

        # Check if agent ID exists and is valid
        agent_status = "unknown"
        if _health_advisor_service.agent_id:
            try:
                # Try to verify the agent exists
                agent = _health_advisor_service.project_client.agents.get_agent(_health_advisor_service.agent_id)
                agent_status = "valid"
            except Exception as e:
                agent_status = f"invalid: {str(e)}"
        else:
            agent_status = "missing"

        return {
            "status": "ready",
            "message": "Health advisor service is ready",
            "agent_id": _health_advisor_service.agent_id,
            "agent_status": agent_status,
            "env_agent_id": os.getenv("HEALTH_ADVISOR_AGENT_ID"),
            "fallback_agent_id": "asst_phjVsezosQqDE3XCufhu1oZd",
            "using_fallback": _health_advisor_service.agent_id == "asst_phjVsezosQqDE3XCufhu1oZd",
            "project_endpoint": _health_advisor_service.project_endpoint,
            "toolbox_url": _health_advisor_service.toolbox_url,
            "tools_loaded": len(_health_advisor_service.tool_definitions)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Service status check failed: {str(e)}",
            "agent_id": None,
            "env_agent_id": os.getenv("HEALTH_ADVISOR_AGENT_ID")
        }


@router.post("/initialize")
async def initialize_service():
    """
    Manually initialize the health advisor service.
    Useful for warming up the service or troubleshooting.
    """
    try:
        global _health_advisor_service
        # Only reinitialize if service doesn't exist or failed
        if _health_advisor_service is None:
            _health_advisor_service = HealthAdvisorService()
            await _health_advisor_service.initialize()
            status_message = "Health advisor service initialized successfully"
        else:
            # Service exists, just verify it's working
            if not _health_advisor_service.agent_id:
                # Agent ID is missing, try to recover
                await _health_advisor_service.initialize()
                status_message = "Health advisor service recovered successfully"
            else:
                status_message = "Health advisor service already initialized and ready"

        return {
            "status": "initialized",
            "message": status_message,
            "agent_id": _health_advisor_service.agent_id,
            "tools_loaded": len(_health_advisor_service.tool_definitions)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize service: {str(e)}"
        )
