from __future__ import annotations

from scripts.common.db import connect
from scripts.common.approvals import list_pending_approvals
from service.queue.task_queue import list_tasks


def inspect_status() -> dict:
    """Small local bridge function for future MCP wrapping."""
    with connect() as conn:
        return {
            "pending_tasks": list_tasks(conn, status="pending", limit=20),
            "pending_approvals": list_pending_approvals(conn),
        }
