from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any

from scripts.common.approvals import create_approval
from scripts.common.config import ensure_runtime_dirs, get_settings
from scripts.common.db import connect
from scripts.common.intent import classify_intent
from scripts.common.logging import append_jsonl
from service.queue.task_queue import (
    claim_next_task,
    complete_task,
    fail_task,
    mark_waiting_approval,
    update_whatsapp_processing_state,
)


def process_one_task() -> dict[str, Any] | None:
    settings = ensure_runtime_dirs(get_settings())
    with connect(settings.database_path) as conn:
        task = claim_next_task(conn)
        if task is None:
            return None
        try:
            if task["task_type"] == "process_whatsapp_message":
                return _process_whatsapp_message(conn, task)
            complete_task(conn, task["task_id"])
            return {"task_id": task["task_id"], "status": "completed", "note": "No processor registered."}
        except Exception as exc:  # pragma: no cover - defensive service logging
            fail_task(conn, task["task_id"], str(exc))
            append_jsonl(
                "error_log.jsonl",
                {
                    "actor": "fferp-worker",
                    "action": "task_failed",
                    "task_id": task["task_id"],
                    "error": str(exc),
                },
            )
            raise


def _process_whatsapp_message(conn, task: dict[str, Any]) -> dict[str, Any]:
    settings = ensure_runtime_dirs(get_settings())
    message = task["payload"]["message"]
    message_id = message["message_id"]
    intent = classify_intent(message.get("text"))
    update_whatsapp_processing_state(
        conn,
        message_id,
        intent=intent.intent,
        risk_level=intent.risk_level,
        status="drafted",
    )

    if intent.intent == "order_request":
        draft_file, summary = _write_order_draft(settings.output_dir, message, intent.confidence)
        action_type = "review_draft_order"
    else:
        draft_file, summary = _write_reply_draft(settings.output_dir, message, intent.intent)
        action_type = "send_whatsapp_reply"

    approval = create_approval(
        conn,
        task_id=task["task_id"],
        action_type=action_type,
        risk_level=intent.risk_level,
        draft_file=draft_file,
        payload={
            "summary": summary,
            "message_id": message_id,
            "from_phone": message.get("from_phone"),
            "message_text": message.get("text"),
            "draft_content": _read_text_file(draft_file),
            "intent": intent.intent,
            "confidence": intent.confidence,
        },
    )
    mark_waiting_approval(conn, task["task_id"], approval["approval_file"])
    append_jsonl(
        "action_log.jsonl",
        {
            "actor": "fferp-worker",
            "skill": _skill_for_intent(intent.intent),
            "action": "draft_created",
            "task_id": task["task_id"],
            "message_id": message_id,
            "intent": intent.intent,
            "confidence": intent.confidence,
            "requires_approval": True,
            "approval_id": approval["approval_id"],
            "output_ref": draft_file,
        },
    )
    return {
        "task_id": task["task_id"],
        "status": "waiting_approval",
        "intent": intent.intent,
        "approval_id": approval["approval_id"],
        "draft_file": draft_file,
    }


def _write_reply_draft(output_dir: Path, message: dict[str, Any], intent: str) -> tuple[str, str]:
    drafts_dir = output_dir / "drafts" / "whatsapp"
    drafts_dir.mkdir(parents=True, exist_ok=True)
    message_id = _safe_filename(message["message_id"])
    draft_path = drafts_dir / f"reply_{message_id}.txt"
    body = _reply_body(message, intent)
    draft_path.write_text(body, encoding="utf-8")
    summary = f"Draft WhatsApp reply for `{intent}` message from `{message.get('from_phone')}`."
    return str(draft_path), summary


def _write_order_draft(output_dir: Path, message: dict[str, Any], confidence: float) -> tuple[str, str]:
    order_dir = output_dir / "drafts" / "orders"
    order_dir.mkdir(parents=True, exist_ok=True)
    message_id = _safe_filename(message["message_id"])
    order_path = order_dir / f"draft_order_{message_id}.json"
    summary_path = order_dir / f"draft_order_{message_id}.md"
    items = _extract_line_items(message.get("text") or "")
    draft = {
        "status": "draft_pending_approval",
        "source": "whatsapp",
        "source_message_id": message["message_id"],
        "from_phone": message.get("from_phone"),
        "customer_id": message.get("customer_id"),
        "items": items,
        "match_confidence": confidence,
        "needs_review": True,
        "raw_text": message.get("text"),
    }
    order_path.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")
    summary_path.write_text(_order_summary_markdown(draft), encoding="utf-8")
    summary = f"Draft order extracted with {len(items)} possible line item(s). Product matching and stock check require review."
    return str(order_path), summary


def _reply_body(message: dict[str, Any], intent: str) -> str:
    name = message.get("customer_profile_name") or "there"
    if intent == "quotation_request":
        return f"Hi {name}, thanks for your inquiry. We are checking the latest price and stock, and will confirm shortly."
    if intent == "delivery_status":
        return f"Hi {name}, we are checking the delivery status for you and will update you shortly."
    if intent == "payment_notice":
        return f"Hi {name}, thanks for the payment update. We are checking the payment record and will confirm after review."
    if intent == "complaint":
        return f"Hi {name}, sorry to hear this. We are reviewing the issue and will follow up carefully after checking the order details."
    return f"Hi {name}, thanks for your message. We are checking and will get back to you shortly."


def _extract_line_items(text: str) -> list[dict[str, Any]]:
    items = []
    for line in text.splitlines() or [text]:
        match = re.search(r"(?P<name>[A-Za-z0-9\u4e00-\u9fff _.-]{2,}?)\s*(?:x|\*|qty|数量)?\s*(?P<qty>\d+(?:\.\d+)?)\s*(?P<unit>pcs|pc|case|cases|box|boxes|kg|箱|件|个)?", line, re.I)
        if match:
            items.append(
                {
                    "raw_name": match.group("name").strip(),
                    "quantity": float(match.group("qty")),
                    "unit": match.group("unit") or "",
                    "sku": None,
                    "match_confidence": 0.0,
                    "needs_review": True,
                }
            )
    return items


def _order_summary_markdown(draft: dict[str, Any]) -> str:
    lines = [
        "# Draft Order",
        "",
        f"- Source message: `{draft['source_message_id']}`",
        f"- From phone: `{draft.get('from_phone') or ''}`",
        f"- Status: `{draft['status']}`",
        f"- Needs review: `{draft['needs_review']}`",
        "",
        "## Items",
        "",
    ]
    if not draft["items"]:
        lines.append("No reliable line items extracted. Human review is required.")
    else:
        for item in draft["items"]:
            lines.append(f"- {item['raw_name']} | qty: {item['quantity']} {item['unit']} | SKU: review needed")
    return "\n".join(lines) + "\n"


def _skill_for_intent(intent: str) -> str:
    if intent == "order_request":
        return "fferp-order-extractor"
    if intent == "payment_notice":
        return "fferp-payment-reconciler"
    return "fferp-whatsapp-reply"


def _safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def _read_text_file(path: str | None) -> str | None:
    if not path:
        return None
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Process FFERP queued tasks.")
    parser.add_argument("--loop", action="store_true", help="Run continuously.")
    parser.add_argument("--sleep", type=float, default=2.0)
    args = parser.parse_args()

    while True:
        result = process_one_task()
        if result:
            print(json.dumps(result, ensure_ascii=False))
        elif not args.loop:
            print("No pending tasks.")
            return
        if not args.loop:
            return
        time.sleep(args.sleep)


if __name__ == "__main__":
    main()
