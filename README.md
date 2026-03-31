# Parking Chatbot - Stage 1

Python chatbot for parking information and reservation requests, built with RAG and LangGraph orchestration.

## Stage 1 Scope

Implemented requirements for Stage 1:
- RAG-based chatbot architecture.
- Vector database integration (Weaviate).
- Interactive reservation flow (first name, last name, car plate, start/end datetime).
- Guardrails to block sensitive/private requests.
- Retrieval evaluation metrics (Recall@K, Precision@K, Hit Rate).
- Performance evaluation metrics (latency avg/p50/p95/max).
- Automated tests with `pytest`.
- CI and IaC artifacts (GitHub Actions + Terraform).

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
- LangChain
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
```

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

Current tests cover:
- router behavior
- reservation/cancellation flow
- DB repositories
- guardrails
- retriever structure

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
