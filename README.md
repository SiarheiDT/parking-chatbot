# Parking Chatbot - Stage 1

Python chatbot for parking information and reservation requests, built with RAG and LangGraph orchestration.

## Stage 1 Scope

Implemented requirements for Stage 1:
- RAG-based chatbot architecture.
- Vector database integration (Weaviate).
- Interactive reservation flow (first name, last name, car plate, start/end datetime).
- Guardrails: regex for structured PII-style patterns plus semantic analysis with a pre-trained SentenceTransformer (`EMBEDDING_MODEL_NAME`) against sensitive-intent reference phrases; phrase matching for private/internal requests.
- Retrieval evaluation metrics (Recall@K, Precision@K, Hit Rate).
- Performance evaluation metrics (latency avg/p50/p95/max).
- Automated tests with `pytest`.
- CI and IaC artifacts (GitHub Actions + Terraform).

## Stage 2 (artifacts layout)

- **Code** for Stage 2 will live under the shared **`app/`** package (same repo as Stage 1).
- **Non-code** materials: **`stage_2/`** — see [`stage_2/README.md`](stage_2/README.md) for scenarios, and subfolders **`stage_2/docs/`** (presentation / diagrams) and **`stage_2/terraform/`** (IaC for the admin-facing service).

## Architecture

```
User
  -> LangGraph Router
      -> Guardrails
      -> Intent routing
          -> Info flow (SQL dynamic data + RAG retrieval from Weaviate)
          -> Reservation flow (store request with pending status)
          -> Cancellation flow (cancel upcoming reservation by car plate)
```

## Tech Stack

- Python 3.10+
- LangChain (text splitters + optional Stage 2 admin tool-calling agent)
- LangGraph
- Weaviate
- Sentence Transformers (`all-MiniLM-L6-v2`)
- SQLite
- Pytest
- GitHub Actions
- Terraform

## Project Structure

```
app/
  chatbot/      # routing and dialog flows
  rag/          # embeddings, vector store, ingestion, retrieval
  db/           # sqlite schema and repository layer
  guardrails/   # request filtering
  notifications/# Stage 2 Telegram (admin alerts)
  stage2/       # Stage 2 FastAPI webhook for Telegram callbacks
  evaluation/   # retrieval and latency evaluation scripts
tests/
data/
docker/
infra/
```

## Run (Linux/WSL Recommended)

### 1) Install and activate environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`.env.example` is a committed template, and `.env` is your local runtime configuration file.

### 2) Start Weaviate

```bash
docker compose -f docker/weaviate-compose.yml up -d
```

### 3) Ingest knowledge base

```bash
python -m app.rag.ingest
```

### 4) Start chatbot

```bash
python -m app.main
```

### Stage 2 — Admin Telegram webhook (optional)

Set `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ADMIN_CHAT_ID`, and a strong `TELEGRAM_WEBHOOK_SECRET` in `.env`. After a user completes a reservation, the admin receives a Telegram message with **Confirm** / **Reject** buttons.

**Admin decision handler** (`STAGE2_ADMIN_HANDLER` in `.env`):

- `direct` (default): webhook updates SQLite and Telegram immediately — best for CI and when no LLM key is available.
- `langchain_tools` (aliases: `langchain`, `agent`, `tools`): a **second LangChain agent** (OpenAI tool-calling) runs the same steps via tools (`get_reservation_details`, `apply_admin_decision`, `finalize_telegram_callback`). Set `OPENAI_API_KEY` and optionally `ADMIN_AGENT_MODEL` (defaults to `MODEL_NAME`). If the key is missing or the agent raises, the webhook **falls back** to `direct`. Set `ADMIN_AGENT_VERBOSE=true` for executor logging.

Run the webhook server (separate terminal; requires a **public HTTPS** URL for production — use [ngrok](https://ngrok.com/) locally):

```bash
uvicorn app.stage2.webhook_app:app --host 0.0.0.0 --port 9090
```

Register the webhook with Telegram (replace placeholders):

`https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook?url=https://<your-host>/telegram/webhook/<TELEGRAM_WEBHOOK_SECRET>`

More detail: [`stage_2/README.md`](stage_2/README.md).

## Evaluation

### Retrieval metrics

```bash
python -m app.evaluation.retrieval_eval
```

Output:
- `data/eval/retrieval_eval_report.json`
- Includes `avg_recall_at_k`, `avg_precision_at_k`, `hit_rate`.

### Latency metrics

```bash
python -m app.evaluation.latency_eval
```

Output:
- `data/eval/latency_eval_report.json`
- Includes `avg_latency_ms`, `p50_latency_ms`, `p95_latency_ms`, `max_latency_ms`.

## Testing

Run all tests:

```bash
python -m pytest -v
```

Run **Stage 1** only (chatbot, RAG, DB, guardrails, evaluation helpers):

```bash
python -m pytest -m stage1 -v
```

Run **Stage 2** only (Telegram notifications, webhook, LangChain admin tools):

```bash
python -m pytest -m stage2 -v
```

Markers are defined in `pytest.ini` (`stage1`, `stage2`).

Current tests cover:
- router behavior
- reservation/cancellation flow
- DB repositories
- guardrails
- retriever structure
- Stage 2 Telegram webhook and admin agent tools

## CI/CD and IaC

- CI workflow: `.github/workflows/ci.yml`
  - dependency install
  - test run
- Terraform workflow: `.github/workflows/terraform.yml`
  - `terraform fmt`, `init`, `validate`
- Local Terraform example: `infra/terraform/local/`

## Submission Checklist (Stage 1)

- [ ] Repository link is ready (GitHub or EPAM GitLab).
- [ ] Weaviate is running and ingestion completed successfully.
- [ ] Chatbot starts and handles info + reservation + cancellation flows.
- [ ] Guardrails block private/sensitive requests.
- [ ] Retrieval evaluation report exists: `data/eval/retrieval_eval_report.json`.
- [ ] Latency evaluation report exists: `data/eval/latency_eval_report.json`.
- [ ] Tests pass locally: `python -m pytest -v`.
- [ ] CI workflows are present and valid.
- [ ] README is up to date (setup, run, evaluation, structure).
- [ ] Optional bonus artifacts prepared (presentation/screenshots).

## Author

Siarhei Kandrashevich
