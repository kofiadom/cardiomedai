from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the parent directory to the path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # Try relative imports first (when run as module)
    from . import models
    from .database import engine
    from .routers import users, blood_pressure, health_advisor, knowledge_agent
except ImportError:
    # Fall back to absolute imports (when run directly)
    from app import models
    from app.database import engine
    from app.routers import users, blood_pressure, health_advisor

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="CardioMed AI API",
    description="An API for managing blood pressure readings",
    version="0.1.0"
)

# Add CORS middleware
# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=False,  # Must be False when allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(users.router)
app.include_router(blood_pressure.router)
app.include_router(health_advisor.router)
app.include_router(knowledge_agent.router)

@app.get("/")
def read_root():
    return {
        "message": "Welcome to the Hypertension Management API",
        "endpoints": {
            "users": "/users/",
            "blood_pressure_readings": "/bp/readings/",
            "upload_bp_image": "/bp/upload/",
            "health_advisor": "/health-advisor/advice",
            "health_advisor_status": "/health-advisor/status",
            "knowledge_agent": "/knowledge-agent/ask",
            "knowledge_agent_status": "/knowledge-agent/status"
        }
    }

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
