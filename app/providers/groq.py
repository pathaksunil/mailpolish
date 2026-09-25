import asyncio
import logging
import re
import socket
import time as _time
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException, status

from app.core.config import Settings
from app.models.rewrite import SUPPORTED_GROQ_MODELS
from app.providers.base import RewriteProvider
from app.providers.prompts import build_rewrite_prompt

logger = logging.getLogger(__name__)

# Transient server-side failures worth retrying before giving up.
_RETRYABLE_STATUS_CODES = {502, 503, 504}
_MAX_RETRIES = 2
_RETRY_BACKOFF_SECONDS = 1.5


async def _async_sleep(seconds: float) -> None:
    await asyncio.sleep(seconds)




class GroqProvider(RewriteProvider):
    """Rewrite provider backed by GroqCloud's OpenAI-compatible Chat Completions API."""

    def __init__(self, settings: Settings):
        self.settings = settings

    async def rewrite(
        self, 
        *, 
        model: str, 
        mode: str, 
        text: str, 
        api_key: str, 
        max_words: int = 200,      # Accept max_words
        instructions: str = "",    # Accept instructions
        output_format: str = "plain_text",
    ) -> str:
        # Pass them into your prompt builder helper
        prompt = build_rewrite_prompt(
            mode, text, max_words=max_words, instructions=instructions,
            output_format=output_format,
        )
        url = f"{self.settings.groq_api_base_url.rstrip('/')}/chat/completions"
        host = urlparse(url).hostname or self.settings.groq_api_base_url
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a professional text rewriting assistant. Keep names, numbers, dates, links, and facts "
                        "unchanged. Adapt to the requested format based on the user's instructions. Do not refer to previous context"
                        "Return only the final rewritten text with no introductory or concluding commentary."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.35,
            "max_completion_tokens": min(2000, max(700, len(text) // 2 + 200)),
        }
        
        # Reasoning models (e.g. openai/gpt-oss-*) spend tokens on hidden
        # reasoning before answering; with a small token budget the final
        # content can come back empty. Keep reasoning minimal for them.
        if model.startswith("openai/gpt-oss"):
            payload["reasoning_effort"] = "low"

        dns_ok, dns_info = await self._check_dns(host)
        logger.info("GroqCloud call: model=%s url=%s dns=%s (%s)", model, url, "OK" if dns_ok else "FAIL", dns_info)
        # Full audit of what is sent to the LLM (prompt included).
        logger.info("GroqCloud request payload: model=%s payload=%s", model, payload)

        last_exc: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
                    response = await client.post(
                        url,
                        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                        json=payload
                    )
            except httpx.TimeoutException as exc:
                logger.error("GroqCloud timed out: model=%s url=%s dns_ok=%s cause=%r", model, url, dns_ok, exc.__cause__ or exc)
                raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="GroqCloud request timed out.") from exc
            except httpx.HTTPError as exc:
                cause = exc.__cause__ or exc
                logger.error(
                    "GroqCloud connection error: model=%s url=%s dns_ok=%s exc_type=%s cause=%r",
                    model, url, dns_ok, type(exc).__name__, cause,
                )
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=self._connection_detail(exc)) from exc

            # Full audit of the raw LLM response.
            logger.info("GroqCloud raw response: status=%s body=%s", response.status_code, response.text)

            # Retry transient server-side errors with backoff.
            if response.status_code in _RETRYABLE_STATUS_CODES and attempt < _MAX_RETRIES:
                wait = _RETRY_BACKOFF_SECONDS * attempt
                logger.warning("GroqCloud transient %s on attempt %s/%s — retrying in %ss", response.status_code, attempt, _MAX_RETRIES, wait)
                await _async_sleep(wait)
                last_exc = HTTPException(status_code=response.status_code, detail=self._error_detail(response))
                continue

            return self._handle_response(response)

        # Should not be reached, but defensive fallback.
        if last_exc:
            raise last_exc
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="GroqCloud request failed after retries.")

        if response.status_code in {401, 403}:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or unauthorized GroqCloud API key.")
        if response.status_code == 429:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="GroqCloud rate limit reached.")
        if response.status_code >= 400:
            detail = self._error_detail(response)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)

        return self._extract_text(response.json())

    async def _check_dns(self, host: str) -> tuple[bool, str]:
        """Resolve the host without blocking the event loop.

        DNS resolution runs in a thread executor so it never stalls the
        async event loop, even on slow or broken network configurations.
        """
        loop = asyncio.get_running_loop()
        try:
            t0 = _time.monotonic()
            infos = await loop.run_in_executor(None, socket.getaddrinfo, host, 443)
            dt_ms = int((_time.monotonic() - t0) * 1000)
            ips = sorted({info[4][0] for info in infos})
            return True, f"resolved {','.join(ips)} in {dt_ms}ms"
        except socket.gaierror as exc:
            return False, f"DNS FAILED ({exc.errno} {exc.strerror})"
        except Exception as exc:  # noqa: BLE001 - logging path should never raise
            return False, f"DNS check error: {type(exc).__name__}: {exc}"

    def _handle_response(self, response: httpx.Response) -> str:
        """Map an HTTP response to either the extracted rewrite or an HTTPException."""
        if response.status_code in {401, 403}:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or unauthorized GroqCloud API key.")
        if response.status_code == 429:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="GroqCloud rate limit reached.")
        if response.status_code >= 400:
            detail = self._error_detail(response)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)

        return self._extract_text(response.json())

    def _error_detail(self, response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return f"GroqCloud returned HTTP {response.status_code}."

        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict):
                error = error.get("message")
            if isinstance(error, str):
                return f"GroqCloud error: {error}"
        return f"GroqCloud returned HTTP {response.status_code}."


    def _connection_detail(self, exc: httpx.HTTPError) -> str:
        # httpx wraps the real cause (DNS / connect / SSL / proxy) in the
        # exception or its __cause__, so surface it instead of a vague message.
        cause = getattr(exc, "__cause__", None) or exc
        exc_type = type(exc).__name__
        msg = str(cause)
        hint = ""
        low = msg.lower()
        if "getaddrinfo" in low or "11001" in msg or "name or service" in low or "nodename" in low:
            hint = " This looks like a DNS/network block on api.groq.com. Check internet/DNS/filter, or run the diagnose script: python -m scripts.hf_diagnose."
        elif "timed out" in low or "timedout" in low or "timeout" in low:
            hint = " Connection to GroqCloud timed out - check firewall/VPN."
        return f"Could not reach GroqCloud ({exc_type}). {msg}.{hint}"

    def _extract_text(self, payload: object) -> str:
        if isinstance(payload, dict):
            choices = payload.get("choices")
            if isinstance(choices, list) and choices:
                first = choices[0]
                if isinstance(first, dict):
                    message = first.get("message")
                    if isinstance(message, dict):
                        content = message.get("content")
                        if isinstance(content, str) and content.strip():
                            return self._clean_output(content)
                        # Reasoning models may put text in "reasoning" when
                        # the completion budget is exhausted before content.
                        reasoning = message.get("reasoning")
                        if isinstance(reasoning, str) and reasoning.strip():
                            return self._clean_output(reasoning)
                    if isinstance(first.get("text"), str):
                        return self._clean_output(first["text"])
            if isinstance(payload.get("error"), (str, dict)):
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="GroqCloud model error.")

        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Unexpected GroqCloud response format.")

    def _clean_output(self, text: str) -> str:
        cleaned = text.strip()
        # Strip reasoning-model wrappers if any leaked into the text.
        cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.DOTALL).strip()
        cleaned = re.sub(r"^(rewritten email text|rewrite|output)\s*:\s*", "", cleaned, flags=re.IGNORECASE).strip()
        if not cleaned:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Model returned an empty rewrite.")
        return cleaned
