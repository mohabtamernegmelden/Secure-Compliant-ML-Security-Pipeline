import psutil
from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any
from app.services.model_service import model_service
from app.services.logging_service import app_logger
from app.utils.limiter import limiter

router = APIRouter()

@router.get("/", tags=["General"])
@limiter.exempt
async def root() -> Dict[str, str]:
    """
    Root endpoint returning basic service status.
    """
    return {
        "status": "online",
        "message": "Secure & Compliant ML Security Pipeline API",
        "documentation": "/docs"
    }

@router.get("/health", tags=["Monitoring"])
@limiter.exempt
async def health_check() -> Dict[str, Any]:
    """
    Liveness and readiness check. Checks system memory, disk storage, and model loading status.
    """
    health_status = "healthy"
    details = {}
    
    # 1. Model Status
    model_loaded = model_service.model is not None
    details["model_loaded"] = model_loaded
    if not model_loaded:
        health_status = "unhealthy"
        app_logger.error("Health check failed: Model is not loaded.")
        
    # 2. Disk Check
    try:
        disk_usage = psutil.disk_usage("/")
        # Require at least 5% disk free space
        disk_free_pct = (disk_usage.free / disk_usage.total) * 100
        details["disk_free_percent"] = round(disk_free_pct, 2)
        if disk_free_pct < 5.0:
            health_status = "degraded"
            app_logger.warning(f"Health check degraded: Disk space low ({details['disk_free_percent']}% free).")
    except Exception as e:
        details["disk_check_error"] = str(e)
        app_logger.error(f"Failed to check disk usage: {e}")
        
    # 3. Memory Check
    try:
        mem = psutil.virtual_memory()
        # Require at least 5% available RAM
        mem_avail_pct = (mem.available / mem.total) * 100
        details["memory_available_percent"] = round(mem_avail_pct, 2)
        if mem_avail_pct < 5.0:
            health_status = "degraded"
            app_logger.warning(f"Health check degraded: Memory availability low ({details['memory_available_percent']}% available).")
    except Exception as e:
        details["memory_check_error"] = str(e)
        app_logger.error(f"Failed to check memory usage: {e}")

    # Set response code based on overall status
    if health_status == "unhealthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": health_status, "details": details}
        )
        
    return {
        "status": health_status,
        "details": details
    }

@router.get("/version", tags=["Monitoring"])
@limiter.exempt
async def version() -> Dict[str, str]:
    """
    Returns the software application version and the machine learning model version.
    """
    return {
        "api_version": "1.0.0",
        "model_version": model_service.model_version
    }
