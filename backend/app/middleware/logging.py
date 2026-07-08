import time
import uuid
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.services.logging_service import log_audit, app_logger, log_security
from app.utils.validators import validate_ip_format

class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to intercept HTTP requests and log audit information,
    track request execution time, and inject correlation request IDs.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.perf_counter()
        
        # 1. Retrieve or generate correlation Request ID
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())
            
        # Attach to state for dependency retrieval if needed
        request.state.request_id = request_id
        
        # 2. Extract Client IP
        client_host = request.client.host if request.client else "unknown"
        # Check forward headers if running behind proxy/load balancer
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the list
            potential_ip = forwarded_for.split(",")[0].strip()
            if validate_ip_format(potential_ip):
                client_host = potential_ip

        # 3. Handle Request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log raw exceptions to error logs
            latency_ms = (time.perf_counter() - start_time) * 1000
            log_audit(
                user="anonymous", 
                endpoint=request.url.path, 
                status=500, 
                ip_address=client_host, 
                latency_ms=latency_ms,
                extra={"error": str(e), "request_id": request_id}
            )
            # Re-raise to let custom exception handlers handle formatting
            raise e

        # 4. Measure execution duration
        process_time_ms = (time.perf_counter() - start_time) * 1000
        
        # Add correlation ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        # 5. Extract user if authenticated (e.g. from request state if set by security dependency)
        user = getattr(request.state, "username", "anonymous")
        
        # 6. Audit log execution details (avoid logging actual login password)
        # We can extract request paths
        path = request.url.path
        
        # Log to audit.log
        log_audit(
            user=user,
            endpoint=path,
            status=response.status_code,
            ip_address=client_host,
            latency_ms=process_time_ms,
            extra={"request_id": request_id}
        )

        return response
