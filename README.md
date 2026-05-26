# FFERP Codex Plugin Suite

FFERP is a Codex-powered, skill-based, file-first ERP automation layer. It helps turn messy business files, WhatsApp messages, orders, inventory, delivery work, and payment follow-up into recordable, approvable, traceable, and gradually automated ERP workflows.

FFERP does not try to make Codex replace an ERP. It uses Codex Skills for business workflow knowledge, local scripts for deterministic file and database work, and a persistent backend service for 7x24 WhatsApp intake and task processing under human approval control.

This first implementation provides:

- Codex Skill folders for the main FFERP workflows.
- A FastAPI webhook service for official WhatsApp Cloud API webhooks.
- SQLite-backed task and approval queues.
- JSONL append-only audit logs.
- A worker that classifies messages and creates draft replies, draft orders, and approval tasks.
- A dry-run WhatsApp sender helper that can be enabled only after human approval.

## Install From GitHub

Install into a local Codex plugins folder:

```bash
mkdir -p ./codex/plugins
git clone https://github.com/baoqj/codex-plugins-fferp.git ./codex/plugins/fferp
cd ./codex/plugins/fferp
```

If you prefer a global Codex plugin location, clone to `~/.codex/plugins/fferp` instead.

Download without Git:

```bash
mkdir -p ./codex/plugins
curl -L https://github.com/baoqj/codex-plugins-fferp/archive/refs/heads/main.zip -o fferp.zip
unzip -q fferp.zip
mv codex-plugins-fferp-main ./codex/plugins/fferp
cd ./codex/plugins/fferp
```

The repository root is the plugin root. It contains `.codex-plugin/plugin.json` and `skills/`, so it can be copied directly under `./codex/plugins/fferp`.

## Architecture

```text
Codex Skills
  -> business knowledge and workflow rules
Local Scripts
  -> Excel, CSV, PDF, SQLite, JSONL, reports
FastAPI Service
  -> WhatsApp webhook and approval API
Worker Queue
  -> background task processing
SQLite / JSONL
  -> structured records and audit logs
Approval System
  -> human confirmation and risk control
MCP Bridge
  -> Codex-facing interaction with FFERP backend
```

## 7x24 Runtime Model

Codex CLI is not the production daemon. The always-on path is:

```text
WhatsApp Cloud API
  -> HTTPS Webhook
  -> FFERP FastAPI service
  -> raw JSONL log and raw payload file
  -> SQLite task queue
  -> worker processor
  -> draft reply/order/approval task
  -> human approval
  -> WhatsApp Send Message API
```

Codex is used to maintain the system, inspect logs, improve skills, and invoke manual workflows.

## Local Python Start

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m scripts.common.bootstrap_data
uvicorn service.api.whatsapp_webhook:app --host 0.0.0.0 --port 8000
```

In another terminal:

```bash
. .venv/bin/activate
python -m service.workers.message_processor --loop
```

For Meta webhook testing, expose the FastAPI service with a real HTTPS endpoint such as Cloudflare Tunnel or ngrok.

## Long-Running Docker Mode

```bash
cp .env.example .env
# edit .env with Meta WhatsApp Cloud API credentials
docker compose up -d
```

Services:

- `fferp-api`: WhatsApp webhook and approval API on port `8000`.
- `fferp-worker`: task queue worker.
- `fferp-scheduler`: scheduled report/payment/receivable jobs.
- `fferp-file-watcher`: `data/inbox/` polling watcher.
- `fferp-mcp`: local Codex interaction bridge on port `8765`.

## Render SaaS Deployment

The first SaaS deployment target is Render project `FF-ERP`.

Use `render.yaml` from this repository root to create the Blueprint. It provisions:

- `ff-erp-api`
- `ff-erp-mcp`
- `ff-erp-worker`
- `ff-erp-daily-scheduler`
- `ff-erp-postgres`

The production services share Render Postgres through `DATABASE_URL`. Local development keeps using SQLite when `DATABASE_URL` is not set.

See `docs/render-deployment.md` for the deployment checklist and required Meta WhatsApp environment variables.

## Direct Codex-Style Commands

These commands back the common direct Codex requests:

```bash
python -m scripts.orders.extract_from_whatsapp --date 2026-05-26
python -m scripts.payments.reconcile_bank_csv --bank-csv data/inbox/bank.csv --receivables-csv data/transactions/receivables.csv
python -m scripts.reports.generate_today_report --date 2026-05-26
```

Example user prompts:

```text
Use fferp-order-extractor to extract orders from today's WhatsApp messages.
Use fferp-payment-reconciler to match this bank CSV with receivables.
Use fferp-report-generator to generate today's sales and inventory report.
```

## WhatsApp Business Cloud API

1. Create or open a Meta Developer App and add WhatsApp.
2. Get `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_BUSINESS_ACCOUNT_ID`, a production `WHATSAPP_ACCESS_TOKEN`, and `WHATSAPP_APP_SECRET`.
3. Set a strong `WHATSAPP_VERIFY_TOKEN` in `.env`.
4. Start FFERP with `docker compose up -d`.
5. Expose `fferp-api` with a public HTTPS endpoint, for example Cloudflare Tunnel:

   ```bash
   cloudflared tunnel --url http://localhost:8000
   ```

6. In Meta Webhooks, set callback URL to:

   ```text
   https://your-public-domain.example/webhook
   ```

7. Set the same verify token from `.env` and subscribe to the WhatsApp `messages` field.
8. Send a test WhatsApp message to the business number and confirm:

   ```bash
   curl http://localhost:8000/status
   curl http://localhost:8000/approvals/pending
   ```

Keep `FFERP_WHATSAPP_SEND_ENABLED=false` until webhook intake, queue processing, drafts, and approval review are verified end to end.

## Safety

The worker only creates drafts and approval records. It does not confirm orders, deduct stock, confirm payments, promise refunds, or send high-risk WhatsApp messages without approval.
