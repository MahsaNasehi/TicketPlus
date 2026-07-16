# Engineering and Portability Standards

## Repository Organization

- `diagrams/` contains the baseline PlantUML architecture sources.
- `rendered/` contains reviewable vector exports of baseline diagrams.
- `docs/architecture-and-operations/` contains production design and incident
  artifacts.
- `docs/quality/` defines verification and release gates.
- `infra/terraform/` provisions cloud infrastructure.
- `quality/load/` contains executable performance scenarios.
- Future service directories own their source, tests, migrations, API/event
  schemas, container definition, and runbook.

Generated dependencies, credentials, reports, Terraform state, and local IDE
files are not committed. Generated reports are retained as CI artifacts.

## Service Standard

Every implemented service must provide:

1. A pinned, reproducible dependency manifest and lockfile.
2. A multi-stage container build that runs as a non-root user.
3. `/health/live`, `/health/ready`, and Prometheus metric endpoints.
4. Structured logs with trace/correlation IDs and data redaction.
5. Versioned OpenAPI and event schemas with compatibility tests.
6. Automated unit, integration, contract, coverage, and mutation commands.
7. Forward-compatible database migrations and a rollback/roll-forward plan.
8. Configuration through validated environment variables or mounted secrets.
9. A runbook describing dependencies, alerts, safe restart, and reconciliation.

## API and Event Rules

- APIs use explicit validation, stable error codes, pagination, and request IDs.
- Mutating requests accept an idempotency key where clients may retry.
- Dates use UTC ISO 8601; money uses integer minor units plus ISO currency.
- Events use past-tense business names, immutable facts, schema versions,
  aggregate versions, correlation IDs, and no sensitive payment data.
- Breaking changes require a new version and a migration window.

## Data and Security

- A context may not write another context's tables, cache keys, or event inbox.
- Database constraints enforce critical invariants in addition to application
  checks.
- Secrets come from protected stores/CI variables and are rotated.
- Least privilege applies to users, workloads, databases, brokers, and CI.
- Dependencies, images, Terraform, secrets, and source are scanned in CI.
- Audit records cover privileged configuration, pricing, refund, and ticket
  revocation actions.

## Environment Portability

Infrastructure is declared in Terraform and parameterized through variables.
Service containers must run identically on a developer machine, CI, and
Kubernetes; environment-specific values remain outside images. A complete
implementation adds a Compose file with health checks and seeded synthetic data
for PostgreSQL, Redis, Kafka, and services. No setup step may depend on an
unrecorded manual database edit or developer-specific path.

The current repository is an architecture and operations deliverable rather
than a service implementation. Therefore it does not claim a runnable local
application. The Terraform layer is documented in
[`../../infra/terraform/README.md`](../../infra/terraform/README.md), and CI
validates all committed executable artifacts.

## Documentation Standard

Documentation states owner, assumptions, decisions, failure behavior, and
verification where relevant. Diagrams and prose use consistent domain names.
Links are relative, examples contain no secrets, and meaningful behavior changes
update their diagrams/runbooks in the same merge request.

