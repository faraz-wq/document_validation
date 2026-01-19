"""
Background task processing for validation
Handles async validation tasks to prevent blocking the main event loop
"""

import asyncio
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from app.logging_config import get_logger

logger = get_logger(__name__)


class TaskStatus:
    """Status tracking for background tasks"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ValidationTaskManager:
    """Manages background validation tasks"""
    
    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}
        logger.info("ValidationTaskManager initialized")
    
    def create_task(self, application_type: str, user_id: int) -> str:
        """
        Create a new validation task.
        
        Returns:
            task_id: Unique identifier for the task
        """
        task_id = str(uuid.uuid4())
        
        self._tasks[task_id] = {
            "task_id": task_id,
            "status": TaskStatus.PENDING,
            "application_type": application_type,
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "result": None,
            "error": None,
            "progress": 0
        }
        
        logger.info(f"Created task {task_id} for user {user_id}, type {application_type}")
        return task_id
    
    def update_task_status(
        self,
        task_id: str,
        status: str,
        result: Optional[Any] = None,
        error: Optional[str] = None,
        progress: Optional[int] = None
    ):
        """Update task status and metadata"""
        if task_id not in self._tasks:
            logger.warning(f"Attempted to update non-existent task: {task_id}")
            return
        
        task = self._tasks[task_id]
        task["status"] = status
        task["updated_at"] = datetime.now().isoformat()
        
        if result is not None:
            task["result"] = result
        if error is not None:
            task["error"] = error
        if progress is not None:
            task["progress"] = progress
        
        logger.debug(f"Task {task_id} updated: status={status}, progress={progress}")
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task information by ID"""
        return self._tasks.get(task_id)
    
    def get_user_tasks(self, user_id: int) -> list:
        """Get all tasks for a specific user"""
        return [
            task for task in self._tasks.values()
            if task["user_id"] == user_id
        ]
    
    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """Remove tasks older than max_age_hours"""
        from datetime import timedelta
        
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        tasks_to_remove = []
        
        for task_id, task in self._tasks.items():
            task_time = datetime.fromisoformat(task["created_at"])
            if task_time < cutoff:
                tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            del self._tasks[task_id]
            logger.debug(f"Cleaned up old task: {task_id}")
        
        if tasks_to_remove:
            logger.info(f"Cleaned up {len(tasks_to_remove)} old tasks")


# Global task manager instance
task_manager = ValidationTaskManager()
