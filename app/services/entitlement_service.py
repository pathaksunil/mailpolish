"""Issue short-lived Ed25519-signed feature entitlements."""

import base64
from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.core.config import get_settings


ENTITLEMENT_TTL_DAYS = 7


def issue_local_presentation_entitlement(user_id: str) -> dict[str, str | list[str]]:
    settings = get_settings()
    encoded_key = settings.entitlement_private_key_b64.get_secret_value()
    if not encoded_key:
        raise RuntimeError("ENTITLEMENT_PRIVATE_KEY_B64 is not configured.")

    private_key = Ed25519PrivateKey.from_private_bytes(base64.b64decode(encoded_key))
    expires_at = datetime.now(timezone.utc) + timedelta(days=ENTITLEMENT_TTL_DAYS)
    payload = {
        "version": 1,
        "user_id": user_id,
        "features": ["local_presentation_generation"],
        "expires_at": expires_at.isoformat(),
    }
    # Canonical JSON is essential: client verification signs these exact bytes.
    import json
    payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    signature = private_key.sign(payload_bytes)
    return {
        "payload": base64.urlsafe_b64encode(payload_bytes).decode("ascii"),
        "signature": base64.urlsafe_b64encode(signature).decode("ascii"),
    }
