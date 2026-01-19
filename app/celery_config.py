"""
Celery application configuration for background task processing
Handles async validation tasks to prevent blocking the main API
"""

import os
from celery import Celery
from app.logging_config import get_logger

logger = get_logger(__name__)

# Get Redis URL from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)

# Create Celery application
celery_app = Celery(
    "document_validation",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND
)

# Configure Celery
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # Timezone
    timezone="UTC",
    enable_utc=True,
    
    # Task routing and optimization
    task_routes={
        "app.celery_tasks.process_validation_task": {"queue": "validation"},
        "app.celery_tasks.process_extraction_task": {"queue": "extraction"},
    },
    
    # Worker optimization
    worker_prefetch_multiplier=1,  # Only fetch one task at a time
    task_acks_late=True,  # Acknowledge task after completion
    worker_max_tasks_per_child=100,  # Restart worker after 100 tasks (prevent memory leaks)
    
    # Task time limits
    task_time_limit=600,  # Hard limit: 10 minutes
    task_soft_time_limit=540,  # Soft limit: 9 minutes
    
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_extended=True,  # Store additional task metadata
    
    # Retry settings
    task_default_retry_delay=60,  # Wait 60 seconds before retry
    task_max_retries=3,  # Maximum 3 retries
)

logger.info(f"Celery configured with broker: {CELERY_BROKER_URL}")
