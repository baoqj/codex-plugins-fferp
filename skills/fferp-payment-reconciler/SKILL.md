---
name: fferp-payment-reconciler
description: Match bank or payment records against FFERP receivables and sales orders with review-safe statuses. Use when Codex needs payment CSV import, receivables matching, exact/likely/partial/conflict classification, overdue reports, or payment reminder drafts.
---

# FFERP Payment Reconciler

## Workflow

1. Load bank CSV, payment Excel, receivables, sales orders, and customer records.
2. Normalize payment references, dates, amounts, currency, and customer names.
3. Match payments to receivables and sales orders.
4. Classify matches as exact_match, likely_match, partial_match, conflict, or unknown.
5. Generate payment match JSON/Excel and overdue report.
6. Create approval tasks for confirmations, reminders, conflicts, and partial matches.
7. Append action and approval logs.

## Safety Rules

- Never confirm payment automatically unless a future config explicitly allows the exact low-risk case.
- Never send payment reminders automatically.
- Treat amount mismatches, duplicate references, chargebacks, and unknown payers as high-risk review items.

## Outputs

- payment match report JSON/Excel
- overdue Markdown report
- payment reminder drafts
- approval tasks

## Resource Map

- Use `schemas/payment_match.schema.json` for output.
- Use `templates/overdue_report.md` for reports.
