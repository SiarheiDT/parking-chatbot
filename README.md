# 🚗 Parking Chatbot (RAG + Evaluation + Production-Ready Architecture)

## Overview

This project implements a **production-ready Parking Chatbot** using:
- Retrieval-Augmented Generation (RAG)
- Vector search (Weaviate)
- Guardrails (input/output filtering)
- Evaluation pipeline (retrieval metrics)
- Automated tests and CI

The chatbot supports:
- FAQ answering
- Parking information retrieval
- Reservation flow handling

---

## Architecture

```
User → Router → (RAG | Reservation Flow | Guardrails)
                    ↓
              Retriever (Weaviate)
                    ↓
                Documents
```

---

## Tech Stack

- Python 3.10+
- Weaviate (vector DB)
- Sentence Transformers (embeddings)
- Pytest (testing)
- GitHub Actions (CI)

---

## Project Structure

```
app/
  chatbot/
  rag/
  db/
  guardrails/
  evaluation/

tests/
data/
docs/
docker/
infra/
```

---

## Features

### 1. RAG Pipeline
- Document ingestion
- Embedding generation
- Vector retrieval
- Context-based answering

### 2. Guardrails
- Sensitive data detection
- Request filtering

### 3. Reservation Flow
- Structured user interaction
- Data collection (name, plate, time)

### 4. Evaluation
- Recall@K
- Precision@K
- Hit Rate

### 5. Tests
- Unit tests
- Integration tests

---

## How to Run

### 1. Setup

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Start Weaviate

```
docker compose up -d
```

### 3. Ingest Data

```
python -m app.rag.ingest
```

### 4. Run Chatbot

```
python -m app.main
```

---

## Evaluation

```
python -m app.evaluation.retrieval_eval
```

Example metrics:
- Recall@K ≈ 0.87
- Hit Rate ≈ 0.88

---

## Testing

```
pytest -v
```

---

## CI

GitHub Actions runs:
- tests
- lint checks

---

## Key Design Decisions

- Separation of concerns (RAG / Router / Guardrails)
- Vector DB abstraction
- Evaluation-first approach
- Clean repo (no env / no DB files)

---

## Improvements (Next Steps)

- Add LLM-based evaluation (RAGAS)
- Add streaming responses
- Add UI (FastAPI + frontend)
- Add caching layer

---

## Author

Siarhei Kandrashevich
