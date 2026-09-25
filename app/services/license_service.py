from datetime import datetime, timezone

from fastapi import HTTPException
from app.core.database import supabase

class LicenseService:
    @staticmethod
    def get_user_profile(user_id: str) -> dict | None:
        response = supabase.table("user_profiles").select("*").eq("id", user_id).execute()
        return response.data[0] if response.data else None

    @staticmethod
    def has_local_presentation_access(user_id: str) -> bool:
        """Only Ultra and Private AI include local presentation generation."""
        subscription = LicenseService.get_latest_subscription(user_id)
        return bool(subscription and subscription.get("plan_code") in {"ultra", "private_ai"} and LicenseService.has_active_subscription(user_id))

    @staticmethod
    def get_latest_subscription(user_id: str) -> dict | None:
        """Return the newest subscription record for this user, if any."""
        response = (
            supabase.table("subscriptions")
            .select("*")
            .eq("user_id", user_id)
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    @staticmethod
    def has_active_subscription(user_id: str) -> bool:
        subscription = LicenseService.get_latest_subscription(user_id)
        if not subscription or subscription.get("status") != "active":
            return False

        # A null period end is tolerated for webhook records that have not yet
        # been enriched; an explicit past end always denies access.
        period_end = subscription.get("current_period_end")
        if not period_end:
            return True
        try:
            return datetime.fromisoformat(period_end.replace("Z", "+00:00")) > datetime.now(timezone.utc)
        except (TypeError, ValueError):
            return False

    @staticmethod
    def check_and_consume_token(user_id: str) -> bool:
        response = supabase.table("user_profiles").select("*").eq("id", user_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="User profile not found.")
            
        profile = response.data[0]
        tokens_used = profile.get("tokens_used_today", 0)

        if LicenseService.has_active_subscription(user_id):
            return True  # Unlimited for active pros

        FREE_DAILY_LIMIT = 20
        if tokens_used >= FREE_DAILY_LIMIT:
            raise HTTPException(status_code=403, detail="Daily free limit reached. Upgrade to Pro!")

        supabase.table("user_profiles").update({
            "tokens_used_today": tokens_used + 1
        }).eq("id", user_id).execute()

        return True
