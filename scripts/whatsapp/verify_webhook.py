from __future__ import annotations

from scripts.common.config import get_settings


def verify_subscription(mode: str | None, token: str | None, challenge: str | None) -> str | None:
    settings = get_settings()
    if mode == "subscribe" and token and token == settings.whatsapp_verify_token:
        return challenge or ""
    return None
