---
name: fferp-inventory-checker
description: Check FFERP inventory availability for draft orders and create stock reports or reservation proposals. Use when Codex needs available/insufficient/needs_review stock status, inventory movement review, warehouse balance checks, shortage reports, or approval-only reservation proposals.
---

# FFERP Inventory Checker

## Workflow

1. Load the draft order and inventory balance files from `data/transactions/`.
2. Validate SKU, warehouse, current stock, reserved stock, and available stock fields.
3. Compute availability for every order line.
4. Produce `available`, `insufficient`, or `needs_review` status.
5. Write a stock reservation proposal only when stock exists.
6. Create approval tasks for any reservation, deduction, or warehouse dispatch action.
7. Append inventory and action log entries.

## Safety Rules

- Never deduct official inventory automatically.
- Never reserve stock without approval.
- Treat negative, missing, stale, or conflicting stock values as `needs_review`.
- Do not mark an order shipped from this skill.

## Outputs

- inventory check JSON
- stock availability report
- reservation proposal requiring approval

## Resource Map

- Use `schemas/inventory_check.schema.json` for check output.
- Use `templates/inventory_report.md` for review reports.
