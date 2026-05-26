# FF-ERP Render Deployment

日期：2026-05-26

## 部署目标

Render project：`FF-ERP`

Blueprint：`render.yaml`

第一阶段部署以下资源：

- `ff-erp-api`：WhatsApp webhook、SaaS 管理 API、审批 API。
- `ff-erp-mcp`：Codex MCP bridge HTTP service。
- `ff-erp-worker`：后台消息处理 worker。
- `ff-erp-daily-scheduler`：每日计划任务。
- `ff-erp-postgres`：共享 PostgreSQL 数据库。

## 为什么必须使用 Postgres

Render 的 Web Service、Worker、MCP Service 是独立容器。SQLite 文件不能在多个服务之间共享，也不能作为生产数据持久层。

因此线上部署必须设置 `DATABASE_URL`，由 Render Postgres 注入。

本地开发仍然可以不设置 `DATABASE_URL`，继续使用 `data/database/fferp.sqlite`。

## 部署步骤

1. 将本目录作为 Render 连接的 Git repository root。

2. 在 Render Dashboard 创建 Blueprint，选择 `render.yaml`。

3. Render 会创建 `FF-ERP` project 和 `production` environment。

4. 初次创建时填写这些 secret env vars：

```text
WHATSAPP_VERIFY_TOKEN
WHATSAPP_ACCESS_TOKEN
WHATSAPP_PHONE_NUMBER_ID
WHATSAPP_BUSINESS_ACCOUNT_ID
WHATSAPP_APP_SECRET
```

5. 部署完成后检查：

```bash
curl https://ff-erp-api.onrender.com/health
curl https://ff-erp-mcp.onrender.com/health
```

实际域名以 Render 控制台显示为准。

管理 API 和 MCP tools 需要 `FFERP_API_TOKEN`：

```bash
export FFERP_API_TOKEN=<Render ff-erp-api generated value>

curl https://ff-erp-api.onrender.com/status \
  -H "Authorization: Bearer $FFERP_API_TOKEN"

curl https://ff-erp-api.onrender.com/admin/whatsapp/config \
  -H "Authorization: Bearer $FFERP_API_TOKEN"

curl https://ff-erp-mcp.onrender.com/tools/list \
  -H "Authorization: Bearer $FFERP_API_TOKEN"
```

## Meta WhatsApp 配置

Callback URL：

```text
https://<ff-erp-api-domain>/webhook
```

Verify Token：

```text
Render 环境变量 WHATSAPP_VERIFY_TOKEN 的值
```

订阅字段：

```text
messages
```

`WHATSAPP_APP_SECRET` 设置后，API 会校验 Meta 的 `X-Hub-Signature-256`。这应在生产保持开启。

## Codex MCP 调用入口

第一阶段 MCP bridge 提供：

```text
GET  /tools/list
POST /tools/call
```

可用工具：

```text
fferp.status
fferp.pending_tasks
fferp.pending_approvals
fferp.inbox_messages
fferp.process_one_task
```

调用示例：

```bash
curl -X POST https://<ff-erp-mcp-domain>/tools/call \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $FFERP_API_TOKEN" \
  -d '{"tool":"fferp.inbox_messages","arguments":{"limit":20}}'
```

## 当前安全边界

已完成：

- PostgreSQL 共享数据层。
- Meta webhook app secret 签名校验。
- Render secret env vars 不写入源码。
- `FFERP_API_TOKEN` 保护管理 API 和 MCP tools。
- 审批 payload 写入 DB，避免依赖 worker 本地草稿文件。

下一阶段必须完成：

- Admin Console 登录和组织权限。
- MCP OAuth/JWT 鉴权，替换第一阶段 Bearer token。
- tenant_id 在所有业务表和查询中的强制隔离。
- Stripe Billing webhook。
- WhatsApp outbound outbox 和发送状态追踪。

在上述安全能力完成前，`ff-erp-mcp` 不应公开给不受信任用户。
