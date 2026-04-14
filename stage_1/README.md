# Stage 1 — RAG Chatbot

This folder contains Stage 1 non-code artifacts and notes.

Stage 1 implementation code lives in:

- `app/chatbot/`
- `app/rag/`
- `app/guardrails/`
- `app/db/`
- `app/evaluation/`

## Stage 1 scope

- LangGraph-based user chat flow
- RAG retrieval from Weaviate
- Reservation and cancellation user flows
- Guardrails (regex + semantic checks)
- Retrieval and latency evaluation scripts

## Run

```bash
python -m app.main
```

## Stage 1 tests

```bash
python -m pytest -m stage1 -v
```

## Stage 1 Terraform

Stage 1 IaC is intentionally separated in:

- `infra/terraform/local/` (Weaviate local stack)
