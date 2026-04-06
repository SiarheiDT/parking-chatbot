# Stage 2 — Terraform (admin service)

Use this directory for **infrastructure as code** that targets the **human-in-the-loop / admin** component, for example:

- Container / VM for a small **FastAPI** approve/reject API  
- Optional: managed email relay, secrets, or networking rules  

The existing **`infra/terraform/local/`** in the repo root remains focused on **Weaviate** (Stage 1 RAG). This folder now contains a separate Terraform stack for Stage 2 admin webhook runtime.

## Conventions

- Name resources with a clear prefix (e.g. `parking_admin_*`).
- Keep secrets in `terraform.tfvars` (local only), not in git.
- Use `terraform.tfvars.example` as onboarding template.

## Included stack

This stack deploys one Docker container for Stage 2 admin webhook service:

- image: `parking-chatbot:latest` (override via variable)
- command: `uvicorn app.stage2.webhook_app:app --host 0.0.0.0 --port 9090`
- env wiring: DB path, Telegram credentials, Stage 2 handler mode, optional OpenAI key

## Prerequisites

- Docker daemon available locally
- Terraform CLI 1.5+ (or run official Terraform Docker image for checks)
- Built image that contains project code and dependencies:

```bash
docker build -t parking-chatbot:latest .
```

## Usage

```bash
cd stage_2/terraform
cp terraform.tfvars.example terraform.tfvars
# edit secrets/values
terraform init
terraform validate
terraform plan
terraform apply
```

Destroy:

```bash
terraform destroy
```

## Verified checks (without local Terraform install)

If Terraform is not installed on your machine, you can run checks via Docker:

```bash
docker run --rm -v "$PWD:/work" -w /work hashicorp/terraform:1.9.8 fmt -check
docker run --rm -v "$PWD:/work" -w /work hashicorp/terraform:1.9.8 init -backend=false
docker run --rm -v "$PWD:/work" -w /work hashicorp/terraform:1.9.8 validate
docker run --rm -v "$PWD:/work" -w /work hashicorp/terraform:1.9.8 plan -var-file=terraform.tfvars.example
```
