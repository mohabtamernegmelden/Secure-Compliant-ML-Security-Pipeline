import jwt
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from passlib.context import CryptContext
from fastapi import HTTPException, status
from app.config import settings
from app.services.logging_service import security_logger

# Password hashing configuration
# Use a scheme that is reliable in the current runtime environment for production-safe password verification.
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# Hardcoded user database for demonstration/testing (in production, query a secure DB)
# Password hashes generated via pwd_context.hash("...")
USER_DB = {
    "admin": {
        "username": "admin",
        "hashed_password": pwd_context.hash("AdminPass123!"),
        "role": "Admin",
        "is_active": True
    },
    "analyst": {
        "username": "analyst",
        "hashed_password": pwd_context.hash("AnalystPass123!"),
        "role": "Analyst",
        "is_active": True
    },
    "user": {
        "username": "user",
        "hashed_password": pwd_context.hash("UserPass123!"),
        "role": "User",
        "is_active": True
    }
}

class AuthService:
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def create_jwt_token(data: Dict[str, Any], expires_delta: timedelta, secret_key: str) -> str:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + expires_delta
        to_encode.update({"exp": int(expire.timestamp())})
        # Explicitly specify HS256 algorithm to prevent alg: none vulnerability
        encoded_jwt = jwt.encode(to_encode, secret_key, algorithm="HS256")
        return encoded_jwt

    @classmethod
    def create_access_token(cls, username: str, role: str) -> str:
        data = {"sub": username, "role": role, "type": "access"}
        return cls.create_jwt_token(
            data=data,
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
            secret_key=settings.JWT_SECRET_KEY
        )

    @classmethod
    def create_refresh_token(cls, username: str) -> str:
        data = {"sub": username, "type": "refresh"}
        return cls.create_jwt_token(
            data=data,
            expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            secret_key=settings.REFRESH_JWT_SECRET_KEY
        )

    @staticmethod
    def verify_token(token: str, secret_key: str, token_type: str = "access") -> Dict[str, Any]:
        try:
            # Decode using explicit algorithm matching
            payload = jwt.decode(token, secret_key, algorithms=["HS256"])
            
            # Check type
            if payload.get("type") != token_type:
                raise jwt.InvalidTokenError("Token type mismatch")
                
            # Verify required fields
            if "sub" not in payload:
                raise jwt.InvalidTokenError("Subject claim missing")
                
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid credentials: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    @classmethod
    def authenticate_user(cls, username: str, password: str) -> Optional[Dict[str, Any]]:
        user = USER_DB.get(username)
        if not user:
            return None
        if not cls.verify_password(password, user["hashed_password"]):
            return None
        if not user["is_active"]:
            return None
        return user
