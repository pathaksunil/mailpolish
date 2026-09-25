"""Authentication and entitlement dependencies for paid cloud endpoints."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.database import supabase
from app.services.license_service import LicenseService

bearer_scheme = HTTPBearer(auto_error=False)


def require_authenticated_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    """Validate a Supabase bearer token and return its authenticated user ID."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in to use cloud generation.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_response = supabase.auth.get_user(credentials.credentials)
        user = getattr(user_response, "user", None)
        user_id = getattr(user, "id", None)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session is invalid or has expired. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session is invalid or has expired. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id


def require_cloud_entitlement(
    user_id: str = Depends(require_authenticated_user),
) -> str:
    """Require and meter a server-owned cloud generation request."""
    # This checks the profile/tier on every cloud request and increments the
    # free-tier counter. Pro users with an active subscription are unlimited.
    LicenseService.check_and_consume_token(user_id)
    return user_id
