from pathlib import Path
from typing import Dict, Any

import psutil
from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse
from app.services.compliance_service import compliance_service
from app.services.model_service import model_service
from app.services.logging_service import app_logger
from app.utils.limiter import limiter

router = APIRouter()

@router.get("/ui", tags=["General"])
@limiter.exempt
async def ui_page() -> HTMLResponse:
    """Serve a simple web interface for interacting with the API."""
    html = """
    <!DOCTYPE html>
    <html lang=\"en\">
    <head>
        <meta charset=\"utf-8\" />
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
        <title>Secure ML Security Pipeline</title>
        <style>
            :root { color-scheme: dark; }
            body { font-family: Arial, sans-serif; margin: 0; background: linear-gradient(135deg, #07111f, #10253d); color: #f5f7fb; }
            .container { max-width: 980px; margin: 0 auto; padding: 48px 24px 80px; }
            .card { background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.14); border-radius: 20px; padding: 24px; box-shadow: 0 16px 50px rgba(0,0,0,0.25); }
            h1 { margin-top: 0; font-size: 2rem; }
            p { line-height: 1.6; color: #dce7f7; }
            button { background: #4f8cff; border: none; color: white; padding: 12px 16px; border-radius: 10px; cursor: pointer; font-weight: 600; }
            button:hover { background: #3e75d8; }
            textarea, input { width: 100%; border-radius: 10px; border: 1px solid #4f8cff; padding: 10px; margin-top: 8px; background: #0d1728; color: white; }
            .grid { display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); }
            .result { margin-top: 16px; padding: 14px; border-radius: 10px; background: rgba(79,140,255,0.16); white-space: pre-wrap; }
        </style>
    </head>
    <body>
        <div class=\"container\">
            <div class=\"card\">
                <h1>Secure & Compliant ML Security Pipeline</h1>
                <p>Use this lightweight dashboard to test the fraud-risk inference API from your browser.</p>
                <div class=\"grid\">
                    <div>
                        <label>API Key</label>
                        <input id=\"apiKey\" value=\"local-dev-api-key-replace-in-production\" />
                    </div>
                    <div>
                        <label>JSON Payload</label>
                        <textarea id=\"payload\" rows=\"10\">{"age":35,"income":75000.0,"transaction_amount":120.5,"risk_score":0.23,"department":"finance","user_role":"user"}</textarea>
                    </div>
                </div>
                <button onclick=\"submitPrediction()\">Run Prediction</button>
                <div id=\"result\" class=\"result\">Waiting for a request...</div>
            </div>
        </div>
        <script>
            async function submitPrediction() {
                const apiKey = document.getElementById('apiKey').value;
                const payload = JSON.parse(document.getElementById('payload').value);
                const result = document.getElementById('result');
                try {
                    const response = await fetch('/predict', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', 'X-API-Key': apiKey },
                        body: JSON.stringify(payload)
                    });
                    const data = await response.json();
                    result.textContent = JSON.stringify(data, null, 2);
                } catch (error) {
                    result.textContent = 'Request failed: ' + error.message;
                }
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

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

    if health_status == "unhealthy" or not (Path("models") / "best_model.pkl").exists():
        return JSONResponse(
            status_code=503,
            content={"error": "HTTP Error", "message": {"status": "unhealthy", "details": {**details, "model_loaded": model_loaded}}},
        )

    return {
        "status": "healthy" if health_status != "degraded" else "healthy",
        "model_loaded": model_loaded,
        "details": details
    }

@router.get("/compliance", tags=["Monitoring"])
@limiter.exempt
async def compliance() -> Dict[str, Any]:
    return {"compliance_pipeline": compliance_service.get_pipeline_status()}


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
