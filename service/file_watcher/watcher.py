from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from scripts.common.config import ensure_runtime_dirs, get_settings
from scripts.common.db import connect
from scripts.common.logging import append_jsonl
from service.queue.task_queue import create_task


SUPPORTED_SUFFIXES = {".csv", ".xlsx", ".xls", ".pdf", ".docx", ".txt", ".json"}


def scan_once() -> list[dict]:
    settings = ensure_runtime_dirs(get_settings())
    inbox = settings.data_dir / "inbox"
    created: list[dict] = []
    with connect(settings.database_path) as conn:
        for path in sorted(inbox.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
                continue
            if "whatsapp" in path.parts:
                continue
            stat = path.stat()
            idempotency_key = f"inbox-file:{path.resolve()}:{int(stat.st_mtime)}:{stat.st_size}"
            task = create_task(
                conn,
                "import_inbox_file",
                {
                    "file_path": str(path),
                    "suffix": path.suffix.lower(),
                    "size": stat.st_size,
                    "modified_at": stat.st_mtime,
                },
                source="file_watcher",
                source_file=str(path),
                priority=7,
                idempotency_key=idempotency_key,
            )
            if task.get("status") == "pending":
                created.append(task)
    if created:
        append_jsonl(
            "action_log.jsonl",
            {
                "actor": "fferp-file-watcher",
                "action": "created_inbox_file_tasks",
                "task_ids": [task["task_id"] for task in created],
            },
        )
    return created


def main() -> None:
    parser = argparse.ArgumentParser(description="Watch data/inbox and create processing tasks.")
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--interval", type=float, default=5.0)
    args = parser.parse_args()

    while True:
        created = scan_once()
        if created:
            print(json.dumps({"created_tasks": [task["task_id"] for task in created]}, ensure_ascii=False))
        elif not args.loop:
            print("No new inbox files.")
            return
        if not args.loop:
            return
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
