# AGENTS.md

## Project

FFERP is a Codex-powered ERP automation system for file-first sales operations and WhatsApp order intake.

## Working Rules

- Prefer Python for data processing and automation.
- Use FastAPI for service endpoints.
- Use SQLite for local queue and approval state.
- Use JSONL for append-only audit logs.
- Keep Excel files as business-user-readable data sources.
- Never overwrite original files.
- Always create cleaned or generated copies.
- Always write logs for AI actions and service actions.
- Always add tests for core scripts.
- Keep humans in control of risky business operations.

## Business Safety Rules

Never directly execute these without approval:

- confirmed order creation
- official inventory deduction
- payment confirmation
- refund
- discount approval
- credit approval
- delivery commitment
- complaint settlement
- mass messaging
- deleting records

## WhatsApp Rules

- Use official WhatsApp Business Cloud API.
- Do not use unofficial WhatsApp Web scraping for production.
- Save raw webhook payloads before processing.
- Deduplicate messages by `message_id`.
- Generate drafts before sending.
- Only send messages when approved or explicitly configured as low-risk auto-reply.

## Output Rules

Every workflow should produce:

- structured JSON result
- human-readable Markdown summary
- log entry
- approval task when risk or business impact requires review
