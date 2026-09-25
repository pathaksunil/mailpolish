"""
Diagnose why the MailPolish API cannot reach GroqCloud.

Runs:
  1. DNS resolution for api.groq.com
  2. A real POST to the Groq Chat Completions API
  3. Optionally checks the local MailPolish API

Usage:

    python hf_diagnose.py

    python hf_diagnose.py --model llama-3.3-70b-versatile

    python hf_diagnose.py --api-key gsk_xxx

    python hf_diagnose.py --model llama-3.3-70b-versatile --api-key gsk_xxx

    python hf_diagnose.py --api http://localhost:8000

Environment variables:

    GROQ_API_KEY
    GROQ_MODEL
    GROQ_API_BASE_URL

Exit codes:
    0 = OK
    1 = diagnosed failure
    2 = not runnable
"""

from __future__ import annotations

import argparse
import os
import socket
import sys
import time
from urllib.parse import urlparse

import httpx


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_BASE = "https://api.groq.com/openai/v1"

# Use a Groq model ID here, NOT a Hugging Face model ID.
#DEFAULT_MODEL = "llama-3.3-70b-versatile"
DEFAULT_MODEL = "openai/gpt-oss-20b"

DEFAULT_TIMEOUT = 45.0

TEST_INPUT = (
    "Rewrite this email to be short and polite: "
    "Hello, can you please send me the report."
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _secs(dt: float) -> str:
    return f"{dt:.2f}s"


def print_separator() -> None:
    print("-" * 70)


# ---------------------------------------------------------------------------
# DNS check
# ---------------------------------------------------------------------------

def check_dns(host: str) -> None:
    print(f"[1/3] Resolving DNS for {host} ...")

    if not host:
        print("  DNS FAILED: hostname is empty.")
        raise SystemExit(2)

    try:
        t0 = time.monotonic()

        infos = socket.getaddrinfo(
            host,
            443,
            type=socket.SOCK_STREAM,
        )

        elapsed = _secs(time.monotonic() - t0)

        addresses = []

        for info in infos:
            try:
                address = info[4][0]
                if address not in addresses:
                    addresses.append(address)
            except (IndexError, TypeError):
                pass

        print(
            f"  DNS OK ({elapsed})"
        )

        if addresses:
            print(
                "  Addresses: "
                + ", ".join(addresses[:10])
            )

    except socket.gaierror as exc:
        print(f"  DNS FAILED: {exc}")
        print()
        print("  This machine cannot resolve the GroqCloud host.")
        print()
        print("  Possible causes:")
        print("    - DNS problem")
        print("    - Firewall")
        print("    - VPN")
        print("    - Proxy")
        print("    - Corporate/network filtering")
        print()
        print("  Try:")
        print("    nslookup api.groq.com")
        print("    ping api.groq.com")

        raise SystemExit(1)

    except OSError as exc:
        print(f"  DNS ERROR: {exc}")
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# Groq request
# ---------------------------------------------------------------------------

def run_groq_request(
    model: str,
    api_key: str,
    base: str,
    timeout: float,
) -> int:

    url = f"{base.rstrip('/')}/chat/completions"

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": TEST_INPUT,
            }
        ],
        "temperature": 0.35,
        "max_completion_tokens": 64,
    }

    headers = {
        "Content-Type": "application/json",
    }

    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    print_separator()
    print("[2/3] Testing GroqCloud API")
    print_separator()

    print(f"  Base URL : {base}")
    print(f"  Endpoint : {url}")
    print(f"  Model    : {model}")
    print(
        "  API key  : "
        + ("<set>" if api_key else "<missing>")
    )
    print(f"  Timeout  : {timeout}s")
    print()

    if not api_key:
        print("  ERROR: GROQ_API_KEY is not set.")
        print()
        print("  Set it in Windows CMD with:")
        print()
        print('    set GROQ_API_KEY=gsk_xxxxxxxxx')
        print()
        print("  Or pass:")
        print()
        print("    --api-key gsk_xxxxxxxxx")
        return 2

    t0 = time.monotonic()

    try:
        print("  Sending POST request...")

        with httpx.Client(
            timeout=timeout,
            follow_redirects=True,
        ) as client:

            resp = client.post(
                url,
                headers=headers,
                json=payload,
            )

    except httpx.ConnectError as exc:
        elapsed = _secs(time.monotonic() - t0)

        print()
        print(f"  CONNECT FAILED after {elapsed}")
        print(f"  Error: {exc}")

        if exc.__cause__:
            print(f"  Cause: {exc.__cause__}")

        print()
        print("  GroqCloud could not be reached.")
        print("  Check firewall, VPN, proxy, or outbound HTTPS access.")

        return 1

    except httpx.ConnectTimeout as exc:
        elapsed = _secs(time.monotonic() - t0)

        print()
        print(f"  CONNECTION TIMEOUT after {elapsed}")
        print(f"  Error: {exc}")

        return 1

    except httpx.ReadTimeout as exc:
        elapsed = _secs(time.monotonic() - t0)

        print()
        print(f"  RESPONSE TIMEOUT after {elapsed}")
        print(f"  Error: {exc}")

        print()
        print(
            "  The request reached GroqCloud, but no response "
            "arrived within the timeout."
        )

        return 1

    except httpx.TimeoutException as exc:
        elapsed = _secs(time.monotonic() - t0)

        print()
        print(f"  TIMEOUT after {elapsed}")
        print(f"  Error: {exc}")

        return 1

    except httpx.HTTPError as exc:
        elapsed = _secs(time.monotonic() - t0)

        print()
        print(f"  HTTP CLIENT ERROR after {elapsed}")
        print(f"  Type: {type(exc).__name__}")
        print(f"  Error: {exc}")

        if exc.__cause__:
            print(f"  Cause: {exc.__cause__}")

        return 1

    except Exception as exc:
        elapsed = _secs(time.monotonic() - t0)

        print()
        print(f"  UNEXPECTED ERROR after {elapsed}")
        print(f"  Type: {type(exc).__name__}")
        print(f"  Error: {exc}")

        return 1

    elapsed = _secs(time.monotonic() - t0)

    print()
    print(f"  HTTP status: {resp.status_code}")
    print(f"  Response time: {elapsed}")

    # -----------------------------------------------------------------------
    # Success
    # -----------------------------------------------------------------------

    if resp.status_code == 200:

        print()
        print("  SUCCESS")
        print("  GroqCloud is reachable and the model responded.")
        print()

        try:
            body = resp.json()

            choices = body.get("choices", [])

            if choices:
                message = choices[0].get("message", {})
                content = message.get("content", "")

                print("  Model response:")
                print()
                print(
                    "    "
                    + (content or "<empty response>")[:500]
                )

            usage = body.get("usage")

            if usage:
                print()
                print("  Usage:")
                print(f"    {usage}")

        except ValueError:
            print("  Response was not valid JSON:")
            print(resp.text[:1000])

        return 0

    # -----------------------------------------------------------------------
    # Authentication
    # -----------------------------------------------------------------------

    if resp.status_code == 401:

        print()
        print("  AUTHENTICATION ERROR (401)")
        print()
        print("  GroqCloud rejected the API key.")
        print()
        print("  Possible causes:")
        print("    - Invalid API key")
        print("    - Revoked API key")
        print("    - Wrong environment variable")
        print("    - Extra spaces/quotes in the key")
        print()
        print("  Response body:")
        print(resp.text[:2000])

        return 1

    # -----------------------------------------------------------------------
    # Forbidden
    # -----------------------------------------------------------------------

    if resp.status_code == 403:

        print()
        print("  FORBIDDEN (403)")
        print()
        print("  GroqCloud received the request but rejected it.")
        print()
        print("  Response body:")
        print(resp.text[:2000])

        return 1

    # -----------------------------------------------------------------------
    # Not found
    # -----------------------------------------------------------------------

    if resp.status_code == 404:

        print()
        print("  NOT FOUND (404)")
        print()
        print("  The request reached GroqCloud.")
        print("  This is NOT a DNS/connectivity problem.")
        print()
        print("  Most likely causes:")
        print("    - Incorrect API endpoint")
        print("    - Invalid/unsupported model ID")
        print("    - Incorrect GROQ_API_BASE_URL")
        print()
        print(f"  Base URL : {base}")
        print(f"  Endpoint : {url}")
        print(f"  Model    : {model}")
        print()
        print("  ACTUAL GROQ RESPONSE:")
        print_separator()
        print(resp.text[:4000])
        print_separator()

        return 1

    # -----------------------------------------------------------------------
    # Rate limit
    # -----------------------------------------------------------------------

    if resp.status_code == 429:

        print()
        print("  RATE LIMITED (429)")
        print()
        print("  GroqCloud rejected the request because a rate/quota limit")
        print("  was exceeded.")
        print()
        print("  ACTUAL GROQ RESPONSE:")
        print_separator()
        print(resp.text[:4000])
        print_separator()

        retry_after = resp.headers.get("retry-after")

        if retry_after:
            print()
            print(f"  Retry-After: {retry_after}")

        return 1

    # -----------------------------------------------------------------------
    # Bad request
    # -----------------------------------------------------------------------

    if resp.status_code == 400:

        print()
        print("  BAD REQUEST (400)")
        print()
        print("  GroqCloud received the request but rejected its contents.")
        print()
        print("  This can indicate:")
        print("    - Invalid model ID")
        print("    - Invalid request parameter")
        print("    - Unsupported parameter")
        print("    - Invalid message format")
        print()
        print("  ACTUAL GROQ RESPONSE:")
        print_separator()
        print(resp.text[:4000])
        print_separator()

        return 1

    # -----------------------------------------------------------------------
    # Model unavailable / server errors
    # -----------------------------------------------------------------------

    if resp.status_code >= 500:

        print()
        print(f"  GROQ SERVER ERROR ({resp.status_code})")
        print()
        print("  GroqCloud returned a server-side error.")
        print()
        print("  ACTUAL GROQ RESPONSE:")
        print_separator()
        print(resp.text[:4000])
        print_separator()

        return 1

    # -----------------------------------------------------------------------
    # Everything else
    # -----------------------------------------------------------------------

    print()
    print(f"  UNEXPECTED HTTP STATUS: {resp.status_code}")
    print()
    print("  ACTUAL RESPONSE:")
    print_separator()
    print(resp.text[:4000])
    print_separator()

    return 1


# ---------------------------------------------------------------------------
# Local MailPolish API
# ---------------------------------------------------------------------------

def check_local_api(
    base: str,
    timeout: float,
) -> int:

    print_separator()
    print("[3/3] Checking local MailPolish API")
    print_separator()

    health_url = f"{base.rstrip('/')}/health"

    print(f"  URL: {health_url}")
    print()

    try:

        with httpx.Client(
            timeout=timeout,
        ) as client:

            resp = client.get(health_url)

        print(f"  HTTP {resp.status_code}")
        print(f"  Response: {resp.text[:1000]}")

        if resp.status_code < 400:
            print()
            print("  LOCAL API OK")
            return 0

        print()
        print("  LOCAL API FAILED")

        return 1

    except httpx.ConnectError as exc:

        print()
        print("  Could not connect to local API.")
        print(f"  Error: {exc}")
        print()
        print(
            "  Is FastAPI running?"
        )
        print()
        print(
            "    uvicorn app.main:app "
            "--host 127.0.0.1 --port 8000"
        )

        return 1

    except httpx.TimeoutException as exc:

        print()
        print("  Local API request timed out.")
        print(f"  Error: {exc}")

        return 1

    except httpx.HTTPError as exc:

        print()
        print("  Local API HTTP error.")
        print(f"  Error: {exc}")

        return 1


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:

    parser = argparse.ArgumentParser(
        description=(
            "Diagnose GroqCloud connectivity for MailPolish."
        )
    )

    parser.add_argument(
        "--model",
        default=os.environ.get(
            "GROQ_MODEL",
            DEFAULT_MODEL,
        ),
        help=(
            "Groq model ID "
            "(default: llama-3.3-70b-versatile)"
        ),
    )

    parser.add_argument(
        "--base",
        default=os.environ.get(
            "GROQ_API_BASE_URL",
            DEFAULT_BASE,
        ),
        help=(
            "Groq API base URL "
            "(default: https://api.groq.com/openai/v1)"
        ),
    )

    parser.add_argument(
        "--api-key",
        dest="api_key",
        default=os.environ.get(
            "GROQ_API_KEY",
            "",
        ),
        help=(
            "Groq API key. "
            "Defaults to GROQ_API_KEY environment variable."
        ),
    )

    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help="HTTP timeout in seconds.",
    )

    parser.add_argument(
        "--api",
        default="",
        help=(
            "Optional local MailPolish API base, "
            "for example http://localhost:8000"
        ),
    )

    args = parser.parse_args(argv)

    # -----------------------------------------------------------------------
    # Validate base URL
    # -----------------------------------------------------------------------

    try:

        parsed = urlparse(args.base)

        host = parsed.hostname or ""

        if parsed.scheme not in ("http", "https"):
            print(
                f"Invalid API base URL scheme: {parsed.scheme}"
            )
            return 2

        if not host:
            print(
                f"Invalid API base URL: {args.base}"
            )
            return 2

    except Exception as exc:

        print(
            f"Could not parse API base URL: {exc}"
        )
        return 2

    # -----------------------------------------------------------------------
    # Run diagnostics
    # -----------------------------------------------------------------------

    print()
    print("=" * 70)
    print("MAILPOLISH / GROQCLOUD DIAGNOSTIC")
    print("=" * 70)
    print()

    check_dns(host)

    result = run_groq_request(
        model=args.model,
        api_key=args.api_key,
        base=args.base,
        timeout=args.timeout,
    )

    if args.api:

        local_result = check_local_api(
            base=args.api,
            timeout=args.timeout,
        )

        result = max(
            result,
            local_result,
        )

    # -----------------------------------------------------------------------
    # Final diagnosis
    # -----------------------------------------------------------------------

    print()
    print("=" * 70)

    if result == 0:
        print("DIAGNOSIS: OK")
        print("GroqCloud is reachable and the request succeeded.")
    elif result == 2:
        print("DIAGNOSIS: NOT RUNNABLE")
        print("Fix the configuration above and run again.")
    else:
        print("DIAGNOSIS: FAILED")
        print("See the detailed error above.")

    print("=" * 70)
    print()

    return result


if __name__ == "__main__":
    raise SystemExit(main())