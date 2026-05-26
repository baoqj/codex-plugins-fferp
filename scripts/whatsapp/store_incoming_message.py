from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.common.config import ensure_runtime_dirs, get_settings
from scripts.common.ids import new_id
from scripts.common.logging import append_jsonl


def store_raw_webhook_payload(payload: dict[str, Any]) -> Path:
    settings = ensure_runtime_dirs(get_settings())
    raw_dir = settings.data_dir / "inbox" / "whatsapp"
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / f"{new_id('WA')}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    append_jsonl(
        "whatsapp_log.jsonl",
        {
            "actor": "fferp-api",
            "action": "raw_webhook_received",
            "raw_payload_file": str(path),
            "entry_count": len(payload.get("entry", [])),
        },
    )
    return path


def log_normalized_message(message: dict[str, Any], raw_payload_file: str | None) -> None:
    append_jsonl(
        "whatsapp_log.jsonl",
        {
            "actor": "fferp-api",
            "action": "message_normalized",
            "message_id": message.get("message_id"),
            "from_phone": message.get("from_phone"),
            "message_type": message.get("message_type"),
            "raw_payload_file": raw_payload_file,
        },
    )
