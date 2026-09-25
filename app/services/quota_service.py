from fastapi import HTTPException, status

from app.core.database import supabase


class QuotaService:
    @staticmethod
    def reserve(user_id: str, provider: str, model: str, estimated_tokens: int) -> str:
        try:
            response = supabase.rpc("reserve_generation_quota", {
                "p_user_id": user_id, "p_provider": provider,
                "p_model": model, "p_reserved_tokens": estimated_tokens,
            }).execute()
            return response.data[0]["usage_id"]
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    @staticmethod
    def complete(user_id: str, usage_id: str, prompt_tokens: int, completion_tokens: int, success: bool) -> None:
        supabase.rpc("complete_generation_quota", {
            "p_usage_id": usage_id, "p_user_id": user_id,
            "p_prompt_tokens": prompt_tokens, "p_completion_tokens": completion_tokens,
            "p_status": "succeeded" if success else "failed",
        }).execute()
