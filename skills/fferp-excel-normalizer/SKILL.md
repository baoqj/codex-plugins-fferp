---
name: fferp-excel-normalizer
description: Normalize messy FFERP Excel or CSV files into clean tables with validation reports. Use when Codex needs to process customer spreadsheets, supplier price lists, inventory sheets, order sheets, payment CSV files, merged-cell workbooks, unknown headers, or local ERP import files without overwriting originals.
---

# FFERP Excel Normalizer

## Workflow

1. Identify the business domain: products, customers, suppliers, inventory, sales orders, payments, or receivables.
2. Read the source file without modifying it.
3. Detect the header row, merged cells, blank columns, repeated headings, and totals rows.
4. Normalize fields to the matching schema under `schemas/`.
5. Write a cleaned copy to `data/inbox/normalized/` or an explicitly requested output path.
6. Write a validation report that lists missing required fields, suspicious quantities, date parsing issues, duplicate IDs, and rows requiring review.
7. Append an action log entry in `data/logs/action_log.jsonl`.

## Safety Rules

- Never overwrite the original workbook.
- Never silently drop rows.
- Preserve a source row reference in normalized output.
- Mark missing SKU, customer name, quantity, price, and date issues as `needs_review`.
- Treat formulas and merged-cell values as extracted data, not as approval to update official records.

## Outputs

- normalized CSV or Excel file
- JSON validation report
- Markdown mapping report
- JSONL action log entry

## Resource Map

- Use `../../scripts/excel/` for reusable normalization scripts.
- Use `schemas/normalized-table.schema.json` for normalized output shape.
- Use `templates/validation_report.md` for human-readable review output.
