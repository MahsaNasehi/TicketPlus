# Production Architecture and Operations

This package documents the production architecture and operational model for
TicketPlus. It extends the UML and infrastructure artifacts without requiring a
live production environment.

| Requirement | Artifact |
|---|---|
| Bounded contexts | [`bounded-contexts.md`](bounded-contexts.md), [`diagrams/bounded-context-map.puml`](diagrams/bounded-context-map.puml), [`rendered/bounded-context-map.svg`](rendered/bounded-context-map.svg) |
| Asynchronous messaging | [`asynchronous-messaging.md`](asynchronous-messaging.md), [`diagrams/async-transaction-flow.puml`](diagrams/async-transaction-flow.puml), [`rendered/async-transaction-flow.svg`](rendered/async-transaction-flow.svg) |
| Telemetry and monitoring | [`telemetry-and-monitoring.md`](telemetry-and-monitoring.md), [`diagrams/production-telemetry.puml`](diagrams/production-telemetry.puml), [`rendered/production-telemetry.svg`](rendered/production-telemetry.svg) |
| Incident management | [`incident-management.md`](incident-management.md) |
| Incident postmortems | [`postmortems/payment-gateway-outage.md`](postmortems/payment-gateway-outage.md), [`postmortems/waiting-room-failure.md`](postmortems/waiting-room-failure.md), [`postmortems/network-partition.md`](postmortems/network-partition.md) |

## Architecture Principles

- Each domain owns its data and business invariants.
- Synchronous calls are limited to interactions that need an immediate answer.
- Cross-domain state propagation uses versioned events and idempotent consumers.
- Availability favors safe degradation: the platform never sells a seat when
  ownership is uncertain.
- Alerts represent user-visible symptoms or exhausted safety margins, not every
  low-level fluctuation.
- Incident reviews are blameless and produce owned, time-bound corrective work.
