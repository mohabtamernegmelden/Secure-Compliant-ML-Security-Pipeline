from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.routers.auth import router as auth_router
from app.routers.health import router as health_router
from app.routers.predict import router as predict_router
from app.services.logging_service import app_logger
from app.services.model_service import model_service
from app.services.preprocessing_service import preprocessing_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    app_logger.info("Starting Secure & Compliant ML Security Pipeline")
    app_logger.info("Model loaded: %s", model_service.model is not None)
    yield


app = FastAPI(
    title="Secure & Compliant ML Security Pipeline",
    description="Model-agnostic intrusion detection API with frontend UI",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or "req-" + request.url.path.replace("/", "-")
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


app.include_router(health_router)
app.include_router(auth_router)
app.include_router(predict_router)

static_dir = Path(__file__).resolve().parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir), html=True), name="static")
    assets_dir = static_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if isinstance(exc.detail, dict):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"message": str(exc.detail)})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": "Validation Error", "message": "Invalid request payload"},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Log the full exception for server-side diagnostics but return a safe JSON response
    app_logger.exception("Unhandled exception while processing request %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "message": "An unexpected error occurred"},
    )


@app.get("/", tags=["General"])
async def index(request: Request):
    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header and (static_dir / "index.html").exists():
        return FileResponse(static_dir / "index.html")
    return {
        "status": "online",
        "message": "Secure & Compliant ML Security Pipeline API",
        "documentation": "/docs",
    }
