# Production Telemetry and Monitoring

## Deployment Strategy

Services run as stateless Kubernetes Deployments across at least three
availability zones. Reservation lock state remains in Redis/PostgreSQL, allowing
pods to be replaced safely. Horizontal Pod Autoscalers use CPU plus domain
signals such as request concurrency and Kafka consumer lag.

Canary releases start at 5% of traffic, then progress to 25%, 50%, and 100% after
ten-minute analysis windows. Promotion stops automatically when the canary's
error rate, latency, or reservation-conflict rate exceeds the stable version.
Readiness probes prevent traffic before dependencies and migrations are ready;
pod disruption budgets preserve capacity during node maintenance.

## Telemetry Pipeline

- OpenTelemetry SDKs emit traces and correlation IDs across HTTP and Kafka.
- Prometheus scrapes service, ingress, Kubernetes, Kafka, Redis, and PostgreSQL
  metrics.
- Centralized structured logs include service, version, trace ID, correlation
  ID, and error code; sensitive identity and payment data are redacted.
- Grafana displays service health and business safety signals.
- Alertmanager routes actionable alerts to the active on-call engineer.

## Service-Level Objectives

| User journey / signal | Objective | Warning | Page |
|---|---|---|---|
| Event search availability | 99.9% monthly | 5-minute error-budget burn > 2x | Burn > 14x for 5 minutes |
| Seat-lock API availability | 99.95% monthly | Error rate > 0.5% for 10 minutes | Error rate > 2% for 5 minutes |
| Seat-lock latency | p95 < 300 ms | p95 > 300 ms for 10 minutes | p95 > 750 ms for 5 minutes |
| Checkout API availability | 99.95% monthly | Failure rate > 1% for 10 minutes | Failure rate > 5% for 5 minutes |
| Double bookings | 0 | Any suspected invariant violation | Immediate page |
| Kafka consumer lag | < 30 seconds | > 30 seconds for 10 minutes | > 120 seconds for 5 minutes |
| Notification delivery | 99% within 2 minutes | DLQ growth or p95 > 2 minutes | Backlog > 15 minutes |

Dashboards are organized into: executive purchase funnel, user-journey SLOs,
service RED metrics (rate/errors/duration), infrastructure saturation, and the
reservation safety panel. High-cardinality identifiers belong in traces/logs,
not Prometheus labels.

The architectural mapping is in
[`diagrams/production-telemetry.puml`](diagrams/production-telemetry.puml).
