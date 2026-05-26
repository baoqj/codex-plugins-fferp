from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from scripts.common.config import ensure_runtime_dirs, get_settings
from scripts.common.ids import utc_now_iso


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    settings = ensure_runtime_dirs(get_settings())
    path = db_path or settings.database_path
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            task_type TEXT NOT NULL,
            status TEXT NOT NULL,
            priority INTEGER NOT NULL DEFAULT 5,
            source TEXT,
            source_file TEXT,
            payload_json TEXT NOT NULL,
            result_file TEXT,
            error_message TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            retry_count INTEGER NOT NULL DEFAULT 0,
            idempotency_key TEXT UNIQUE
        );

        CREATE TABLE IF NOT EXISTS approvals (
            approval_id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            action_type TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            draft_file TEXT,
            status TEXT NOT NULL,
            reviewer TEXT,
            reviewed_at TEXT,
            comment TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            FOREIGN KEY(task_id) REFERENCES tasks(task_id)
        );

        CREATE TABLE IF NOT EXISTS whatsapp_messages (
            message_id TEXT PRIMARY KEY,
            from_phone TEXT,
            customer_id TEXT,
            direction TEXT NOT NULL,
            message_type TEXT,
            text TEXT,
            raw_payload_file TEXT,
            intent TEXT,
            risk_level TEXT,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS action_logs (
            log_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            actor TEXT NOT NULL,
            skill TEXT,
            action TEXT NOT NULL,
            input_ref TEXT,
            output_ref TEXT,
            confidence REAL,
            requires_approval INTEGER NOT NULL DEFAULT 0,
            approval_id TEXT,
            payload_json TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_tasks_status_priority
            ON tasks(status, priority, created_at);

        CREATE INDEX IF NOT EXISTS idx_approvals_status
            ON approvals(status, created_at);
        """
    )
    conn.commit()


def encode_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def decode_json(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    return json.loads(value)


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


def touch_task(conn: sqlite3.Connection, task_id: str, status: str, **fields: Any) -> None:
    now = utc_now_iso()
    assignments = ["status = ?", "updated_at = ?"]
    values: list[Any] = [status, now]
    for key, value in fields.items():
        assignments.append(f"{key} = ?")
        values.append(value)
    values.append(task_id)
    conn.execute(f"UPDATE tasks SET {', '.join(assignments)} WHERE task_id = ?", values)
    conn.commit()
