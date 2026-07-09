import html
import json
import logging
import os
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple
from contextlib import asynccontextmanager

import joblib
import jwt
import numpy as np
import psutil
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from passlib.context import CryptContext
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

# Load local environment variables from .env if present
load_dotenv()

# ---------------------------
# Settings & secret loading
# ---------------------------
class Settings(BaseSettings):
    ENVIRONMENT: str = Field(default="development")
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)
    LOG_LEVEL: str = Field(default="INFO")
    JWT_SECRET_KEY: str = Field(default="e83d8e578a101b44d715dfeb6e6761fa63bc87e9cf19920d3f23a492fdfbc30b")
    REFRESH_JWT_SECRET_KEY: str = Field(default="9aefb20c6a8bb1cf5bcf7a61d157ebce60da3bb2e805560b299e525fd408f62c")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)
    API_KEY: str = Field(default="local-dev-api-key-replace-in-production")
    ENCRYPTION_KEY: Optional[str] = Field(default=None)
    ENCRYPTION_SALT: str = Field(default="ml_security_default_salt_change_in_prod")
    REDIS_URL: Optional[str] = Field(default=None)
    AZURE_KEYVAULT_URL: Optional[str] = Field(default=None)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()


def load_azure_secrets() -> None:
    if not settings.AZURE_KEYVAULT_URL:
        if settings.ENVIRONMENT == "production":
            print("Warning: AZURE_KEYVAULT_URL is not configured in production; falling back to local environment values.")
        return

    try:
        from azure.identity import DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient

        credential = DefaultAzureCredential()
        client = SecretClient(vault_url=settings.AZURE_KEYVAULT_URL, credential=credential)

        def get_secret(name: str, default_value: str) -> str:
            secret_name = name.replace("_", "-")
            try:
                return client.get_secret(secret_name).value
            except Exception as exc:  # pragma: no cover
                if settings.ENVIRONMENT == "production":
                    raise RuntimeError(f"Failed to load critical secret {name} from Azure Key Vault: {exc}")
                print(f"Warning: Failed to fetch secret '{name}' from Key Vault: {exc}. Using fallback value.")
                return default_value

        settings.JWT_SECRET_KEY = get_secret("JWT_SECRET_KEY", settings.JWT_SECRET_KEY)
        settings.REFRESH_JWT_SECRET_KEY = get_secret("REFRESH_JWT_SECRET_KEY", settings.REFRESH_JWT_SECRET_KEY)
        settings.API_KEY = get_secret("API_KEY", settings.API_KEY)
        settings.ENCRYPTION_KEY = get_secret("ENCRYPTION_KEY", settings.ENCRYPTION_KEY or "")
        settings.REDIS_URL = get_secret("REDIS_URL", settings.REDIS_URL or "")
    except Exception as exc:  # pragma: no cover
        if settings.ENVIRONMENT == "production":
            raise RuntimeError(f"Azure Key Vault connection failed in production: {exc}") from exc
        print(f"Azure Key Vault integration skipped: {exc}")


load_azure_secrets()


# ---------------------------
# Logging helpers
# ---------------------------
class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if hasattr(record, "request_id"):
            log_data["request_id"] = getattr(record, "request_id")
        if hasattr(record, "user"):
            log_data["user"] = getattr(record, "user")
        if hasattr(record, "ip_address"):
            log_data["ip_address"] = getattr(record, "ip_address")
        if hasattr(record, "latency_ms"):
            log_data["latency_ms"] = getattr(record, "latency_ms")
        if hasattr(record, "extra_data"):
            log_data.update(getattr(record, "extra_data"))
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logger(name: str, log_file: str, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    if logger.handlers:
        logger.handlers.clear()

    os.makedirs("logs", exist_ok=True)

    file_handler = RotatingFileHandler(
        filename=os.path.join("logs", log_file),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(JSONFormatter())
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JSONFormatter())
    logger.addHandler(console_handler)

    return logger


app_logger = setup_logger("app", "app.log")
security_logger = setup_logger("security", "security.log")
audit_logger = setup_logger("audit", "audit.log")
error_logger = setup_logger("error", "error.log", level=logging.ERROR)


def log_audit(user: str, endpoint: str, status_code: int, ip_address: str, latency_ms: float, prediction: Any = None, extra: Optional[Dict[str, Any]] = None) -> None:
    extra_data = extra.copy() if extra else {}
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
                "status": status_code,
                **extra_data,
            },
        },
    )


def log_security(event: str, user: str, ip_address: str, status: str = "FAILED", extra: Optional[Dict[str, Any]] = None) -> None:
    security_logger.warning(
        f"Security Event: {event} for user {user} [{status}]",
        extra={
            "user": user,
            "ip_address": ip_address,
            "extra_data": {
                "event": event,
                "status": status,
                **(extra or {}),
            },
        },
    )


# ---------------------------
# Utility helpers
# ---------------------------

def sanitize_input_text(value: str) -> str:
    if not isinstance(value, str):
        return value
    cleaned = html.escape(value)
    cleaned = re.sub(r"[\r\n]", "", cleaned)
    return cleaned.strip()


def validate_ip_format(ip: str) -> bool:
    ipv4_pattern = r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
    ipv6_pattern = r"^([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}$"
    return bool(re.match(ipv4_pattern, ip) or re.match(ipv6_pattern, ip))


# ---------------------------
# Authentication service
# ---------------------------
password_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

USER_DB: Dict[str, Dict[str, Any]] = {
    "admin": {
        "username": "admin",
        "hashed_password": password_context.hash("AdminPass123!"),
        "role": "Admin",
        "is_active": True,
    },
    "analyst": {
        "username": "analyst",
        "hashed_password": password_context.hash("AnalystPass123!"),
        "role": "Analyst",
        "is_active": True,
    },
    "user": {
        "username": "user",
        "hashed_password": password_context.hash("UserPass123!"),
        "role": "User",
        "is_active": True,
    },
}


class AuthService:
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return password_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_jwt_token(data: Dict[str, Any], expires_delta: timedelta, secret_key: str) -> str:
        payload = data.copy()
        expire = datetime.now(timezone.utc) + expires_delta
        payload["exp"] = int(expire.timestamp())
        return jwt.encode(payload, secret_key, algorithm="HS256")

    @classmethod
    def create_access_token(cls, username: str, role: str) -> str:
        data = {"sub": username, "role": role, "type": "access"}
        return cls.create_jwt_token(data, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES), settings.JWT_SECRET_KEY)

    @classmethod
    def create_refresh_token(cls, username: str) -> str:
        data = {"sub": username, "type": "refresh"}
        return cls.create_jwt_token(data, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS), settings.REFRESH_JWT_SECRET_KEY)

    @staticmethod
    def verify_token(token: str, secret_key: str, token_type: str = "access") -> Dict[str, Any]:
        try:
            payload = jwt.decode(token, secret_key, algorithms=["HS256"])
            if payload.get("type") != token_type:
                raise jwt.InvalidTokenError("Token type mismatch")
            if "sub" not in payload:
                raise jwt.InvalidTokenError("Subject claim missing")
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid credentials: {str(exc)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    @classmethod
    def authenticate_user(cls, username: str, password: str) -> Optional[Dict[str, Any]]:
        user = USER_DB.get(username)
        if not user or not cls.verify_password(password, user["hashed_password"]) or not user.get("is_active", False):
            return None
        return user


# ---------------------------
# Pydantic schemas
# ---------------------------
class LoginInput(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Username for login", json_schema_extra={"example": "analyst"})
    password: str = Field(..., min_length=8, max_length=128, description="Password for login", json_schema_extra={"example": "AnalystPass123!"})

    @field_validator("username")
    @classmethod
    def validate_username_alphanumeric(cls, value: str) -> str:
        cleaned = sanitize_input_text(value)
        if not re.match(r"^[a-zA-Z0-9_-]+$", cleaned):
            raise ValueError("Username must contain only alphanumeric characters, underscores, or hyphens")
        return cleaned.lower()


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT Access Token")
    refresh_token: str = Field(..., description="JWT Refresh Token")
    token_type: str = Field(default="bearer", description="Token type, typically bearer")
    role: str = Field(..., description="Role associated with the authenticated user")


class RefreshTokenInput(BaseModel):
    refresh_token: str = Field(..., description="Valid JWT Refresh Token")


class PredictionInput(BaseModel):
    age: int = Field(..., ge=18, le=120, description="Age of the entity or user")
    income: float = Field(..., ge=0.0, le=10000000.0, description="Annual income")
    transaction_amount: float = Field(..., ge=0.0, le=5000000.0, description="Amount being evaluated")
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Pre-calculated risk score")
    department: Literal["finance", "healthcare", "other"] = Field(..., description="Department originating the request")
    user_role: Literal["admin", "analyst", "user"] = Field(..., description="Role of the user making the request")

    @field_validator("department", "user_role")
    @classmethod
    def sanitize_string_fields(cls, value: str) -> str:
        return sanitize_input_text(value).lower()


class PredictionResponse(BaseModel):
    prediction: int = Field(..., description="Binary prediction output: 0 for low risk, 1 for high risk")
    probability: float = Field(..., ge=0.0, le=1.0, description="High-risk probability")
    model_version: str = Field(..., description="Model version serving this prediction")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    request_id: str = Field(..., description="Correlation request ID")
    processing_time_ms: float = Field(..., ge=0.0, description="Processing time in milliseconds")


class BatchPredictionInput(BaseModel):
    inputs: List[PredictionInput] = Field(..., min_length=1, max_length=100, description="Batch input records")


class BatchPredictionResponse(BaseModel):
    predictions: List[PredictionResponse] = Field(..., description="Prediction responses")
    model_version: str = Field(..., description="Model version")
    request_id: str = Field(..., description="Correlation ID")
    processing_time_ms: float = Field(..., ge=0.0, description="Total batch processing time")


# ---------------------------
# Model and preprocessing
# ---------------------------
class ModelService:
    def __init__(self) -> None:
        base_dir = Path(__file__).resolve().parents[1]
        models_dir = Path(os.getenv("MODEL_DIR", base_dir / "models"))
        if not models_dir.exists():
            fallback_dir = Path.cwd() / "models"
            if fallback_dir.exists():
                models_dir = fallback_dir

        self.model_version = "UNKNOWN"
        self.model = None

        model_path = models_dir / "best_model.pkl"
        if not model_path.exists():
            app_logger.error(f"CRITICAL: Model file not found at {model_path}. Prediction endpoints will be unavailable.")
            return

        try:
            app_logger.info(f"Loading ML model from {model_path}...")
            self.model = joblib.load(model_path)
            self.model_version = "1.0.0"
            app_logger.info(f"Model version {self.model_version} loaded successfully.")
        except Exception as exc:
            app_logger.error(f"Failed to load model: {exc}")

    def predict(self, features: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        if self.model is None:
            raise RuntimeError("Model is not loaded.")

        predictions = np.asarray(self.model.predict(features))
        if hasattr(self.model, "predict_proba"):
            probabilities = np.asarray(self.model.predict_proba(features))
            if probabilities.ndim == 1:
                probabilities = probabilities.reshape(-1, 1)
            if probabilities.shape[1] == 1:
                positive_probability = probabilities[:, 0]
                probabilities = np.column_stack((1 - positive_probability, positive_probability))
            else:
                positive_probability = probabilities[:, -1]
                probabilities = np.column_stack((1 - positive_probability, positive_probability))
        else:
            probabilities = np.column_stack((1 - predictions.astype(float), predictions.astype(float)))

        return predictions, probabilities


class PreprocessingService:
    def __init__(self) -> None:
        base_dir = Path(__file__).resolve().parents[1]
        models_dir = Path(os.getenv("MODEL_DIR", base_dir / "models"))
        if not models_dir.exists():
            fallback_dir = Path.cwd() / "models"
            if fallback_dir.exists():
                models_dir = fallback_dir

        self.feature_config: Optional[Dict[str, Any]] = None
        self.num_features: List[str] = []
        self.cat_features: List[str] = []
        self.scaler = None
        self.encoder = None

        config_path = models_dir / "feature_columns.json"
        if not config_path.exists():
            app_logger.error(f"CRITICAL: Feature config not found at {config_path}. Preprocessing will be unavailable.")
            return

        with open(config_path, "r", encoding="utf-8") as handle:
            self.feature_config = json.load(handle)

        self.num_features = self.feature_config.get("numerical_features", [])
        self.cat_features = self.feature_config.get("categorical_features", [])

        if self.num_features:
            scaler_path = models_dir / "scaler.pkl"
            if scaler_path.exists():
                self.scaler = joblib.load(scaler_path)
                app_logger.info(f"Loaded scaler for {len(self.num_features)} numerical features.")
            else:
                app_logger.warning(f"Missing scaler asset at {scaler_path}; using raw numerical values.")

        if self.cat_features:
            encoder_path = models_dir / "encoder.pkl"
            if encoder_path.exists():
                self.encoder = joblib.load(encoder_path)
                app_logger.info(f"Loaded encoder for {len(self.cat_features)} categorical features.")
            else:
                app_logger.warning(f"Missing encoder asset at {encoder_path}; using raw categorical values.")

        app_logger.info("Preprocessing service initialized.")

    def preprocess_batch(self, inputs: List[Dict[str, Any]]) -> np.ndarray:
        if self.feature_config is None:
            raise RuntimeError("Preprocessing configuration is missing.")

        features: List[np.ndarray] = []
        if self.num_features:
            numeric_rows = [[float(item[feat]) for feat in self.num_features] for item in inputs]
            numeric_array = np.asarray(numeric_rows, dtype=float)
            features.append(self.scaler.transform(numeric_array) if self.scaler else numeric_array)

        if self.cat_features:
            categorical_rows = [[item[feat] for feat in self.cat_features] for item in inputs]
            categorical_array = np.asarray(categorical_rows, dtype=object)
            features.append(self.encoder.transform(categorical_array) if self.encoder else categorical_array)

        if not features:
            return np.asarray([list(item.values()) for item in inputs], dtype=object)

        return np.hstack(features)

    def preprocess_single(self, data: Dict[str, Any]) -> np.ndarray:
        return self.preprocess_batch([data])


model_service = ModelService()
preprocessing_service = PreprocessingService()


# ---------------------------
# Authentication dependencies
# ---------------------------
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login", auto_error=False)
limiter = Limiter(key_func=lambda request: request.client.host if request.client else "unknown")


def get_client_ip(request: Request) -> str:
    client_host = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        first_ip = forwarded.split(",")[0].strip()
        if validate_ip_format(first_ip):
            return first_ip
    return client_host


async def verify_jwt_or_api_key(request: Request, token: Optional[str] = Depends(oauth2_scheme), api_key: Optional[str] = Depends(api_key_header)) -> Dict[str, Any]:
    client_ip = get_client_ip(request)

    if api_key is not None:
        if api_key == settings.API_KEY:
            request.state.username = "api-service-client"
            return {"username": "api-service-client", "role": "Service"}
        log_security("Invalid API Key presented in multi-auth", "service-client", client_ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key", headers={"WWW-Authenticate": "ApiKey"})

    if token is not None:
        payload = AuthService.verify_token(token, settings.JWT_SECRET_KEY, token_type="access")
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")

        user = USER_DB.get(username)
        if not user or not user.get("is_active", False):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is inactive or missing")

        user_role = user.get("role")
        if user_role not in ["Analyst", "Admin"]:
            log_security(
                f"Unauthorized inference attempt to {request.url.path} (Has: {user_role})",
                username,
                client_ip,
                status="FORBIDDEN",
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Access denied: role '{user_role}' does not have permission")

        request.state.username = username
        return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated. Bearer token or X-API-Key is required.",
        headers={"WWW-Authenticate": "Bearer, ApiKey"},
    )


# ---------------------------
# Middleware
# ---------------------------
class AuditLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.perf_counter()
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        client_host = get_client_ip(request)

        try:
            response = await call_next(request)
        except Exception as exc:
            latency_ms = (time.perf_counter() - start_time) * 1000
            log_audit(
                user="anonymous",
                endpoint=request.url.path,
                status_code=500,
                ip_address=client_host,
                latency_ms=latency_ms,
                extra={"error": str(exc), "request_id": request_id},
            )
            raise

        latency_ms = (time.perf_counter() - start_time) * 1000
        response.headers["X-Request-ID"] = request_id
        log_audit(
            user=getattr(request.state, "username", "anonymous"),
            endpoint=request.url.path,
            status_code=response.status_code,
            ip_address=client_host,
            latency_ms=latency_ms,
            extra={"request_id": request_id},
        )
        return response


def setup_cors(application: FastAPI) -> None:
    if settings.ENVIRONMENT == "production":
        allowed_origins = ["https://portal.mybank.secure", "https://api.mybank.secure"]
    else:
        allowed_origins = [
            "http://localhost",
            "http://localhost:8000",
            "http://localhost:3000",
            "http://127.0.0.1",
            "http://127.0.0.1:8000",
        ]

    application.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Request-ID", "X-API-Key"],
        expose_headers=["X-Request-ID"],
        max_age=600,
    )


# ---------------------------
# FastAPI application
# ---------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    app_logger.info("Starting Secure & Compliant ML Security Pipeline Backend")
    app_logger.info(f"Environment: {settings.ENVIRONMENT}")
    app_logger.info(f"Model loaded: {model_service.model is not None}")
    app_logger.info("Application startup complete.")
    yield

app = FastAPI(
    title="Secure & Compliant ML Security Pipeline",
    description="Single-file secure ML inference backend.",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan,
)

setup_cors(app)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(AuditLoggingMiddleware)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.middleware("http")
async def add_security_headers(request: Request, call_next) -> Response:
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    if settings.ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none'; object-src 'none';"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    app_logger.warning(f"Request validation failed [{request_id}]: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "message": "The request payload failed validation rules.",
            "request_id": request_id,
            "details": [{"field": ".".join(map(str, err["loc"][1:])), "message": err["msg"]} for err in exc.errors()],
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "HTTP Error", "message": exc.detail, "request_id": request_id},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    error_logger.exception(f"Unhandled exception occurred [{request_id}]: {exc}", extra={"request_id": request_id})
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. Please contact system support.",
            "request_id": request_id,
        },
    )


@app.get("/", tags=["General"])
@limiter.exempt
async def root() -> Dict[str, str]:
    return {
        "status": "online",
        "message": "Secure & Compliant ML Security Pipeline API",
        "documentation": "/docs",
    }


@app.get("/ui", tags=["General"])
@limiter.exempt
async def ui_page() -> HTMLResponse:
    html_content = """
    <!DOCTYPE html>
    <html lang=\"en\">
    <head>
        <meta charset=\"utf-8\" />
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
        <title>Secure and Compliant ML Security Pipeline</title>
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
    return HTMLResponse(content=html_content)


@app.get("/health", tags=["Monitoring"])
@limiter.exempt
async def health_check() -> Dict[str, Any]:
    health_status = "healthy"
    details: Dict[str, Any] = {}

    model_loaded = model_service.model is not None
    details["model_loaded"] = model_loaded
    if not model_loaded:
        health_status = "unhealthy"
        app_logger.error("Health check failed: Model is not loaded.")

    try:
        disk_usage = psutil.disk_usage("/")
        disk_free_pct = (disk_usage.free / disk_usage.total) * 100
        details["disk_free_percent"] = round(disk_free_pct, 2)
        if disk_free_pct < 5.0:
            health_status = "degraded"
            app_logger.warning(f"Health check degraded: Disk space low ({details['disk_free_percent']}% free).")
    except Exception as exc:
        details["disk_check_error"] = str(exc)
        app_logger.error(f"Failed to check disk usage: {exc}")

    try:
        mem = psutil.virtual_memory()
        mem_avail_pct = (mem.available / mem.total) * 100
        details["memory_available_percent"] = round(mem_avail_pct, 2)
        if mem_avail_pct < 5.0:
            health_status = "degraded"
            app_logger.warning(f"Health check degraded: Memory availability low ({details['memory_available_percent']}% available).")
    except Exception as exc:
        details["memory_check_error"] = str(exc)
        app_logger.error(f"Failed to check memory usage: {exc}")

    if health_status == "unhealthy":
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"status": health_status, "details": details})

    return {"status": health_status, "details": details}


@app.get("/version", tags=["Monitoring"])
@limiter.exempt
async def version() -> Dict[str, str]:
    return {"api_version": "1.0.0", "model_version": model_service.model_version}


@app.post("/login", response_model=TokenResponse, tags=["Authentication"])
@limiter.limit("20/minute")
async def login(credentials: LoginInput, request: Request) -> TokenResponse:
    client_ip = get_client_ip(request)
    user = AuthService.authenticate_user(credentials.username, credentials.password)
    if not user:
        log_security("Failed login attempt", credentials.username, client_ip, status="UNAUTHORIZED")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password", headers={"WWW-Authenticate": "Bearer"})

    log_security("Successful login", user["username"], client_ip, status="SUCCESS")
    access_token = AuthService.create_access_token(user["username"], user["role"])
    refresh_token = AuthService.create_refresh_token(user["username"])
    return TokenResponse(access_token=access_token, refresh_token=refresh_token, token_type="bearer", role=user["role"])


@app.post("/refresh-token", response_model=TokenResponse, tags=["Authentication"])
@limiter.limit("20/minute")
async def refresh_token(body: RefreshTokenInput, request: Request) -> TokenResponse:
    client_ip = get_client_ip(request)
    payload = AuthService.verify_token(body.refresh_token, settings.REFRESH_JWT_SECRET_KEY, token_type="refresh")
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token claims")

    user = USER_DB.get(username)
    if not user or not user.get("is_active", False):
        log_security("Failed token refresh (user inactive or missing)", username, client_ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is inactive or not found")

    log_security("Refreshed JWT tokens", username, client_ip, status="SUCCESS")
    return TokenResponse(
        access_token=AuthService.create_access_token(user["username"], user["role"]),
        refresh_token=AuthService.create_refresh_token(user["username"]),
        token_type="bearer",
        role=user["role"],
    )


@app.post("/predict", response_model=PredictionResponse, tags=["Inference"])
@limiter.limit("50/minute")
async def predict_single(request: Request, input_payload: PredictionInput, current_user: Dict[str, Any] = Depends(verify_jwt_or_api_key)) -> PredictionResponse:
    start_time = time.perf_counter()
    request_id = getattr(request.state, "request_id", "unknown")

    if model_service.model is None or preprocessing_service.feature_config is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="ML Model is not configured. Please place the official model artifacts in the models/ directory.")

    processed_features = preprocessing_service.preprocess_single(input_payload.model_dump())
    predictions, probabilities = model_service.predict(processed_features)
    prediction = int(predictions[0])
    probability = float(probabilities[0][-1])
    latency_ms = (time.perf_counter() - start_time) * 1000

    return PredictionResponse(
        prediction=prediction,
        probability=probability,
        model_version=model_service.model_version,
        timestamp=datetime.now(timezone.utc).isoformat(),
        request_id=request_id,
        processing_time_ms=round(latency_ms, 2),
    )


@app.post("/batch-predict", response_model=BatchPredictionResponse, tags=["Inference"])
@limiter.limit("20/minute")
async def predict_batch(request: Request, batch_payload: BatchPredictionInput, current_user: Dict[str, Any] = Depends(verify_jwt_or_api_key)) -> BatchPredictionResponse:
    start_time = time.perf_counter()
    request_id = getattr(request.state, "request_id", "unknown")

    if model_service.model is None or preprocessing_service.feature_config is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="ML Model is not configured. Please place the official model artifacts in the models/ directory.")

    processed_features = preprocessing_service.preprocess_batch([item.model_dump() for item in batch_payload.inputs])
    predictions, probabilities = model_service.predict(processed_features)
    timestamp_str = datetime.now(timezone.utc).isoformat()

    return BatchPredictionResponse(
        predictions=[
            PredictionResponse(
                prediction=int(predictions[idx]),
                probability=float(probabilities[idx][-1]),
                model_version=model_service.model_version,
                timestamp=timestamp_str,
                request_id=request_id,
                processing_time_ms=0.0,
            )
            for idx in range(len(batch_payload.inputs))
        ],
        model_version=model_service.model_version,
        request_id=request_id,
        processing_time_ms=round((time.perf_counter() - start_time) * 1000, 2),
    )
