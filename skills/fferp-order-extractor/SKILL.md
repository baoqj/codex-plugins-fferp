---
name: fferp-order-extractor
description: Extract draft sales orders from WhatsApp messages, text, PDFs, or Excel files for FFERP. Use when Codex needs to turn free-form customer order requests into draft_order JSON, order summaries, confirmation drafts, product matching checks, inventory checks, and approval tasks.
---

# FFERP Order Extractor

## Workflow

1. Confirm the source and customer identity.
2. Extract requested products, quantities, units, delivery dates, delivery address, and special instructions.
3. Invoke or follow `fferp-product-matcher` logic for each line item.
4. Invoke or follow `fferp-inventory-checker` logic before proposing fulfillment.
5. Write `draft_order.json` with `status=draft_pending_approval`.
6. Write `order_summary.md` and a customer confirmation draft.
7. Create an approval task before any official order confirmation.
8. Append action and approval logs.

## Safety Rules

- Never create a confirmed order directly.
- Always mark ambiguous products, quantities, prices, and customer identity as `needs_review`.
- Never reserve or deduct inventory.
- Never promise delivery dates without approval.
- Keep the raw source text in the draft for traceability.

## Outputs

- draft order JSON
- order summary Markdown
- customer confirmation draft
- approval task

## Resource Map

- Use `../../service/workers/message_processor.py` for the current WhatsApp queue implementation.
- Use `schemas/draft_order.schema.json` for draft order output.
- Use `templates/order_summary.md` for summaries.
