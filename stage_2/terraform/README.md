# Stage 2 — Terraform (admin service)

Use this directory for **infrastructure as code** that targets the **human-in-the-loop / admin** component, for example:

- Container / VM for a small **FastAPI** approve/reject API  
- Optional: managed email relay, secrets, or networking rules  

The existing **`infra/terraform/local/`** in the repo root can remain focused on **Weaviate** (Stage 1 RAG). Splitting avoids mixing unrelated resources.

## Conventions

- Name resources with a clear prefix (e.g. `parking_admin_*`).
- Document required variables in `variables.tf` and copy a `terraform.tfvars.example` when you add real `.tf` files.

When you add `.tf` files, update the root **`README.md`** Stage 2 section with `terraform init/plan/apply` instructions from this folder.
