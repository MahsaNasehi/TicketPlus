# Isolating Service Boundaries

## Decision: Reservation Owns Availability

Seat geometry is stable venue configuration, but availability is a volatile
business state governed by locking, expiration, confirmation, and cancellation.
The **Reservation and Inventory** context therefore owns the authoritative seat
state machine:

`AVAILABLE -> LOCKED -> BOOKED`

A lock may return to `AVAILABLE` after expiry, payment failure, or cancellation.
Only the Reservation service can perform these transitions. The Catalog context
stores event metadata and a read-only availability projection for search. That
projection can be slightly stale, so the seat-map and checkout paths always
revalidate against Reservation.

Putting availability in Catalog would require Reservation to call Catalog while
Catalog also calls Reservation for fresh counts. This creates circular runtime
coupling and splits the overbooking invariant across two owners. The chosen
boundary removes both problems.

## Context Ownership

| Context | Owns | Does not own | Integration style |
|---|---|---|---|
| Identity and Access | Accounts, credentials, roles, tokens | Orders or organizer business data | Synchronous token validation; user lifecycle events |
| Catalog and Discovery | Events, schedules, venue geometry, price definitions, search projection | Live locks or booking truth | Synchronous queries; consumes inventory summaries |
| Waiting Room | Queue position, admission tokens, rate policy | Authentication or seat inventory | Synchronous admission check; emits admission telemetry |
| Reservation and Inventory | Seat state, lock TTL, reservation aggregate, concurrency invariant | Payment settlement | Synchronous lock/confirm API; publishes reservation events |
| Billing and Checkout | Order saga, payment attempts, refunds, financial ledger references | Seat state | Synchronous gateway adapter; commands Reservation; publishes outcomes |
| Ticketing | Issued ticket, QR token hash, revocation status | Payment authorization | Consumes successful checkout events |
| Notification | Templates, delivery attempts, channel preferences | Order or ticket truth | Consumes domain events; calls email/SMS providers |

Each context has a private logical datastore. A shared PostgreSQL cluster may be
used initially for cost reasons, but schemas, credentials, migrations, and write
access remain isolated per context. Redis is owned by Reservation for lock TTLs;
Catalog may use a separate cache namespace but cannot inspect lock keys.

## Dependency Rules

1. Clients enter through the API Gateway; services are not publicly addressable.
2. Identity is referenced by immutable `userId`, never by joining another
   service's account tables.
3. Catalog never writes inventory and Reservation never writes event metadata.
4. Checkout coordinates the purchase saga but does not bypass Reservation's
   confirm/release commands.
5. Notification and Ticketing react to events and are never required for payment
   authorization to complete.
6. Event payloads contain stable identifiers and required facts, not internal
   database entities.

## Consistency Model

- Seat locks, booking confirmation, and payment-attempt transitions require
  strong consistency within their owning aggregate.
- Search availability, dashboards, notifications, and analytics are eventually
  consistent.
- Every event includes `eventId`, `eventType`, `schemaVersion`, `aggregateId`,
  `aggregateVersion`, `occurredAt`, `correlationId`, and `causationId`.
- Producers use a transactional outbox. Consumers store processed `eventId`
  values so replay is safe.

The context map is defined in
[`diagrams/bounded-context-map.puml`](diagrams/bounded-context-map.puml).
