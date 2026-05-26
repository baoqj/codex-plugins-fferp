from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.common.db import connect
from scripts.whatsapp.generate_reply_task import generate_reply_task
from scripts.whatsapp.parse_webhook_payload import parse_webhook_payload
from service.queue.task_queue import list_tasks
from service.workers.message_processor import process_one_task


def main() -> None:
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "contacts": [{"wa_id": "15551234567", "profile": {"name": "Alice Buyer"}}],
                            "messages": [
                                {
                                    "from": "15551234567",
                                    "id": "wamid.smoke001",
                                    "timestamp": "1710000000",
                                    "type": "text",
                                    "text": {"body": "Need tomato sauce 10 cases"},
                                }
                            ],
                        }
                    }
                ]
            }
        ]
    }
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        os.environ["FFERP_DATA_DIR"] = str(root / "data")
        os.environ["FFERP_OUTPUT_DIR"] = str(root / "output")
        messages = parse_webhook_payload(payload)
        assert len(messages) == 1

        conn = connect()
        first = generate_reply_task(conn, messages[0], raw_payload_file=str(root / "raw.json"))
        second = generate_reply_task(conn, messages[0], raw_payload_file=str(root / "raw.json"))
        assert first is not None
        assert second is None
        assert len(list_tasks(conn, status="pending")) == 1

        result = process_one_task()
        assert result is not None
        assert result["status"] == "waiting_approval"
        draft = json.loads(Path(result["draft_file"]).read_text(encoding="utf-8"))
        assert draft["status"] == "draft_pending_approval"
        assert list((root / "output" / "approvals").glob("APP-*.json"))
        print(json.dumps({"ok": True, "result": result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
