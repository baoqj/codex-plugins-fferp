from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from scripts.common.config import ensure_runtime_dirs, get_settings
from scripts.common.db import decode_json, encode_json, row_to_dict
from scripts.common.ids import new_id, utc_now_iso
from scripts.common.logging import append_jsonl


def create_approval(
    conn: sqlite3.Connection,
    *,
    task_id: str,
    action_type: str,
    risk_level: str,
    draft_file: str | None,
    payload: dict[str, Any],
) -> dict[str, Any]:
    settings = ensure_runtime_dirs(get_settings())
    approval_id = new_id("APP")
    now = utc_now_iso()
    approval = {
        "approval_id": approval_id,
        "task_id": task_id,
        "action_type": action_type,
        "risk_level": risk_level,
        "draft_file": draft_file,
        "status": "pending",
        "created_by": "fferp-worker",
        "created_at": now,
        "requires_human": True,
        "payload": payload,
    }

    conn.execute(
        """
        INSERT INTO approvals (
            approval_id, task_id, action_type, risk_level, draft_file, status,
            created_at, updated_at, payload_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            approval_id,
            task_id,
            action_type,
            risk_level,
            draft_file,
            "pending",
            now,
            now,
            encode_json(payload),
        ),
    )
    conn.commit()

    json_path = settings.output_dir / "approvals" / f"{approval_id}.json"
    md_path = settings.output_dir / "approvals" / f"{approval_id}.md"
    json_path.write_text(json.dumps(approval, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_approval_markdown(approval), encoding="utf-8")
    append_jsonl(
        "approval_log.jsonl",
        {
            "actor": "fferp-worker",
            "action": "create_approval",
            "approval_id": approval_id,
            "task_id": task_id,
            "risk_level": risk_level,
            "draft_file": draft_file,
        },
    )
    approval["approval_file"] = str(json_path)
    approval["summary_file"] = str(md_path)
    return approval


def list_pending_approvals(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM approvals WHERE status = 'pending' ORDER BY created_at ASC"
    ).fetchall()
    return [_approval_row(row) for row in rows]


def review_approval(
    conn: sqlite3.Connection,
    approval_id: str,
    *,
    action: str,
    reviewer: str = "human",
    comment: str | None = None,
) -> dict[str, Any]:
    if action not in {"approve", "reject", "edit", "request_more_info", "cancel"}:
        raise ValueError(f"Unsupported approval action: {action}")
    row = conn.execute("SELECT * FROM approvals WHERE approval_id = ?", (approval_id,)).fetchone()
    if row is None:
        raise KeyError(f"Approval not found: {approval_id}")

    status_map = {
        "approve": "approved",
        "reject": "rejected",
        "edit": "edited",
        "request_more_info": "pending",
        "cancel": "cancelled",
    }
    now = utc_now_iso()
    conn.execute(
        """
        UPDATE approvals
        SET status = ?, reviewer = ?, reviewed_at = ?, comment = ?, updated_at = ?
        WHERE approval_id = ?
        """,
        (status_map[action], reviewer, now, comment, now, approval_id),
    )
    conn.commit()
    append_jsonl(
        "approval_log.jsonl",
        {
            "actor": reviewer,
            "action": f"approval_{action}",
            "approval_id": approval_id,
            "comment": comment,
        },
    )
    updated = conn.execute("SELECT * FROM approvals WHERE approval_id = ?", (approval_id,)).fetchone()
    return _approval_row(updated)


def _approval_row(row: sqlite3.Row) -> dict[str, Any]:
    item = row_to_dict(row)
    assert item is not None
    item["payload"] = decode_json(item.pop("payload_json"))
    return item


def _approval_markdown(approval: dict[str, Any]) -> str:
    payload = approval.get("payload", {})
    text = [
        f"# Approval {approval['approval_id']}",
        "",
        f"- Task: `{approval['task_id']}`",
        f"- Action: `{approval['action_type']}`",
        f"- Risk: `{approval['risk_level']}`",
        f"- Status: `{approval['status']}`",
        f"- Draft file: `{approval.get('draft_file') or ''}`",
        "",
        "## Summary",
        "",
        str(payload.get("summary", "Review the draft and approve, reject, or request more information.")),
    ]
    if payload.get("message_text"):
        text.extend(["", "## Incoming Message", "", payload["message_text"]])
    return "\n".join(text) + "\n"
