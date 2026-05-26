from __future__ import annotations

import sqlite3
from typing import Any

from service.queue.task_queue import create_task, upsert_whatsapp_message


def generate_reply_task(
    conn: sqlite3.Connection,
    message: dict[str, Any],
    *,
    raw_payload_file: str | None,
) -> dict[str, Any] | None:
    inserted = upsert_whatsapp_message(conn, message, raw_payload_file=raw_payload_file)
    if not inserted:
        return None
    return create_task(
        conn,
        "process_whatsapp_message",
        {
            "message": message,
            "raw_payload_file": raw_payload_file,
        },
        source="whatsapp",
        source_file=raw_payload_file,
        priority=3,
        idempotency_key=f"whatsapp:{message['message_id']}",
    )
