from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def parse_webhook_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract normalized inbound messages from a WhatsApp Cloud API webhook payload."""
    messages: list[dict[str, Any]] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            contacts_by_wa_id = {
                contact.get("wa_id"): contact
                for contact in value.get("contacts", [])
                if contact.get("wa_id")
            }
            for message in value.get("messages", []):
                message_id = message.get("id")
                if not message_id:
                    continue
                from_phone = message.get("from")
                message_type = message.get("type", "unknown")
                text = _extract_text(message, message_type)
                timestamp = _normalize_timestamp(message.get("timestamp"))
                media_id = _extract_media_id(message, message_type)
                contact = contacts_by_wa_id.get(from_phone, {})
                messages.append(
                    {
                        "message_id": message_id,
                        "from_phone": from_phone,
                        "timestamp": timestamp,
                        "message_type": message_type,
                        "text": text,
                        "media_id": media_id,
                        "customer_profile_name": contact.get("profile", {}).get("name"),
                        "raw_message": message,
                    }
                )
    return messages


def _extract_text(message: dict[str, Any], message_type: str) -> str | None:
    if message_type == "text":
        return message.get("text", {}).get("body")
    if message_type == "button":
        return message.get("button", {}).get("text")
    if message_type == "interactive":
        interactive = message.get("interactive", {})
        if interactive.get("type") == "button_reply":
            return interactive.get("button_reply", {}).get("title")
        if interactive.get("type") == "list_reply":
            return interactive.get("list_reply", {}).get("title")
    return message.get(message_type, {}).get("caption")


def _extract_media_id(message: dict[str, Any], message_type: str) -> str | None:
    if message_type in {"image", "audio", "video", "document", "sticker"}:
        return message.get(message_type, {}).get("id")
    return None


def _normalize_timestamp(value: str | int | None) -> str | None:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(int(value), timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return str(value)
