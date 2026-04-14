# Stage 3 — Confirmed Reservation Processing (MCP)

This folder contains Stage 3 non-code artifacts and notes.

Stage 3 implementation code lives in:

- `app/stage3/mcp_server.py`
- `app/stage3/mcp_client.py`
- `app/stage2/webhook_app.py` (integration point after admin confirmation)

## Goal

After admin confirms a reservation, write reservation details into persistent text storage via MCP-like service.

Required line format:

`Name | Car Number | Reservation Period | Approval Time`

## Run

Start Stage 3 MCP-like server:

```bash
uvicorn app.stage3.mcp_server:app --host 0.0.0.0 --port 9191
```

## Security and reliability

- Header-based API key authentication (`X-API-Key`)
- Reject unauthorized requests (`401`)
- Retry/backoff in MCP client
- Thread-safe append on server side

## Stage 3 tests

```bash
python -m pytest -m stage3 -v
```
