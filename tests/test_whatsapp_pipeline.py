from __future__ import annotations

import json

from scripts.common.db import connect
from scripts.whatsapp.generate_reply_task import generate_reply_task
from scripts.whatsapp.parse_webhook_payload import parse_webhook_payload
from service.queue.task_queue import list_tasks
from service.workers.message_processor import process_one_task


def sample_payload() -> dict:
    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "contacts": [
                                {"wa_id": "15551234567", "profile": {"name": "Alice Buyer"}}
                            ],
                            "messages": [
                                {
                                    "from": "15551234567",
                                    "id": "wamid.test001",
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


def test_parse_webhook_payload_extracts_text_message() -> None:
    messages = parse_webhook_payload(sample_payload())
    assert len(messages) == 1
    assert messages[0]["message_id"] == "wamid.test001"
    assert messages[0]["from_phone"] == "15551234567"
    assert messages[0]["text"] == "Need tomato sauce 10 cases"
    assert messages[0]["customer_profile_name"] == "Alice Buyer"


def test_task_generation_deduplicates_messages(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FFERP_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("FFERP_OUTPUT_DIR", str(tmp_path / "output"))
    conn = connect()
    message = parse_webhook_payload(sample_payload())[0]

    first = generate_reply_task(conn, message, raw_payload_file="/tmp/raw.json")
    second = generate_reply_task(conn, message, raw_payload_file="/tmp/raw.json")

    assert first is not None
    assert second is None
    assert len(list_tasks(conn, status="pending")) == 1


def test_worker_creates_draft_order_and_approval(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FFERP_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("FFERP_OUTPUT_DIR", str(tmp_path / "output"))
    conn = connect()
    message = parse_webhook_payload(sample_payload())[0]
    task = generate_reply_task(conn, message, raw_payload_file="/tmp/raw.json")
    assert task is not None

    result = process_one_task()

    assert result is not None
    assert result["status"] == "waiting_approval"
    assert result["intent"] == "order_request"
    draft = json.loads(open(result["draft_file"], encoding="utf-8").read())
    assert draft["status"] == "draft_pending_approval"
    assert draft["needs_review"] is True
    approval_files = list((tmp_path / "output" / "approvals").glob("APP-*.json"))
    assert len(approval_files) == 1
