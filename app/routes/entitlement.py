import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import require_authenticated_user
from app.services.entitlement_service import issue_local_presentation_entitlement
from app.services.license_service import LicenseService

router = APIRouter(prefix="/v1", tags=["entitlement"])
logger = logging.getLogger(__name__)


@router.post("/entitlement/local-presentation")
def get_local_presentation_entitlement(
    user_id: str = Depends(require_authenticated_user),
) -> dict:
    """Issue a seven-day offline entitlement to an active Pro subscriber."""
    if not LicenseService.has_local_presentation_access(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="An active Pro subscription is required for local presentation generation.",
        )
    try:
        return issue_local_presentation_entitlement(user_id)
    except RuntimeError:
        logger.exception("Local entitlement signing is not configured.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Local entitlement service is not configured.",
        )
