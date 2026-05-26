from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

from scripts.common.db import connect
from scripts.common.ids import utc_now_iso
from scripts.orders.extract_from_whatsapp import extract_orders_for_date
from scripts.payments.reconcile_bank_csv import reconcile_bank_csv
from scripts.reports.generate_today_report import generate_report
from service.file_watcher.watcher import scan_once


def test_direct_order_extractor_from_todays_whatsapp(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FFERP_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("FFERP_OUTPUT_DIR", str(tmp_path / "output"))
    conn = connect()
    today = date.today().isoformat()
    conn.execute(
        """
        INSERT INTO whatsapp_messages (
            message_id, from_phone, direction, message_type, text, status, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "wamid.direct001",
            "15551234567",
            "inbound",
            "text",
            "Need tomato sauce 10 cases",
            "received",
            utc_now_iso(),
            utc_now_iso(),
        ),
    )
    conn.commit()

    result = extract_orders_for_date(today)

    assert result["created_tasks"]
    assert result["processed"][0]["intent"] == "order_request"
    assert result["waiting_approval_count"] == 1


def test_direct_payment_reconciler_matches_bank_csv(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FFERP_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("FFERP_OUTPUT_DIR", str(tmp_path / "output"))
    bank = tmp_path / "bank.csv"
    receivables = tmp_path / "receivables.csv"
    _write_csv(bank, ["payment_id", "amount", "reference"], [["PMT-1", "120.00", "SO-1 payment"]])
    _write_csv(
        receivables,
        ["receivable_id", "customer_id", "order_id", "amount_due", "amount_paid", "status"],
        [["AR-1", "CUST-1", "SO-1", "120.00", "0", "open"]],
    )

    result = reconcile_bank_csv(str(bank), str(receivables), str(tmp_path / "reports"))
    payload = json.loads(Path(result["json_report"]).read_text(encoding="utf-8"))

    assert payload["summary"]["exact_match"] == 1
    assert payload["matches"][0]["requires_approval"] is True


def test_direct_report_generator_creates_report(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FFERP_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("FFERP_OUTPUT_DIR", str(tmp_path / "output"))
    transactions = tmp_path / "data" / "transactions"
    transactions.mkdir(parents=True)
    today = date.today().isoformat()
    _write_csv(
        transactions / "sales_orders.csv",
        ["order_id", "customer_id", "order_date", "status", "source_message_id", "total_amount"],
        [["SO-1", "CUST-1", today, "draft", "wamid.1", "120.00"]],
    )
    _write_csv(
        transactions / "inventory_movements.csv",
        ["movement_id", "date", "sku", "warehouse_id", "movement_type", "quantity"],
        [["MOV-1", today, "SKU-1", "WH-1", "in", "10"]],
    )
    _write_csv(
        transactions / "receivables.csv",
        ["receivable_id", "customer_id", "order_id", "amount_due", "amount_paid", "due_date", "status"],
        [["AR-1", "CUST-1", "SO-1", "120.00", "0", today, "open"]],
    )

    result = generate_report(today, str(tmp_path / "reports"))

    assert Path(result["markdown_report"]).exists()
    assert result["summary"]["sales_order_count"] == 1
    assert result["summary"]["open_receivables_count"] == 1


def test_file_watcher_creates_inbox_task(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FFERP_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("FFERP_OUTPUT_DIR", str(tmp_path / "output"))
    inbox = tmp_path / "data" / "inbox"
    inbox.mkdir(parents=True)
    (inbox / "bank.csv").write_text("payment_id,amount\nPMT-1,10\n", encoding="utf-8")

    created = scan_once()

    assert len(created) == 1
    assert created[0]["task_type"] == "import_inbox_file"


def _write_csv(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)
