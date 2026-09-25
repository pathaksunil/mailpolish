import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from app.core.config import Settings, get_settings
from app.core.dependencies import require_cloud_entitlement
from app.models.rewrite import RewriteRequest, RewriteResponse
from app.providers.factory import get_provider
from app.security.scrub import reveal_secret

router = APIRouter(prefix="/v1", tags=["rewrite"])
logger = logging.getLogger(__name__)


@router.post("/rewrite", response_model=RewriteResponse)
async def rewrite_email(
    request: RewriteRequest,
    settings: Settings = Depends(get_settings),
    user_id: str = Depends(require_cloud_entitlement),
) -> RewriteResponse:
    # Defense-in-depth: cap input length even though Pydantic validates it.
    # This guards against future model changes or direct API callers.
    if len(request.text) > settings.max_input_chars:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": f"Text exceeds maximum length of {settings.max_input_chars} characters."},
        )

    # Resolve the server-side Groq key. The API owns this; clients never see it.
    api_key = reveal_secret(settings.groq_api_key)
    if not api_key or api_key == "gsk_replace_with_your_real_key":
        logger.error("GROQ_API_KEY is not configured on the server.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MailPolish API is not configured with a Groq API key. Set GROQ_API_KEY in the API's .env file.",
        )

    logger.info("Rewrite request: user_id=%s provider=%s model=%s mode=%s text_len=%d", user_id, request.provider, request.model, request.mode, len(request.text))
    provider = get_provider(request.provider, settings)

    # Call the provider, passing all parameters correctly from 'request'
    rewritten = await provider.rewrite(
        model=request.model,
        mode=request.mode,
        text=request.text,
        api_key=api_key,
        max_words=request.max_words,
        instructions=request.instructions,
        output_format=request.output_format,
    )

    return RewriteResponse(rewrittenText=rewritten, provider=request.provider, model=request.model)
