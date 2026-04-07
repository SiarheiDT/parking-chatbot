# Stage 2 — Human-in-the-Loop (artifacts)

This folder is **non-code**: scenarios, screenshots, diagrams, and **Stage-2-only** Terraform for the admin-facing service.

All **Python implementation** lives under the shared package **`app/`** (same repository as Stage 1).

## Layout

| Path | Purpose |
|------|---------|
| `stage_2/README.md` | This file — how Stage 2 is documented and organized |
| `stage_2/docs/` | Presentation exports, architecture diagrams, sequence diagrams |
| `stage_2/terraform/` | IaC for the **admin** component (e.g. API / notifier), separate from `infra/terraform/local` for Weaviate if desired |
| *(optional)* `stage_2/screenshots/` | UI/API screenshots for the assignment (if you add this folder, reference it here) |

## Suggested demo scenarios (fill in as you implement)

1. User completes a reservation in the Stage 1 chat → row stored as `pending`.
2. Admin receives a notification (email / REST / messenger — per your implementation in `app/`).
3. Admin confirms or refuses → `reservations.status` updated accordingly.
4. *(Optional)* User is informed of the outcome (if you add this flow).

## Implementation steps (incremental)

1. **Done:** `app/db/repositories.py` — `save_reservation` returns new `id`; `get_reservation_by_id`, `list_pending_reservations`, `update_reservation_status` (`pending` → `confirmed` | `rejected`) for admin flow.
2. **Done:** `app/config.py` + `.env.example` — `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ADMIN_CHAT_ID`, optional `TELEGRAM_API_BASE`. `app/notifications/telegram.py` — `send_telegram_message` / `telegram_is_configured` (stdlib `urllib`, no extra deps).
3. **Done:** After `save_reservation`, `notify_admin_new_reservation` sends Telegram text + **Confirm / Reject** inline buttons. FastAPI webhook `app/stage2/webhook_app.py` — `POST /telegram/webhook/<TELEGRAM_WEBHOOK_SECRET>` handles `callback_query`, updates DB (`confirmed` / `rejected`), answers callback, clears keyboard. Run: `uvicorn app.stage2.webhook_app:app --host 0.0.0.0 --port 9090`.
4. **Done:** `app/stage2/admin_agent.py` — second LangChain admin agent with tools (`get_reservation_details`, `apply_admin_decision`, `finalize_telegram_callback`) enabled by `STAGE2_ADMIN_HANDLER=langchain_tools` with fallback to `direct`.
5. **Done:** Separate Terraform stack in `stage_2/terraform/` for Stage 2 admin webhook runtime (distinct from Stage 1 Weaviate Terraform in `infra/terraform/local/`).
6. **Done (Stage 3):** `app/stage3/mcp_server.py` and `app/stage3/mcp_client.py` — once reservation is confirmed, payload is sent to MCP-like service and appended to text storage (`Name | Car Number | Reservation Period | Approval Time`).

## Link to code

Implemented modules under `app/`:

- `app/stage2/admin_agent.py` — LangChain admin agent + tools
- `app/stage2/webhook_app.py` — FastAPI webhook for approve/reject callbacks
- `app/notifications/telegram.py` — Telegram client for notify/callback APIs

Run commands (to be updated when code exists):

- Stage 1 user chat: `python -m app.main`
- Stage 2 admin service: `uvicorn app.stage2.webhook_app:app --host 0.0.0.0 --port 9090`
- Stage 2 Terraform checks: `cd stage_2/terraform && terraform init && terraform validate && terraform plan`
- Stage 3 MCP server: `uvicorn app.stage3.mcp_server:app --host 0.0.0.0 --port 9191`
