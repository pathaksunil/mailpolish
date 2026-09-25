from typing import Literal
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.dependencies import require_authenticated_user
from app.services.quota_service import QuotaService

router = APIRouter(prefix="/v1/generations", tags=["quota"])

class ReserveRequest(BaseModel):
    provider: Literal["groq", "ollama"]
    model: str = Field(min_length=1, max_length=160)
    estimated_tokens: int = Field(gt=0, le=50_000)

class CompleteRequest(BaseModel):
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    success: bool = True

@router.post("/reserve")
def reserve(request: ReserveRequest, user_id: str = Depends(require_authenticated_user)) -> dict:
    return {"usage_id": QuotaService.reserve(user_id, request.provider, request.model, request.estimated_tokens)}

@router.post("/{usage_id}/complete")
def complete(usage_id: str, request: CompleteRequest, user_id: str = Depends(require_authenticated_user)) -> dict:
    QuotaService.complete(user_id, usage_id, request.prompt_tokens, request.completion_tokens, request.success)
    return {"ok": True}
