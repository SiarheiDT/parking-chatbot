# Stage 3 — Terraform

This Terraform stack deploys the Stage 3 MCP server as a Docker container.

## What is provisioned

- Docker image reference for project runtime (`parking-chatbot:latest` by default)
- Docker container running `uvicorn app.stage3.mcp_server:app` on port `9191`
- Runtime environment variables required by Stage 3 server

## Files

- `main.tf` — provider + Docker resources
- `variables.tf` — stack inputs
- `outputs.tf` — container name and local URL outputs
- `terraform.tfvars.example` — required example input for API key

## Usage

```bash
cd stage_3/terraform
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars and set stage3_mcp_api_key
terraform init
terraform validate
terraform plan
terraform apply
```

## Notes

- This stack is Stage 3 only; do not place Stage 1/2/4 infrastructure here.
- Build `parking-chatbot:latest` image before `terraform apply` if image is not already present.
