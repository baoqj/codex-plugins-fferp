---
name: fferp-whatsapp-reply
description: Classify WhatsApp customer messages and generate FFERP reply drafts with risk levels and approval requirements. Use when Codex needs inquiry replies, quotation drafts, delivery-status responses, payment-note acknowledgements, complaint handling drafts, WhatsApp intent classification, or safe customer-service messaging.
---

# FFERP WhatsApp Reply

## Workflow

1. Read the normalized WhatsApp message and customer context.
2. Classify intent as inquiry, quotation_request, order_request, order_confirmation, delivery_status, payment_notice, complaint, after_sales, or unknown.
3. Assign risk level.
4. Draft a reply using templates under `templates/`.
5. Create an approval task for pricing, delivery promises, payment, complaints, refunds, compensation, unknown customers, and any medium/high-risk message.
6. Never send directly unless the payload has an approved flag and config allows the exact action.
7. Append WhatsApp and action logs.

## Safety Rules

- Never send messages directly by default.
- Never promise discount, delivery date, refund, compensation, legal position, or complaint settlement without approval.
- Preserve the incoming message ID and customer phone in every draft.
- Use official WhatsApp Cloud API only.

## Outputs

- reply draft text
- intent classification JSON
- risk level
- approval task when required

## Resource Map

- Use `../../service/api/whatsapp_webhook.py` for webhook intake.
- Use `../../scripts/whatsapp/send_message.py` only after approval.
- Use `schemas/reply_draft.schema.json` for output.
