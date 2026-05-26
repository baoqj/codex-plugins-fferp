---
name: fferp-report-generator
description: Generate FFERP sales, inventory, receivables, distributor, customer follow-up, top-products, and order-pipeline reports from local files and logs. Use when Codex needs daily, weekly, or monthly business reports with source references, abnormal-record lists, Markdown output, Excel output, or optional PDF export.
---

# FFERP Report Generator

## Workflow

1. Identify report type and time period.
2. Load only relevant files from `data/master/`, `data/transactions/`, and `data/logs/`.
3. Validate source freshness and missing data.
4. Generate metrics, abnormal records, and source references.
5. Write Markdown and Excel outputs under `output/reports/`.
6. Do not hide missing source data.
7. Append an action log entry.

## Safety Rules

- Reports are analytical outputs, not approvals to execute business actions.
- List missing, stale, inconsistent, or duplicate records.
- Keep source file references and extraction timestamps.
- Do not invent sales, stock, payment, or receivable values.

## Outputs

- Markdown report
- Excel report
- optional PDF report
- source reference section
- abnormal records section

## Resource Map

- Use `schemas/business_report.schema.json` for output.
- Use `templates/daily_sales_report.md` for report structure.
