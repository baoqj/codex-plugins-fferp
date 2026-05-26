from __future__ import annotations

import hmac

from fastapi import Header, HTTPException

from scripts.common.config import get_settings


def require_api_token(authorization: str | None = Header(default=None)) -> None:
    """Protect public SaaS admin and MCP endpoints when FFERP_API_TOKEN is configured."""
    token = get_settings().api_token
    if not token:
        return
    expected = f"Bearer {token}"
    if not authorization or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing API token.")
