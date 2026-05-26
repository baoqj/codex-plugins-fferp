from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from scripts.common.approvals import list_pending_approvals, review_approval
from scripts.common.config import ensure_runtime_dirs, get_settings
from scripts.common.db import connect
from scripts.common.logging import append_jsonl
from scripts.whatsapp.generate_reply_task import generate_reply_task
from scripts.whatsapp.parse_webhook_payload import parse_webhook_payload
from scripts.whatsapp.store_incoming_message import log_normalized_message, store_raw_webhook_payload
from scripts.whatsapp.verify_webhook import verify_subscription
from service.queue.task_queue import list_tasks


app = FastAPI(title="FFERP Service", version="0.1.0")


class ApprovalReview(BaseModel):
    action: str
    reviewer: str = "human"
    comment: str | None = None


@app.on_event("startup")
def startup() -> None:
    ensure_runtime_dirs(get_settings())
    connect().close()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/status")
def status() -> dict[str, Any]:
    with connect() as conn:
        counts = {
            row["status"]: row["count"]
            for row in conn.execute("SELECT status, COUNT(*) AS count FROM tasks GROUP BY status").fetchall()
        }
        approvals = {
            row["status"]: row["count"]
            for row in conn.execute("SELECT status, COUNT(*) AS count FROM approvals GROUP BY status").fetchall()
        }
    return {"tasks": counts, "approvals": approvals}


@app.get("/tasks/pending")
def pending_tasks(limit: int = 50) -> list[dict[str, Any]]:
    with connect() as conn:
        return list_tasks(conn, status="pending", limit=limit)


@app.get("/approvals/pending")
def pending_approvals() -> list[dict[str, Any]]:
    with connect() as conn:
        return list_pending_approvals(conn)


@app.post("/approvals/{approval_id}/review")
def approve_or_reject(approval_id: str, payload: ApprovalReview) -> dict[str, Any]:
    try:
        with connect() as conn:
            return review_approval(
                conn,
                approval_id,
                action=payload.action,
                reviewer=payload.reviewer,
                comment=payload.comment,
            )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/webhook", response_class=PlainTextResponse)
def verify_webhook(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
) -> PlainTextResponse:
    challenge = verify_subscription(hub_mode, hub_verify_token, hub_challenge)
    if challenge is None:
        raise HTTPException(status_code=403, detail="Webhook verification failed.")
    return PlainTextResponse(challenge)


@app.post("/webhook")
async def receive_webhook(request: Request) -> dict[str, Any]:
    payload = await request.json()
    raw_path = store_raw_webhook_payload(payload)
    messages = parse_webhook_payload(payload)
    created_tasks: list[str] = []
    duplicates = 0

    with connect() as conn:
        for message in messages:
            log_normalized_message(message, str(raw_path))
            task = generate_reply_task(conn, message, raw_payload_file=str(raw_path))
            if task is None:
                duplicates += 1
            else:
                created_tasks.append(task["task_id"])

    append_jsonl(
        "action_log.jsonl",
        {
            "actor": "fferp-api",
            "action": "webhook_processed",
            "message_count": len(messages),
            "created_tasks": created_tasks,
            "duplicates": duplicates,
        },
    )
    return {"ok": True, "messages": len(messages), "created_tasks": created_tasks, "duplicates": duplicates}
