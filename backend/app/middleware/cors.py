from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

def setup_cors(app: FastAPI) -> None:
    """
    Applies CORSMiddleware to the FastAPI application.
    Configures secure origins based on environment.
    """
    if settings.ENVIRONMENT == "production":
        # In production, specify exact allowed origins.
        # Avoid wildcard '*' in regulated banking/healthcare environments.
        allowed_origins = [
            "https://portal.mybank.secure",
            "https://api.mybank.secure"
        ]
        allow_credentials = True
    else:
        # Development allow local hosts
        allowed_origins = [
            "http://localhost",
            "http://localhost:8000",
            "http://localhost:3000",
            "http://127.0.0.1",
            "http://127.0.0.1:8000"
        ]
        allow_credentials = True

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=allow_credentials,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Request-ID", "X-API-Key"],
        expose_headers=["X-Request-ID"],
        max_age=600, # Cache preflight response for 10 minutes
    )
