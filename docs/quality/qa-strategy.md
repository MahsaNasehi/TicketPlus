# Quality Assurance Strategy

## Objectives

TicketPlus quality is measured first by purchase integrity, then by reliability,
security, performance, and maintainability. A release is unacceptable if two
buyers can confirm the same event seat, even when every availability target is
met.

## Quality Gates

| Gate | Merge-request requirement | Release requirement |
|---|---|---|
| Unit tests | All pass; changed business logic covered | All pass from immutable release commit |
| Reservation coverage | At least 90% line and 85% branch | No decrease from approved baseline |
| Other service coverage | At least 80% line and 75% branch | No unexplained decrease |
| Mutation testing | Changed reservation/payment logic has at least 80% mutation score | Full critical-module score at least 85% |
| Contract tests | Provider and consumer contracts pass | Deployed contract versions are compatible |
| Integration tests | PostgreSQL, Redis, and Kafka paths pass | Compensation and replay scenarios pass |
| Security | No committed secrets or unresolved critical/high vulnerabilities | Threat-model controls verified |
| IaC and diagrams | Terraform validates; PlantUML renders | Artifacts match release architecture |
| Load and stress | Smoke scenario on merge when environment exists | Planned peak plus 50% headroom passes |

Exceptions require a tracked risk, owner, expiry date, and approval from QA and
the relevant technical owner. Double-booking, payment duplication, authorization
bypass, and data-loss failures cannot be waived.

## Test Levels

### Unit and Property Tests

- Seat-state transitions reject illegal paths and expired owners.
- Lock release compares ownership tokens before deleting.
- Money calculations use decimal arithmetic and preserve currency.
- Payment commands reuse the same idempotency key.
- Event consumers produce the same result when a message is delivered twice.
- Property-based tests generate interleavings of lock, expire, pay, confirm, and
  cancel commands and assert at most one confirmed owner per event seat.

### Component and Integration Tests

Each service runs against disposable real dependencies in CI. Reservation tests
use PostgreSQL and Redis; asynchronous workflows use Kafka-compatible test
containers. Tests verify transaction boundaries, uniqueness constraints, TTL
behavior, outbox publication, consumer inbox handling, migrations, and rollback.

### Contract Tests

OpenAPI schemas define synchronous APIs and versioned JSON/Avro schemas define
events. Consumer-driven tests cover the API Gateway, Checkout-to-Reservation,
payment adapter, and notification provider. Removing or changing a required
field requires a new contract version and a compatibility window.

### End-to-End Tests

The critical journey covers authentication, queue admission, event discovery,
seat lock, payment success, reservation confirmation, ticket issuance, and
notification. Failure journeys cover lock conflict, TTL expiry, user
cancellation, definitive payment rejection, ambiguous timeout, duplicate event,
and provider outage.

## Reservation Integrity Oracle

Every concurrency test finishes with authoritative database queries that assert:

1. At most one confirmed reservation exists per `(event_id, seat_id)`.
2. Every booked seat has exactly one confirmed reservation.
3. Every successful charge maps to one confirmed order or an explicit refund.
4. No expired/cancelled reservation retains a live lock after the cleanup window.
5. Every issued ticket maps to one successful payment and one booked seat.

HTTP response counts alone are insufficient evidence because a race can return
success before a conflicting transaction commits.

## Test Data and Environments

- Factories create synthetic users, venues, seats, events, and tokenized payment
  references; production personal or card data is forbidden.
- Tests use unique run IDs and remove only their own data.
- CI dependencies are ephemeral and version-aligned with production.
- Performance environments use production-like limits and isolated load-agent
  capacity so the generator is not the bottleneck.
- Clocks are injectable for TTL and saga tests; distributed tests record clock
  skew and use server timestamps for assertions.

## Defect Management

| Severity | Definition | Release impact |
|---|---|---|
| Blocker | Double booking, duplicate charge, security bypass, unrecoverable loss | Stop release and affected sales |
| Critical | Critical journey unavailable without workaround | Stop release |
| Major | Material degradation with safe workaround | Product/QA approval required |
| Minor | Limited impact outside critical flow | May defer with owner and due date |

Each defect contains environment, build SHA, correlation ID, exact steps, actual
and expected result, impact, logs/traces, and regression-test location.

## Traceability

Test cases reference the relevant backlog story and architectural artifact.
Pipeline reports are retained with the commit SHA. The release summary records
coverage, mutation score, performance results, unresolved defects, accepted
risks, and approving roles.

