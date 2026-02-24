"""Create or update the Langfuse LLM connection to point at LiteLLM (infrastructure as code).

Run after deploy or when the proxy URL changes. Requires LANGFUSE_PUBLIC_KEY,
LANGFUSE_SECRET_KEY, LANGFUSE_BASE_URL. When LITELLM_PROXY_URL is set, upserts
an LLM connection so the Langfuse Playground and LLM-as-a-Judge use the same
gateway. When unset, exits successfully without making changes.

Usage:
    uv run python scripts/infra/setup_langfuse_llm_connection.py
    # Or with .env loaded:
    uv run python -c "from dotenv import load_dotenv; load_dotenv(); exec(open('scripts/infra/setup_langfuse_llm_connection.py').read())"
"""

from __future__ import annotations

import base64
import json
import os
import sys
import urllib.error
import urllib.request


def _main() -> int:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    base_url = (os.getenv("LANGFUSE_BASE_URL") or "").rstrip("/")
    proxy_url = (os.getenv("LITELLM_PROXY_URL") or "").strip()
    secret = os.getenv("LITELLM_MASTER_KEY") or os.getenv("ANTHROPIC_API_KEY")
    models_str = os.getenv("LANGFUSE_LLM_CONNECTION_MODELS", "claude-sonnet-4-6")

    if not proxy_url:
        print("LITELLM_PROXY_URL not set; skipping Langfuse LLM connection setup.")
        return 0

    if not all([public_key, secret_key, base_url]):
        print(
            "Missing LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, or LANGFUSE_BASE_URL.",
            file=sys.stderr,
        )
        return 1

    connection_base = proxy_url.rstrip("/")
    if not connection_base.endswith("/v1"):
        connection_base = f"{connection_base}/v1"

    custom_models = [m.strip() for m in models_str.split(",") if m.strip()]
    if not custom_models:
        custom_models = ["claude-sonnet-4-6"]

    body = {
        "provider": "litellm",
        "adapter": "openai",
        "secretKey": secret or "",
        "baseURL": connection_base,
        "customModels": custom_models,
        "withDefaultModels": False,
    }

    url = f"{base_url}/api/public/llm-connections"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="PUT",
        headers={"Content-Type": "application/json"},
    )
    credentials = base64.b64encode(f"{public_key}:{secret_key}".encode()).decode()
    req.add_header("Authorization", f"Basic {credentials}")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status not in (200, 201):
                print(f"Unexpected status {resp.status}", file=sys.stderr)
                return 1
            print("Langfuse LLM connection upserted successfully (litellm).")
            return 0
    except urllib.error.HTTPError as e:
        print(f"HTTP error {e.code}: {e.reason}", file=sys.stderr)
        if e.fp:
            try:
                body_read = e.fp.read().decode()
                print(body_read, file=sys.stderr)
            except Exception:
                pass
        return 1
    except OSError as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(_main())
