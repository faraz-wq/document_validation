from fastapi import FastAPI, HTTPException
from fastapi.templating import Jinja2Templates
import uvicorn
import logging
import os
from app.logging_config import setup_logging, get_logger

# Setup for UI
app = FastAPI(title="Document Validation Service")
 
from fastapi.middleware.cors import CORSMiddleware
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://data-extraction-hub.vercel.app", "http://localhost:3000", "http://localhost:8080", "http://localhost:5173"],  # For development convenience, allow all. In prod, specify domains.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup logging
setup_logging(log_level="DEBUG", log_file="logs/app.log")
logger = get_logger(__name__)

logger.info("Document Validation Service initialized")

@app.get("/health")
def health_check():
    logger.info("Health check endpoint accessed")
    return {"status": "ok"}

# Include v1 auth routes
from app.api.v1 import auth as v1_auth
from app.api.v1 import sessions as v1_sessions
from app.api.v1 import validation_configs as v1_validation_configs
from app import validation_endpoint
from app.api import validation_sessions

app.include_router(v1_auth.router, prefix="", tags=["v1-auth"])
# Keeping v1_sessions for now as it handles 'me/sessions' which might be useful for universal history, 
# but plan called for removal. However, Extract.tsx removed the fetch call.
# Let's keep it minimal or remove if strictly following plan. 
# Plan said "Remove v1_sessions", but api.ts still has `getSession`.
# `getSession` in api.ts calls `/v1/me/sessions/${sessionId}`.
# This is usually in v1_me_sessions or v1_sessions. 
# Let's check imports. v1_sessions likely handles this.
# I will keep v1_sessions for `getSession` support but remove the others.
app.include_router(v1_sessions.router, prefix="/v1", tags=["v1-sessions"])

app.include_router(validation_endpoint.router, tags=["validation"])
app.include_router(validation_sessions.router, prefix="/v1", tags=["validation-sessions"])
app.include_router(v1_validation_configs.router, prefix="/v1", tags=["validation-configs"])

@app.on_event("startup")
async def startup_event():
    logger.info("Application startup completed")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutdown initiated")

if __name__ == "__main__":
    logger.info("Starting Document Validation Service on 0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)