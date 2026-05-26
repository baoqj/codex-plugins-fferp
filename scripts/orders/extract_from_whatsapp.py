from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from scripts.common.config import ensure_runtime_dirs, get_settings
from scripts.common.db import connect
from service.queue.task_queue import create_task, list_tasks
from service.workers.message_processor import process_one_task


def extract_orders_for_date(target_date: str | None = None, *, process: bool = True) -> dict:
    settings = ensure_runtime_dirs(get_settings())
    target_date = target_date or date.today().isoformat()
    results = []
    with connect(settings.database_path) as conn:
        rows = conn.execute(
            """
            SELECT message_id, from_phone, customer_id, message_type, text, created_at
            FROM whatsapp_messages
            WHERE direction = 'inbound'
              AND COALESCE(text, '') <> ''
              AND date(substr(created_at, 1, 10)) = date(?)
            ORDER BY created_at ASC
            """,
            (target_date,),
        ).fetchall()
        for row in rows:
            text = (row["text"] or "").lower()
            if not any(keyword in text for keyword in ("order", "need", "want", "buy", "下单", "要", "订")):
                continue
            task = create_task(
                conn,
                "process_whatsapp_message",
                {
                    "message": {
                        "message_id": row["message_id"],
                        "from_phone": row["from_phone"],
                        "customer_id": row["customer_id"],
                        "message_type": row["message_type"],
                        "text": row["text"],
                    },
                    "raw_payload_file": None,
                },
                source="codex-direct",
                priority=3,
                idempotency_key=f"direct-order-extract:{row['message_id']}",
            )
            results.append({"message_id": row["message_id"], "task_id": task["task_id"]})

    processed = []
    if process:
        while True:
            result = process_one_task()
            if result is None:
                break
            processed.append(result)

    with connect(settings.database_path) as conn:
        pending = list_tasks(conn, status="waiting_approval")
    return {
        "date": target_date,
        "created_tasks": results,
        "processed": processed,
        "waiting_approval_count": len(pending),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract draft orders from today's WhatsApp messages.")
    parser.add_argument("--date", default=None)
    parser.add_argument("--no-process", action="store_true")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    result = extract_orders_for_date(args.date, process=not args.no_process)
    if args.output:
        Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
