from __future__ import annotations

from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from scripts.common.approvals import list_pending_approvals
from scripts.common.db import connect, row_to_dict
from scripts.common.security import require_api_token
from service.queue.task_queue import list_tasks
from service.workers.message_processor import process_one_task


app = FastAPI(title="FFERP MCP Bridge", version="0.1.0")


class ToolCall(BaseModel):
    tool: str
    arguments: dict[str, Any] = {}


TOOLS = {
    "fferp.status": "Return task and approval status counts.",
    "fferp.pending_tasks": "List pending task queue entries.",
    "fferp.pending_approvals": "List pending human approval tasks.",
    "fferp.inbox_messages": "List recent WhatsApp inbox messages.",
    "fferp.process_one_task": "Process one pending task and return the result.",
}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/tools/list", dependencies=[Depends(require_api_token)])
def list_tools() -> dict[str, Any]:
    return {"tools": [{"name": name, "description": description} for name, description in TOOLS.items()]}


@app.get("/context/status", dependencies=[Depends(require_api_token)])
def context_status() -> dict[str, Any]:
    with connect() as conn:
        task_counts = {
            row["status"]: row["count"]
            for row in conn.execute("SELECT status, COUNT(*) AS count FROM tasks GROUP BY status").fetchall()
        }
        approval_counts = {
            row["status"]: row["count"]
            for row in conn.execute("SELECT status, COUNT(*) AS count FROM approvals GROUP BY status").fetchall()
        }
    return {"tasks": task_counts, "approvals": approval_counts}


@app.post("/tools/call", dependencies=[Depends(require_api_token)])
def call_tool(call: ToolCall) -> dict[str, Any]:
    if call.tool == "fferp.status":
        return {"result": context_status()}
    if call.tool == "fferp.pending_tasks":
        with connect() as conn:
            return {"result": list_tasks(conn, status="pending", limit=int(call.arguments.get("limit", 50)))}
    if call.tool == "fferp.pending_approvals":
        with connect() as conn:
            return {"result": list_pending_approvals(conn)}
    if call.tool == "fferp.inbox_messages":
        limit = max(1, min(int(call.arguments.get("limit", 50)), 200))
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT message_id, from_phone, customer_id, direction, message_type, text,
                       intent, risk_level, status, created_at, updated_at
                FROM whatsapp_messages
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return {"result": [item for row in rows if (item := row_to_dict(row)) is not None]}
    if call.tool == "fferp.process_one_task":
        return {"result": process_one_task()}
    raise HTTPException(status_code=404, detail=f"Unknown tool: {call.tool}")
