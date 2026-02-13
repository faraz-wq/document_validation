from fastapi import FastAPI, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import logging
import os
from app.logging_config import setup_logging, get_logger

# Setup for UI
app = FastAPI(title="Document Validation Service")
 
from fastapi.middleware.cors import CORSMiddleware
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://data-extraction-hub.vercel.app", "http://localhost:3000", "http://localhost:8081", "http://localhost:5173"],  # For development convenience, allow all. In prod, specify domains.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Setup logging
setup_logging(log_level="DEBUG", log_file="logs/app.log")
logger = get_logger(__name__)

logger.info("Document Validation Service initialized")

@app.get("/health")
def health_check():
    """Enhanced health check with database and pool statistics"""
    logger.info("Health check endpoint accessed")
    
    from app.db.database import check_db_connection, get_pool_stats
    
    # Check database connection
    db_healthy = check_db_connection()
    
    # Get pool statistics
    pool_stats = get_pool_stats()
    
    health_status = {
        "status": "healthy" if db_healthy else "degraded",
        "service": "document-validation",
        "database": {
            "connected": db_healthy,
            "pool": pool_stats
        }
    }
    
    return health_status


# Include v1 auth routes
from app.api.v1 import auth as v1_auth
from app.api.v1 import sessions as v1_sessions
from app.api.v1 import validation_configs as v1_validation_configs
from app import validation_endpoint
from app.api import validation_sessions
from app.api import admin
from app.api import async_validation

app.include_router(v1_auth.router, prefix="", tags=["v1-auth"])
app.include_router(v1_sessions.router, prefix="/v1", tags=["v1-sessions"])

app.include_router(validation_endpoint.router, tags=["validation"])
app.include_router(async_validation.router, tags=["async-validation"])
app.include_router(validation_sessions.router, prefix="/v1", tags=["validation-sessions"])
app.include_router(v1_validation_configs.router, prefix="/v1", tags=["validation-configs"])
app.include_router(admin.router, prefix="/v1", tags=["admin"])

@app.on_event("startup")
async def startup_event():
    """Initialize services on application startup"""
    logger.info("Application startup initiated")
    
    # Start file cleanup service
    from app.utils.file_cleanup import file_cleanup_service
    file_cleanup_service.start_cleanup_service()
    
    logger.info("Application startup completed")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    logger.info("Application shutdown initiated")
    
    # Stop file cleanup service
    from app.utils.file_cleanup import file_cleanup_service
    file_cleanup_service.stop_cleanup_service()
    
    logger.info("Application shutdown completed")


# Serve static files (SPA)
# This is for the combined Docker image where frontend build is copied to /app/static
static_path = "static"
if os.path.isdir(static_path):
    # Mount assets (CSS, JS, images)
    app.mount("/assets", StaticFiles(directory=f"{static_path}/assets"), name="assets")
    
    # helper for other root files
    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        return FileResponse(f"{static_path}/favicon.ico")

    # Catch-all for SPA routes
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        # Don't serve HTML for API 404s
        if full_path.startswith("api") or full_path.startswith("v1") or full_path.startswith("validate-form") or full_path == "docs" or full_path == "openapi.json":
             raise HTTPException(status_code=404, detail="Not Found")
        
        # Check if file exists in static (e.g. vite.svg, robots.txt)
        potential_file_path = os.path.join(static_path, full_path)
        if os.path.isfile(potential_file_path):
             return FileResponse(potential_file_path)

        # detailed 404 for debugging if needed, but for SPA we return index.html
        return FileResponse(f"{static_path}/index.html")

    # Root route
    @app.get("/", include_in_schema=False)
    async def root():
        return FileResponse(f"{static_path}/index.html")

if __name__ == "__main__":
    logger.info("Starting Document Validation Service on 0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)