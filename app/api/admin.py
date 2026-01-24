"""
Admin endpoints for monitoring and management
Provides endpoints for checking system health, pool stats, and triggering cleanup
"""

from fastapi import APIRouter, Depends
from typing import Dict, Any
from app.api.v1.deps import get_current_user_from_jwt
from app.db.models import User as UserModel
from app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/admin/pool-stats")
async def get_pool_statistics(
    current_user: UserModel = Depends(get_current_user_from_jwt)
) -> Dict[str, Any]:
    """
    Get database connection pool statistics.
    Requires authentication.
    """
    from app.db.database import get_pool_stats
    
    stats = get_pool_stats()
    logger.info(f"Pool stats requested by user {current_user.id}")
    
    return {
        "pool_statistics": stats,
        "user_id": current_user.id
    }


@router.get("/admin/cleanup-stats")
async def get_cleanup_statistics(
    current_user: UserModel = Depends(get_current_user_from_jwt)
) -> Dict[str, Any]:
    """
    Get file cleanup service statistics.
    Shows disk usage for monitored directories.
    Requires authentication.
    """
    from app.utils.file_cleanup import file_cleanup_service
    
    stats = file_cleanup_service.get_directory_stats()
    logger.info(f"Cleanup stats requested by user {current_user.id}")
    
    return {
        "directory_statistics": stats,
        "user_id": current_user.id
    }


@router.post("/admin/cleanup-trigger")
async def trigger_manual_cleanup(
    current_user: UserModel = Depends(get_current_user_from_jwt)
) -> Dict[str, Any]:
    """
    Manually trigger file cleanup.
    Returns statistics about files deleted and space freed.
    Requires authentication.
    """
    from app.utils.file_cleanup import file_cleanup_service
    
    logger.info(f"Manual cleanup triggered by user {current_user.id}")
    cleanup_result = file_cleanup_service.manual_cleanup()
    
    return {
        "cleanup_result": cleanup_result,
        "triggered_by": current_user.id
    }


@router.get("/admin/system-health")
async def get_system_health(
    current_user: UserModel = Depends(get_current_user_from_jwt)
) -> Dict[str, Any]:
    """
    Get comprehensive system health information.
    Includes database, pool stats, and disk usage.
    Requires authentication.
    """
    from app.db.database import check_db_connection, get_pool_stats
    from app.utils.file_cleanup import file_cleanup_service
    import psutil
    
    # Database health
    db_healthy = check_db_connection()
    pool_stats = get_pool_stats()
    
    # Disk usage
    directory_stats = file_cleanup_service.get_directory_stats()
    
    # System resources
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    health_info = {
        "status": "healthy" if db_healthy else "degraded",
        "database": {
            "connected": db_healthy,
            "pool": pool_stats
        },
        "storage": {
            "directories": directory_stats,
            "disk_usage": {
                "total_gb": disk.total / (1024**3),
                "used_gb": disk.used / (1024**3),
                "free_gb": disk.free / (1024**3),
                "percent_used": disk.percent
            }
        },
        "system": {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_gb": memory.available / (1024**3)
        },
        "checked_by": current_user.id
    }
    
    logger.info(f"System health check requested by user {current_user.id}")
    
    return health_info
