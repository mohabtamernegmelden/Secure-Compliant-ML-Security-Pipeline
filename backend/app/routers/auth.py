from fastapi import APIRouter, Depends, HTTPException, Request, status
from app.schemas.auth import LoginInput, TokenResponse, RefreshTokenInput
from app.services.auth_service import AuthService
from app.services.logging_service import log_security, app_logger
from app.config import settings

router = APIRouter()

@router.post("/login", response_model=TokenResponse, tags=["Authentication"])
async def login(request: Request, credentials: LoginInput) -> TokenResponse:
    """
    Authenticate user and return JWT access and refresh tokens.
    """
    client_ip = request.client.host if request.client else "unknown"
    
    # Authenticate
    user = AuthService.authenticate_user(
        username=credentials.username,
        password=credentials.password
    )
    
    if not user:
        # Log auth failure event to security log (for threat detection/SIEM integration)
        log_security(
            event="Failed login attempt",
            user=credentials.username,
            ip_address=client_ip,
            status="UNAUTHORIZED"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # Log successful authentication event
    log_security(
        event="Successful login",
        user=user["username"],
        ip_address=client_ip,
        status="SUCCESS"
    )
    
    # Generate tokens
    access_token = AuthService.create_access_token(user["username"], user["role"])
    refresh_token = AuthService.create_refresh_token(user["username"])
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        role=user["role"]
    )

@router.post("/refresh-token", response_model=TokenResponse, tags=["Authentication"])
async def refresh_token(request: Request, body: RefreshTokenInput) -> TokenResponse:
    """
    Issue a new JWT access token and refresh token using a valid refresh token.
    """
    client_ip = request.client.host if request.client else "unknown"
    
    # Verify the refresh token signature and type
    payload = AuthService.verify_token(
        token=body.refresh_token,
        secret_key=settings.REFRESH_JWT_SECRET_KEY,
        token_type="refresh"
    )
    
    username = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token claims"
        )
        
    from app.services.auth_service import USER_DB
    user = USER_DB.get(username)
    if not user or not user["is_active"]:
        log_security("Failed token refresh (user inactive or missing)", username, client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive or not found"
        )
        
    # Log successful token refresh
    log_security(
        event="Refreshed JWT tokens",
        user=username,
        ip_address=client_ip,
        status="SUCCESS"
    )
    
    # Rotate tokens (issue new access AND new refresh token)
    new_access_token = AuthService.create_access_token(user["username"], user["role"])
    new_refresh_token = AuthService.create_refresh_token(user["username"])
    
    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        role=user["role"]
    )
