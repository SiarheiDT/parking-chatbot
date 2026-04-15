# Stage 4 — Unified LangGraph Orchestration

This folder contains Stage 4 non-code artifacts and notes.

Stage 4 implementation code lives in:

- `app/stage4/orchestrator.py` (unified LangGraph pipeline)
- `app/stage4/service.py` (API endpoint to run pipeline)
- `app/stage4/load_test.py` (load test helper for Stage 4 runtime checks)

## Graph nodes

- `user_interaction` — chat context + optional reservation intake
- `admin_approval` — applies confirmation/rejection decision
- `data_recording` — persists confirmed reservation through Stage 3 MCP client

## Pipeline behavior

1. User interaction is processed.
2. If reservation + admin decision are provided, system runs admin approval.
3. If status becomes `confirmed`, reservation is sent to MCP persistence.

## Architecture and logic

- Orchestrator is implemented with LangGraph and explicit conditional edges.
- Stage 4 API exposes one endpoint that executes the full graph state machine.
- Recording step delegates to Stage 3 MCP client, keeping write path isolated.

## Setup and run

Run unified Stage 4 API:

```bash
uvicorn app.stage4.service:app --host 0.0.0.0 --port 9292
```

Run a local load smoke check:

```bash
python - <<'PY'
from app.stage4.load_test import run_stage4_load_test
print(run_stage4_load_test(total_requests=20, workers=4, mode="chat_only"))
print(run_stage4_load_test(total_requests=20, workers=4, mode="confirm_flow"))
PY
```

## Run tests

```bash
python -m pytest -m stage4 -v
```

## Deployment guideline (minimal)

- Keep Stage 4 API and Stage 3 MCP server as separate services.
- Configure env values in one place (`.env`) and inject via runtime env.
- Expose Stage 4 behind HTTPS reverse proxy when deployed externally.

## Related stages

- Stage 1: chatbot/RAG flow
- Stage 2: human-in-the-loop admin decision
- Stage 3: MCP recording service

## Terraform (Stage 4 only)

Stage 4 infrastructure IaC is now in `stage_4/terraform/` and deploys unified orchestration API as Docker container.
