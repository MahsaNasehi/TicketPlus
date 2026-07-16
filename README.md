# TicketPlus Architecture Project

TicketPlus is a design and operations package for a scalable event-ticketing
platform. It covers concurrency-safe seat reservation, payment compensation,
asynchronous fulfillment, Kubernetes deployment, infrastructure provisioning,
quality assurance, and production incident handling.

## Repository Map

| Area | Location |
|---|---|
| UML sources | [`diagrams/`](diagrams/) |
| Rendered UML | [`rendered/`](rendered/) |
| Production architecture and incidents | [`docs/architecture-and-operations/`](docs/architecture-and-operations/) |
| QA, load, mutation, and coverage policy | [`docs/quality/`](docs/quality/) |
| Executable load scenarios | [`quality/load/`](quality/load/) |
| Team roles and engineering standards | [`docs/project-governance/`](docs/project-governance/) |
| Terraform infrastructure | [`infra/terraform/`](infra/terraform/) |
| Contribution and review workflow | [`CONTRIBUTING.md`](CONTRIBUTING.md) |
| Submission status | [`docs/submission-checklist.md`](docs/submission-checklist.md) |

Product Vision, Risk Analysis, and Jira artifacts are maintained by the project
team and must be added before final packaging. The checklist deliberately marks
them as external rather than claiming incomplete placeholder documents.

## Validation

GitLab CI validates Markdown, renders PlantUML, formats and validates Terraform,
runs service tests when their runtime manifests exist, scans for security issues,
and supports scheduled mutation and load-test jobs. Load tests require an
isolated deployed test environment and protected CI variables.

Terraform commands and deployment boundaries are documented in
[`infra/terraform/README.md`](infra/terraform/README.md). Do not run
`terraform apply` without an approved AWS account and cost review.

