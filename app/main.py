from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from . import models
from .database import engine
from .routers import users, blood_pressure

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="CardioMed AI API",
    description="An API for managing blood pressure readings",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(users.router)
app.include_router(blood_pressure.router)

@app.get("/")
def read_root():
    return {
        "message": "Welcome to the Hypertension Management API",
        "endpoints": {
            "users": "/users/",
            "blood_pressure_readings": "/bp/readings/",
            "upload_bp_image": "/bp/upload/"
        }
    }

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)