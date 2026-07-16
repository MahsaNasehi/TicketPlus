# Contributing to TicketPlus

## Workflow

1. Create a Jira issue with acceptance criteria and link it to an epic.
2. Branch from the protected default branch using
   `feature/TICKET-123-short-description`, `fix/...`, or `docs/...`.
3. Keep commits focused and use imperative subjects, for example
   `Prevent expired reservation confirmation`.
4. Add or update tests and documentation with the behavior change.
5. Open a merge request using the repository template and link the Jira issue.
6. Resolve pipeline failures and all reviewer comments before approval.
7. Squash merge after required approvals; direct pushes to protected branches
   are forbidden.

## Definition of Ready

- User value and acceptance criteria are clear.
- Dependencies, security implications, and affected service owner are known.
- API/event/schema changes identify consumers and compatibility strategy.
- The work is small enough to complete and verify within one sprint.

## Definition of Done

- Acceptance criteria and negative paths are verified.
- Unit, integration, contract, and relevant concurrency tests pass.
- Coverage and mutation thresholds meet
  [`docs/quality/mutation-and-coverage.md`](docs/quality/mutation-and-coverage.md).
- API, event, schema, UML, runbook, and decision documentation is current.
- Logs/metrics contain correlation data without secrets or personal information.
- Database changes are backward-compatible and have a rollback plan.
- CI, security scans, and required performance tests pass.
- Reviewer comments are resolved and evidence is attached to the Jira issue.

## Review Standards

At least one domain owner approves ordinary changes. Reservation, Checkout,
identity, payment, infrastructure, and data migrations require two approvals,
including the relevant specialist. Authors cannot approve their own changes.

Reviewers prioritize correctness, security, compatibility, failure handling,
observability, test quality, and operational impact. Style-only feedback is
clearly marked nonblocking. Critical findings remain open until code and tests
demonstrate the resolution.

## Architecture Changes

A short architecture decision record is required when a change introduces a
service, datastore, external provider, cross-domain dependency, public contract,
new consistency model, or material security/availability tradeoff. The record
states context, decision, alternatives, consequences, and rollback/migration.

## Sensitive Data

Never commit credentials, tokens, real customer data, card data, Terraform state,
or production logs. Use synthetic fixtures and protected CI variables. If a
secret is exposed, revoke it immediately and follow the incident process; Git
history rewriting alone is not remediation.

