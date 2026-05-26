from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from scripts.common.config import ensure_runtime_dirs, get_settings
from scripts.common.ids import utc_now_iso


class PostgresConnection:
    backend = "postgres"

    def __init__(self, raw_conn: Any):
        self._raw_conn = raw_conn

    def execute(self, sql: str, params: Iterable[Any] | None = None) -> Any:
        return self._raw_conn.execute(_postgres_sql(sql), tuple(params or ()))

    def executescript(self, script: str) -> None:
        for statement in _split_sql_script(script):
            self.execute(statement)

    def commit(self) -> None:
        self._raw_conn.commit()

    def rollback(self) -> None:
        self._raw_conn.rollback()

    def close(self) -> None:
        self._raw_conn.close()

    def __enter__(self) -> "PostgresConnection":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        self.close()


Connection = sqlite3.Connection | PostgresConnection


def connect(db_path: Path | None = None) -> Connection:
    settings = ensure_runtime_dirs(get_settings())
    if settings.database_url and (db_path is None or db_path == settings.database_path):
        conn = _connect_postgres(settings.database_url)
        init_db(conn)
        return conn

    path = db_path or settings.database_path
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


def _connect_postgres(database_url: str) -> PostgresConnection:
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:  # pragma: no cover - only hit in Postgres deployments
        raise RuntimeError("DATABASE_URL is set, but psycopg is not installed.") from exc

    return PostgresConnection(psycopg.connect(database_url, row_factory=dict_row))


def init_db(conn: Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS tenants (
            tenant_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            plan TEXT NOT NULL DEFAULT 'starter',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            display_name TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS tenant_memberships (
            tenant_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (tenant_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS subscriptions (
            subscription_id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            provider TEXT NOT NULL,
            provider_subscription_id TEXT,
            plan TEXT NOT NULL,
            status TEXT NOT NULL,
            current_period_end TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS whatsapp_business_accounts (
            waba_id TEXT PRIMARY KEY,
            tenant_id TEXT,
            display_name TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS whatsapp_phone_numbers (
            phone_number_id TEXT PRIMARY KEY,
            tenant_id TEXT,
            waba_id TEXT,
            display_phone_number TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS webhook_events (
            event_id TEXT PRIMARY KEY,
            tenant_id TEXT,
            provider TEXT NOT NULL,
            provider_event_id TEXT,
            event_type TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            idempotency_key TEXT UNIQUE
        );

        CREATE TABLE IF NOT EXISTS skill_runs (
            run_id TEXT PRIMARY KEY,
            tenant_id TEXT,
            skill_name TEXT NOT NULL,
            skill_version TEXT,
            status TEXT NOT NULL,
            input_json TEXT NOT NULL,
            output_json TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

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

        CREATE INDEX IF NOT EXISTS idx_whatsapp_messages_created
            ON whatsapp_messages(created_at);

        CREATE INDEX IF NOT EXISTS idx_webhook_events_provider
            ON webhook_events(provider, created_at);
        """
    )
    conn.commit()


def encode_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def decode_json(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    return json.loads(value)


def row_to_dict(row: Any | None) -> dict[str, Any] | None:
    if row is None:
        return None
    if isinstance(row, dict):
        return dict(row)
    return {key: row[key] for key in row.keys()}


def touch_task(conn: Connection, task_id: str, status: str, **fields: Any) -> None:
    now = utc_now_iso()
    assignments = ["status = ?", "updated_at = ?"]
    values: list[Any] = [status, now]
    for key, value in fields.items():
        assignments.append(f"{key} = ?")
        values.append(value)
    values.append(task_id)
    conn.execute(f"UPDATE tasks SET {', '.join(assignments)} WHERE task_id = ?", values)
    conn.commit()


def is_postgres_connection(conn: Any) -> bool:
    return isinstance(conn, PostgresConnection)


def is_integrity_error(exc: Exception) -> bool:
    if isinstance(exc, sqlite3.IntegrityError):
        return True
    name = exc.__class__.__name__
    module = exc.__class__.__module__
    return name in {"IntegrityError", "UniqueViolation"} or "psycopg" in module and "UniqueViolation" in name


def _postgres_sql(sql: str) -> str:
    return sql.replace("?", "%s")


def _split_sql_script(script: str) -> list[str]:
    return [statement.strip() for statement in script.split(";") if statement.strip()]
