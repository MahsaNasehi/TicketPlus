# Payment Gateway Outage Postmortem

**Severity:** SEV-1  
**Duration:** 42 minutes  
**Status:** Resolved (scenario analysis)

## Summary and Impact

The external payment gateway began timing out after receiving charge requests.
Checkout workers retried ambiguous requests, while reservations remained locked
because no definitive payment result reached the saga. For 42 minutes, 38% of
checkout attempts failed or remained pending and 1,246 seats were unavailable
longer than the ten-minute lock policy. No confirmed seat was sold twice, but 73
customers saw duplicate pending bank authorizations.

## Timeline

| Time | Event |
|---|---|
| 19:00 | Payment latency rises after the headline event sale opens. |
| 19:04 | Checkout p95 alert fires; on-call acknowledges. |
| 19:08 | Incident declared SEV-1; deployments frozen. |
| 19:13 | Gateway timeouts confirmed; circuit breaker opened. |
| 19:18 | New checkouts show `PAYMENT_UNAVAILABLE`; existing locks stop extending. |
| 19:25 | Reconciliation job starts querying gateway by idempotency key. |
| 19:34 | Confirmed charges are committed; declined/unknown expired locks are released. |
| 19:42 | Gateway recovers; traffic restored at 10%, then gradually increased. |
| 20:12 | Backlogs drained and reservation/payment reconciliation completes. |

## Root Cause

The gateway degraded after connection-pool exhaustion. TicketPlus treated a
client-side timeout as retryable without first querying the original request's
status. The lock-release path waited for a terminal payment event, so ambiguous
attempts never scheduled compensation until their much longer order timeout.

## Contributing Factors

- Payment retries lacked a gateway idempotency key on one legacy adapter path.
- The reservation TTL was extended on every payment retry.
- Monitoring tracked HTTP errors but not the count and age of `PAYMENT_PENDING`
  orders with expired customer sessions.
- The compensation job was sized for routine failures, not a provider outage.

## Resolution and Compensation

The circuit breaker stopped new requests. A reconciliation script grouped
payment attempts by order and gateway idempotency key, queried the provider, and
performed one of three idempotent actions: confirm the reservation for a settled
charge, release the lock for a definite failure, or quarantine the order for
manual review when status remained unknown. Refunds were issued for duplicate
settlements before affected customers were contacted.

## Corrective Actions

| Action | Owner | Due | Verification |
|---|---|---|---|
| Enforce idempotency keys in every gateway adapter | Checkout team | 7 days | Contract test rejects missing key |
| Stop extending seat TTL after the first authorization request | Reservation team | 7 days | Saga integration test |
| Add pending-payment age and ambiguity dashboards | SRE | 5 days | Alert exercise |
| Scale and load-test the reconciliation worker | Platform team | 14 days | 10,000-order recovery drill |
| Add a secondary payment-provider routing policy | Architecture | 30 days | Controlled failover test |
