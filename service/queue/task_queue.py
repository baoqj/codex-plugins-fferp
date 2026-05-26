from __future__ import annotations

import sqlite3
from typing import Any

from scripts.common.db import decode_json, encode_json, is_integrity_error, is_postgres_connection, row_to_dict, touch_task
from scripts.common.ids import new_id, utc_now_iso


PENDING = "pending"
PROCESSING = "processing"
WAITING_APPROVAL = "waiting_approval"
APPROVED = "approved"
REJECTED = "rejected"
COMPLETED = "completed"
FAILED = "failed"
CANCELLED = "cancelled"


def create_task(
    conn: sqlite3.Connection,
    task_type: str,
    payload: dict[str, Any],
    *,
    source: str | None = None,
    source_file: str | None = None,
    priority: int = 5,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    now = utc_now_iso()
    task_id = new_id("TASK")
    try:
        conn.execute(
            """
            INSERT INTO tasks (
                task_id, task_type, status, priority, source, source_file, payload_json,
                created_at, updated_at, idempotency_key
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                task_type,
                PENDING,
                priority,
                source,
                source_file,
                encode_json(payload),
                now,
                now,
                idempotency_key,
            ),
        )
        conn.commit()
    except Exception as exc:
        if not is_integrity_error(exc):
            raise
        conn.rollback()
        row = conn.execute("SELECT * FROM tasks WHERE idempotency_key = ?", (idempotency_key,)).fetchone()
        existing = row_to_dict(row)
        if existing is None:
            raise
        existing["payload"] = decode_json(existing.pop("payload_json"))
        return existing

    return {
        "task_id": task_id,
        "task_type": task_type,
        "status": PENDING,
        "priority": priority,
        "source": source,
        "source_file": source_file,
        "payload": payload,
        "idempotency_key": idempotency_key,
    }


def claim_next_task(conn: sqlite3.Connection) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT * FROM tasks
        WHERE status = ?
        ORDER BY priority ASC, created_at ASC
        LIMIT 1
        """,
        (PENDING,),
    ).fetchone()
    if row is None:
        return None
    task = row_to_dict(row)
    assert task is not None
    touch_task(conn, task["task_id"], PROCESSING)
    task["status"] = PROCESSING
    task["payload"] = decode_json(task.pop("payload_json"))
    return task


def mark_waiting_approval(conn: sqlite3.Connection, task_id: str, result_file: str | None) -> None:
    touch_task(conn, task_id, WAITING_APPROVAL, result_file=result_file)


def complete_task(conn: sqlite3.Connection, task_id: str, result_file: str | None = None) -> None:
    touch_task(conn, task_id, COMPLETED, result_file=result_file)


def fail_task(conn: sqlite3.Connection, task_id: str, error_message: str) -> None:
    row = conn.execute("SELECT retry_count FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
    retry_count = int(row["retry_count"] if row else 0) + 1
    touch_task(conn, task_id, FAILED, error_message=error_message, retry_count=retry_count)


def list_tasks(conn: sqlite3.Connection, status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    if status:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC LIMIT ?",
            (status, limit),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    tasks = []
    for row in rows:
        item = row_to_dict(row)
        assert item is not None
        item["payload"] = decode_json(item.pop("payload_json"))
        tasks.append(item)
    return tasks


def upsert_whatsapp_message(
    conn: sqlite3.Connection,
    message: dict[str, Any],
    *,
    raw_payload_file: str | None,
    status: str = "received",
) -> bool:
    now = utc_now_iso()
    if is_postgres_connection(conn):
        insert_sql = """
        INSERT INTO whatsapp_messages (
            message_id, from_phone, customer_id, direction, message_type, text,
            raw_payload_file, status, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (message_id) DO NOTHING
        """
    else:
        insert_sql = """
        INSERT OR IGNORE INTO whatsapp_messages (
            message_id, from_phone, customer_id, direction, message_type, text,
            raw_payload_file, status, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
    cursor = conn.execute(
        insert_sql,
        (
            message["message_id"],
            message.get("from_phone"),
            message.get("customer_id"),
            "inbound",
            message.get("message_type"),
            message.get("text"),
            raw_payload_file,
            status,
            now,
            now,
        ),
    )
    conn.commit()
    return cursor.rowcount > 0


def update_whatsapp_processing_state(
    conn: sqlite3.Connection,
    message_id: str,
    *,
    intent: str,
    risk_level: str,
    status: str,
) -> None:
    now = utc_now_iso()
    conn.execute(
        """
        UPDATE whatsapp_messages
        SET intent = ?, risk_level = ?, status = ?, updated_at = ?
        WHERE message_id = ?
        """,
        (intent, risk_level, status, now, message_id),
    )
    conn.commit()
