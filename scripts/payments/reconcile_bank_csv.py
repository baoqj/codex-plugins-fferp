from __future__ import annotations

import argparse
import csv
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

from scripts.common.config import ensure_runtime_dirs, get_settings
from scripts.common.ids import new_id
from scripts.common.logging import append_jsonl


def reconcile_bank_csv(bank_csv: str, receivables_csv: str, output_dir: str | None = None) -> dict:
    settings = ensure_runtime_dirs(get_settings())
    output_base = Path(output_dir) if output_dir else settings.output_dir / "reports"
    output_base.mkdir(parents=True, exist_ok=True)
    bank_rows = _read_csv(Path(bank_csv))
    receivable_rows = _read_csv(Path(receivables_csv))
    matches = [_match_payment(payment, receivable_rows) for payment in bank_rows]
    summary = {
        "total_payments": len(bank_rows),
        "exact_match": sum(1 for row in matches if row["match_type"] == "exact_match"),
        "likely_match": sum(1 for row in matches if row["match_type"] == "likely_match"),
        "partial_match": sum(1 for row in matches if row["match_type"] == "partial_match"),
        "unknown": sum(1 for row in matches if row["match_type"] == "unknown"),
    }
    report_id = new_id("PAY")
    json_path = output_base / f"payment_match_report_{report_id}.json"
    md_path = output_base / f"payment_match_report_{report_id}.md"
    payload = {"summary": summary, "matches": matches, "sources": [bank_csv, receivables_csv]}
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_payment_markdown(payload), encoding="utf-8")
    append_jsonl(
        "action_log.jsonl",
        {
            "actor": "fferp-payment-reconciler",
            "action": "reconcile_bank_csv",
            "input_ref": bank_csv,
            "output_ref": str(json_path),
            "requires_approval": True,
        },
    )
    return {"summary": summary, "json_report": str(json_path), "markdown_report": str(md_path)}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _amount(value: str | None) -> Decimal | None:
    try:
        return Decimal((value or "").replace(",", "").strip())
    except InvalidOperation:
        return None


def _match_payment(payment: dict[str, str], receivables: list[dict[str, str]]) -> dict:
    payment_amount = _amount(payment.get("amount") or payment.get("Amount"))
    reference = " ".join(
        str(payment.get(key, ""))
        for key in ("reference", "Reference", "memo", "Memo", "description", "Description", "order_id")
    ).lower()
    best = None
    for receivable in receivables:
        amount_due = _amount(receivable.get("amount_due"))
        amount_paid = _amount(receivable.get("amount_paid")) or Decimal("0")
        outstanding = amount_due - amount_paid if amount_due is not None else None
        order_id = (receivable.get("order_id") or "").lower()
        customer_id = (receivable.get("customer_id") or "").lower()
        ref_hit = bool(order_id and order_id in reference) or bool(customer_id and customer_id in reference)
        if payment_amount is not None and outstanding is not None and payment_amount == outstanding and ref_hit:
            best = (receivable, "exact_match")
            break
        if payment_amount is not None and outstanding is not None and payment_amount < outstanding and ref_hit:
            best = (receivable, "partial_match")
            break
        if ref_hit:
            best = (receivable, "likely_match")
    if not best:
        return {"payment": payment, "match_type": "unknown", "requires_approval": True}
    receivable, match_type = best
    return {
        "payment": payment,
        "receivable_id": receivable.get("receivable_id"),
        "customer_id": receivable.get("customer_id"),
        "order_id": receivable.get("order_id"),
        "match_type": match_type,
        "requires_approval": True,
    }


def _payment_markdown(payload: dict) -> str:
    lines = [
        "# Payment Match Report",
        "",
        "## Summary",
        "",
    ]
    for key, value in payload["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Matches", ""])
    for match in payload["matches"]:
        lines.append(f"- {match['match_type']} | order: {match.get('order_id', '')} | approval required")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Match a bank CSV with receivables.")
    parser.add_argument("--bank-csv", required=True)
    parser.add_argument("--receivables-csv", required=True)
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()
    print(json.dumps(reconcile_bank_csv(args.bank_csv, args.receivables_csv, args.output_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
