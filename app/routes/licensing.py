from fastapi import APIRouter, HTTPException
from app.services.license_service import LicenseService

router = APIRouter(prefix="/api/license", tags=["Licensing & Quotas"])

@router.get("/status/{user_id}")
def get_user_license_status(user_id: str):
    """Fetches user tier and real-time token status for UI rendering."""
    profile = LicenseService.get_user_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")
    
    return {
        "success": True,
        "email": profile.get("email"),
        "tier": profile.get("tier"),
        "tokens_used_today": profile.get("tokens_used_today"),
        "daily_limit": 100,
        "is_pro": profile.get("tier") == "pro"
    }

@router.post("/consume/{user_id}")
def consume_token(user_id: str):
    """Validates quotas and increments token usage for a user."""
    success, message, current_count = LicenseService.verify_and_increment(user_id)
    if not success:
        raise HTTPException(status_code=403, detail=message)
        
    return {
        "success": True, 
        "message": "Token consumed successfully",
        "tokens_used_today": current_count
    }