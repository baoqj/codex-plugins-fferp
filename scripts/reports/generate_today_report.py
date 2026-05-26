from __future__ import annotations

import argparse
import csv
import json
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from scripts.common.config import ensure_runtime_dirs, get_settings
from scripts.common.ids import new_id
from scripts.common.logging import append_jsonl


def generate_report(target_date: str | None = None, output_dir: str | None = None) -> dict:
    settings = ensure_runtime_dirs(get_settings())
    target_date = target_date or date.today().isoformat()
    output_base = Path(output_dir) if output_dir else settings.output_dir / "reports"
    output_base.mkdir(parents=True, exist_ok=True)
    sales_path = settings.data_dir / "transactions" / "sales_orders.csv"
    inventory_path = settings.data_dir / "transactions" / "inventory_movements.csv"
    receivables_path = settings.data_dir / "transactions" / "receivables.csv"
    sales_rows = _read_csv(sales_path)
    inventory_rows = _read_csv(inventory_path)
    receivable_rows = _read_csv(receivables_path)
    todays_sales = [row for row in sales_rows if row.get("order_date") == target_date]
    todays_inventory = [row for row in inventory_rows if row.get("date") == target_date]
    overdue = [row for row in receivable_rows if row.get("status") not in {"paid", "closed", ""}]
    summary = {
        "date": target_date,
        "sales_order_count": len(todays_sales),
        "sales_total_amount": str(sum((_amount(row.get("total_amount")) or Decimal("0")) for row in todays_sales)),
        "inventory_movement_count": len(todays_inventory),
        "open_receivables_count": len(overdue),
    }
    report_id = new_id("RPT")
    md_path = output_base / f"sales_inventory_report_{target_date}_{report_id}.md"
    json_path = output_base / f"sales_inventory_report_{target_date}_{report_id}.json"
    payload = {
        "report_type": "daily_sales_inventory",
        "period": target_date,
        "summary": summary,
        "source_files": [str(sales_path), str(inventory_path), str(receivables_path)],
        "abnormal_records": _abnormal_records(todays_sales, todays_inventory, overdue),
    }
    md_path.write_text(_report_markdown(payload), encoding="utf-8")
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    append_jsonl(
        "action_log.jsonl",
        {
            "actor": "fferp-report-generator",
            "action": "generate_daily_sales_inventory_report",
            "output_ref": str(md_path),
        },
    )
    return {"markdown_report": str(md_path), "json_report": str(json_path), "summary": summary}


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _amount(value: str | None) -> Decimal | None:
    try:
        return Decimal((value or "").replace(",", "").strip())
    except InvalidOperation:
        return None


def _abnormal_records(sales_rows: list[dict], inventory_rows: list[dict], receivable_rows: list[dict]) -> list[dict]:
    abnormal = []
    for row in sales_rows:
        if not row.get("customer_id") or not row.get("total_amount"):
            abnormal.append({"source": "sales_orders", "record": row, "issue": "missing customer_id or total_amount"})
    for row in inventory_rows:
        quantity = _amount(row.get("quantity"))
        if quantity is None or quantity == 0:
            abnormal.append({"source": "inventory_movements", "record": row, "issue": "missing or zero quantity"})
    for row in receivable_rows:
        if row.get("status") not in {"paid", "closed", ""}:
            abnormal.append({"source": "receivables", "record": row, "issue": "open receivable"})
    return abnormal


def _report_markdown(payload: dict) -> str:
    lines = [
        "# Daily Sales and Inventory Report",
        "",
        f"- Date: {payload['period']}",
        "",
        "## Summary",
        "",
    ]
    for key, value in payload["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Abnormal Records", ""])
    if not payload["abnormal_records"]:
        lines.append("No abnormal records found.")
    else:
        for record in payload["abnormal_records"]:
            lines.append(f"- {record['source']}: {record['issue']}")
    lines.extend(["", "## Source References", ""])
    for source in payload["source_files"]:
        lines.append(f"- `{source}`")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate today's sales and inventory report.")
    parser.add_argument("--date", default=None)
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()
    print(json.dumps(generate_report(args.date, args.output_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
