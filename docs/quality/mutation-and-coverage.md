# Mutation Testing and Coverage Policy

## Purpose

Coverage shows which code executed; mutation testing shows whether assertions
detect incorrect behavior. Both are mandatory for Reservation and transactional
Checkout modules because shallow tests can execute a lock or compensation branch
without proving its invariant.

## Tool Selection

Use the mutation engine matching each service implementation:

| Runtime | Mutation tool | Coverage tool |
|---|---|---|
| Java/Kotlin | PIT | JaCoCo |
| JavaScript/TypeScript | StrykerJS | Istanbul/nyc |
| Python | mutmut or Cosmic Ray | coverage.py |
| .NET | Stryker.NET | coverlet |

The repository does not prescribe a service language. Each service must commit
its tool configuration and expose standard `test`, `coverage`, and `mutation`
commands before implementation is merged.

## Scope and Thresholds

- Run changed-file mutation analysis on every Reservation or Checkout merge
  request; run the full suite nightly and before release.
- Critical modules require at least 90% line, 85% branch, and 85% mutation score.
- Other domain modules require at least 80% line, 75% branch, and 70% mutation.
- Exclusions are limited to generated code, declarative configuration, DTO
  accessors, and unreachable defensive adapters. Every exclusion is documented.
- Surviving mutants in lock ownership, expiry comparisons, uniqueness checks,
  amount/currency, idempotency, saga compensation, or authorization block merge.

## Required Mutation Classes

Tests must kill mutations that:

- Remove `NX`/ownership conditions or invert lock success.
- Change `< expiresAt` to `<=`, `>` or an unconditional result.
- Remove the confirmed-seat uniqueness constraint handling.
- Replace a payment idempotency key or retry an unknown result as a new charge.
- Skip a compensation command or acknowledge an event before durable processing.
- Remove event deduplication, version checks, or transaction rollback.
- Bypass role checks or accept an expired/incorrectly scoped token.

## Review and Reporting

CI publishes machine-readable coverage and mutation reports. Reviewers inspect
changed critical modules, surviving mutants, timeouts, and `no coverage` results.
Equivalent mutants may be excluded only with a code reference and reviewer
approval. The release record includes tool version, score by module, thresholds,
and all approved exclusions.

