from typing import List, Dict, Any, Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from app.config import settings
from app.services.auth_service import AuthService, USER_DB
from app.services.logging_service import log_security

# Define authentication schemes with auto_error=False to support fallback verification
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login", auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_current_user(request: Request, token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """
    Dependency to authenticate and retrieve the current user from the JWT access token.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Verify access token structure and signature
    payload = AuthService.verify_token(token, settings.JWT_SECRET_KEY, token_type="access")
    username = payload.get("sub")
    if not username:
        raise credentials_exception
        
    user = USER_DB.get(username)
    if not user:
        # User not found in database
        log_security("Authenticated user not found in DB", username, request.client.host if request.client else "unknown")
        raise credentials_exception
        
    # Inject username into request state for audit logger middleware
    request.state.username = username
    return user

async def get_current_active_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Dependency to verify that the authenticated user account is active.
    """
    if not current_user.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )
    return current_user

class RoleChecker:
    """
    Authorization class to restrict endpoint access by roles.
    """
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, request: Request, current_user: Dict[str, Any] = Depends(get_current_active_user)) -> Dict[str, Any]:
        user_role = current_user.get("role")
        if user_role not in self.allowed_roles:
            client_ip = request.client.host if request.client else "unknown"
            log_security(
                event=f"Unauthorized access attempt to {request.url.path} (Required: {self.allowed_roles}, Has: {user_role})",
                user=current_user.get("username", "unknown"),
                ip_address=client_ip,
                status="FORBIDDEN"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: role '{user_role}' does not have permission to access this resource"
            )
        return current_user

async def verify_api_key(request: Request, api_key: str = Depends(api_key_header)) -> str:
    """
    Alternative authentication method using a pre-shared API Key header.
    Suitable for automated service-to-service communication.
    """
    if not api_key or api_key != settings.API_KEY:
        client_ip = request.client.host if request.client else "unknown"
        log_security("Invalid API Key presented", "service-client", client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    # Set dummy name for logging
    request.state.username = "api-service-client"
    return api_key

async def verify_jwt_or_api_key(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    api_key: Optional[str] = Depends(api_key_header)
) -> Dict[str, Any]:
    """
    Combined dependency that supports either valid X-API-Key headers OR a valid JWT token
    with roles: 'Analyst' or 'Admin'. Used to secure inference routes.
    """
    client_ip = request.client.host if request.client else "unknown"
    
    # 1. API Key Auth check (takes priority if present)
    if api_key is not None:
        if api_key == settings.API_KEY:
            request.state.username = "api-service-client"
            return {"username": "api-service-client", "role": "Service"}
        else:
            log_security("Invalid API Key presented in multi-auth", "service-client", client_ip)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API Key",
                headers={"WWW-Authenticate": "ApiKey"},
            )
            
    # 2. JWT Auth check
    if token is not None:
        try:
            payload = AuthService.verify_token(token, settings.JWT_SECRET_KEY, token_type="access")
            username = payload.get("sub")
            if not username:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")
                
            user = USER_DB.get(username)
            if not user or not user.get("is_active", False):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is inactive or missing")
                
            # Perform role authorization
            user_role = user.get("role")
            if user_role not in ["Analyst", "Admin"]:
                log_security(
                    event=f"Unauthorized inference attempt to {request.url.path} (Has: {user_role})",
                    user=username,
                    ip_address=client_ip,
                    status="FORBIDDEN"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied: role '{user_role}' does not have permission"
                )
                
            request.state.username = username
            return user
        except HTTPException as e:
            # Re-raise HTTPExceptions as-is
            raise e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Authentication failed: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
    # 3. Neither present
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated. Bearer token or X-API-Key is required.",
        headers={"WWW-Authenticate": "Bearer, ApiKey"},
    )
