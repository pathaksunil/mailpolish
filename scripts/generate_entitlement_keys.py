"""Generate an Ed25519 entitlement key pair for deployment configuration.

Keep the private value in AWS Secrets Manager as ENTITLEMENT_PRIVATE_KEY_B64.
Embed the public value in the desktop installer as
MAILPOLISH_ENTITLEMENT_PUBLIC_KEY_B64.
"""

import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

private_key = Ed25519PrivateKey.generate()
private_bytes = private_key.private_bytes(
    encoding=serialization.Encoding.Raw,
    format=serialization.PrivateFormat.Raw,
    encryption_algorithm=serialization.NoEncryption(),
)
public_bytes = private_key.public_key().public_bytes(
    encoding=serialization.Encoding.Raw,
    format=serialization.PublicFormat.Raw,
)

print("ENTITLEMENT_PRIVATE_KEY_B64=" + base64.urlsafe_b64encode(private_bytes).decode("ascii"))
print("MAILPOLISH_ENTITLEMENT_PUBLIC_KEY_B64=" + base64.urlsafe_b64encode(public_bytes).decode("ascii"))
