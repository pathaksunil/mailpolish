# MailPolish API service

Deploy this folder separately from the Windows desktop application. It exposes
the rewrite, quota, billing, and local-presentation entitlement endpoints.

## Local or server startup

```powershell
cd server
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

For production, run the same ASGI app behind HTTPS (for example, behind a
reverse proxy) and set the desktop application's `mp_backend_api_url` to its
public HTTPS URL.

## Fixing local Ollama presentation entitlement

The local presentation feature uses an Ed25519 key pair. The server signs a
short-lived entitlement; the desktop app verifies it with the corresponding
public key. Both values must originate from the **same** generated key pair.

1. On a secure administrator machine, run:

   ```powershell
   cd server
   python scripts/generate_entitlement_keys.py
   ```

2. Put `ENTITLEMENT_PRIVATE_KEY_B64` in the API server's secret store or its
   deployment environment. Do not commit it or ship it with the desktop app.

3. Before desktop packaging, copy
   `mailpolish_desktop/assets/entitlement_public_key.txt.example` to
   `mailpolish_desktop/assets/entitlement_public_key.txt`, replace its
   placeholder with the printed public value, and include that asset in the
   installer. The public value is safe to embed. Developers may instead set
   `MAILPOLISH_ENTITLEMENT_PUBLIC_KEY_B64` as an environment override.

4. Restart/redeploy both components, sign in with an account that has the Pro
   local-presentation entitlement, and retry.

The error `Local entitlement verification is not configured` means step 3 is
missing. The server will return `Local entitlement service is not configured`
when step 2 is missing.

## Deployment boundary

- Keep all API keys, Supabase credentials, and
  `ENTITLEMENT_PRIVATE_KEY_B64` on the server.
- Keep PowerPoint rendering and optional local Ollama inference in
  `mailpolish_desktop/`; they run on the user's Windows machine.
- The API server does not need Microsoft PowerPoint installed.
