from __future__ import annotations

import argparse
import json
from typing import Any

import requests

from scripts.common.config import get_settings
from scripts.common.logging import append_jsonl


def send_text_message(to_phone: str, text: str, *, dry_run: bool = True) -> dict[str, Any]:
    settings = get_settings()
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_phone,
        "type": "text",
        "text": {"preview_url": False, "body": text},
    }
    if dry_run or not settings.whatsapp_send_enabled:
        append_jsonl(
            "action_log.jsonl",
            {
                "actor": "fferp-send-message",
                "action": "dry_run_send_whatsapp",
                "to_phone": to_phone,
                "payload": payload,
            },
        )
        return {"dry_run": True, "payload": payload}

    if not settings.whatsapp_access_token or not settings.whatsapp_phone_number_id:
        raise RuntimeError("WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID are required to send messages.")

    url = f"https://graph.facebook.com/{settings.whatsapp_graph_api_version}/{settings.whatsapp_phone_number_id}/messages"
    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {settings.whatsapp_access_token}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=20,
    )
    response.raise_for_status()
    result = response.json()
    append_jsonl(
        "action_log.jsonl",
        {
            "actor": "fferp-send-message",
            "action": "send_whatsapp",
            "to_phone": to_phone,
            "response": result,
        },
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Send a WhatsApp text message after approval.")
    parser.add_argument("--to", required=True)
    parser.add_argument("--text", required=True)
    parser.add_argument("--send", action="store_true", help="Actually call WhatsApp API. Default is dry-run.")
    args = parser.parse_args()
    print(json.dumps(send_text_message(args.to, args.text, dry_run=not args.send), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
