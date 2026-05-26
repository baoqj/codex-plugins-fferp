---
name: fferp-delivery-dispatcher
description: Generate delivery orders, warehouse instructions, and customer delivery notice drafts for approved FFERP sales orders. Use when Codex needs dispatch documents, warehouse picking instructions, driver handoff notes, delivery notice drafts, or shipment approval workflows.
---

# FFERP Delivery Dispatcher

## Workflow

1. Load an approved sales order and customer delivery details.
2. Validate warehouse, SKU, quantity, address, and delivery constraints.
3. Generate delivery order Markdown.
4. Generate warehouse instruction text.
5. Generate customer delivery notice draft.
6. Create approval or warehouse confirmation task before marking anything shipped.
7. Append action and approval logs.

## Safety Rules

- Only operate on approved sales orders.
- Never mark an order shipped automatically.
- Never promise delivery arrival time without approval.
- Keep warehouse confirmation separate from customer notification.

## Outputs

- delivery order Markdown
- warehouse instruction text
- customer delivery notice draft
- approval or confirmation task

## Resource Map

- Use `schemas/delivery_dispatch.schema.json` for dispatch output.
- Use `templates/delivery_order.md` for generated documents.
