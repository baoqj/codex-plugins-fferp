# Connect WhatsApp Business Cloud API

## Required Meta Values

Configure these in `.env`:

```bash
WHATSAPP_VERIFY_TOKEN=your-random-verify-token
WHATSAPP_ACCESS_TOKEN=your-system-user-access-token
WHATSAPP_PHONE_NUMBER_ID=your-phone-number-id
WHATSAPP_BUSINESS_ACCOUNT_ID=your-waba-id
WHATSAPP_APP_SECRET=your-meta-app-secret
WHATSAPP_GRAPH_API_VERSION=v25.0
FFERP_WHATSAPP_SEND_ENABLED=false
```

Use a long-lived system user access token for production. Do not commit `.env`.

## Start FFERP

```bash
docker compose up -d
curl http://localhost:8000/health
curl http://localhost:8765/health
```

## Expose Webhook

Meta requires public HTTPS for webhooks. For testing:

```bash
cloudflared tunnel --url http://localhost:8000
```

Use the generated HTTPS URL as:

```text
https://your-tunnel-domain.example/webhook
```

In Meta Webhooks, configure:

- Callback URL: `https://your-tunnel-domain.example/webhook`
- Verify Token: same value as `WHATSAPP_VERIFY_TOKEN`
- Subscribe field: `messages`

## Verify

Send a WhatsApp message to the business number. Then check:

```bash
curl http://localhost:8000/status
curl http://localhost:8000/tasks/pending
curl http://localhost:8000/approvals/pending
```

Expected flow:

```text
Webhook payload
  -> data/inbox/whatsapp/*.json
  -> data/logs/whatsapp_log.jsonl
  -> SQLite tasks
  -> worker draft
  -> approval task
```

## Sending

The sender is dry-run by default:

```bash
python -m scripts.whatsapp.send_message --to 15551234567 --text "Approved reply"
```

Only send after approval:

```bash
FFERP_WHATSAPP_SEND_ENABLED=true python -m scripts.whatsapp.send_message --to 15551234567 --text "Approved reply" --send
```

Production sending must also satisfy WhatsApp template, session-window, opt-in, and business policy requirements.
