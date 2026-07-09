import os
import json
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone
from typing import Any, Dict

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

class JSONFormatter(logging.Formatter):
    """
    Custom formatter to output logs in structured JSON format.
    """
    def format(self, record: logging.LogRecord) -> str:
        # Standard fields
        log_data: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add correlation ID (request_id) if present
        if hasattr(record, "request_id"):
            log_data["request_id"] = getattr(record, "request_id")
            
        # Add user identification if present
        if hasattr(record, "user"):
            log_data["user"] = getattr(record, "user")
            
        # Add IP address if present
        if hasattr(record, "ip_address"):
            log_data["ip_address"] = getattr(record, "ip_address")
            
        # Add performance latency if present
        if hasattr(record, "latency_ms"):
            log_data["latency_ms"] = getattr(record, "latency_ms")

        # Inject extra dictionary parameters if they were provided
        if hasattr(record, "extra_data"):
            log_data.update(getattr(record, "extra_data"))
            
        # Add exception details if present and we're in the error/app logger
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)

def setup_logger(name: str, log_file: str, level=logging.INFO) -> logging.Logger:
    """
    Helper function to configure a logger with a RotatingFileHandler and JSONFormatter.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False # Prevent duplication in default console output
    
    # Remove existing handlers to avoid duplicates
    if logger.handlers:
        logger.handlers.clear()
        
    # File Handler
    file_handler = RotatingFileHandler(
        filename=os.path.join("logs", log_file),
        maxBytes=10 * 1024 * 1024, # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(JSONFormatter())
    logger.addHandler(file_handler)
    
    # Console Handler for container environments
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JSONFormatter())
    logger.addHandler(console_handler)
    
    return logger

# Initialize distinct loggers
app_logger = setup_logger("app", "app.log")
security_logger = setup_logger("security", "security.log")
audit_logger = setup_logger("audit", "audit.log")
error_logger = setup_logger("error", "error.log", level=logging.ERROR)

def log_audit(user: str, endpoint: str, status: int, ip_address: str, latency_ms: float, prediction: Any = None, extra: Dict[str, Any] = None):
    """
    Helper to write audit log entries.
    """
    extra_data = extra or {}
    if prediction is not None:
        extra_data["prediction"] = prediction
        
    audit_logger.info(
        f"Audit: {user} accessed {endpoint}",
        extra={
            "user": user,
            "ip_address": ip_address,
            "latency_ms": latency_ms,
            "extra_data": {
                "endpoint": endpoint,
                "status": status,
                **extra_data
            }
        }
    )

def log_security(event: str, user: str, ip_address: str, status: str = "FAILED", extra: Dict[str, Any] = None):
    """
    Helper to write security log entries.
    """
    security_logger.warning(
        f"Security Event: {event} for user {user} [{status}]",
        extra={
            "user": user,
            "ip_address": ip_address,
            "extra_data": {
                "event": event,
                "status": status,
                **(extra or {})
            }
        }
    )
