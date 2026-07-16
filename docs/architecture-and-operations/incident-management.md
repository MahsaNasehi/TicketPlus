# Incident Management Framework

## Severity and Response Matrix

| Severity | Definition | Examples | Acknowledge | Update cadence | Leadership notification |
|---|---|---|---|---|---|
| SEV-1 | Purchase integrity, security, or platform-wide outage | Double booking; checkout unavailable; data breach | 5 minutes | 15 minutes | Immediate |
| SEV-2 | Major degradation with workaround or limited scope | One payment provider down; queue delays; regional failure | 10 minutes | 30 minutes | Within 30 minutes |
| SEV-3 | Minor user impact, no integrity risk | Delayed email; partial dashboard failure | 4 business hours | Daily | In daily summary |
| SEV-4 | No current user impact | Capacity warning; documentation defect | 2 business days | As tracked | Not required |

## Roles

- **Incident Commander (IC):** owns severity, priorities, decisions, and handoffs.
- **Operations Lead:** investigates and executes mitigations; does not also act
  as IC during SEV-1.
- **Communications Lead:** publishes internal and customer-facing updates using
  confirmed facts from the IC.
- **Subject-Matter Expert:** advises on the failing domain and validates recovery.
- **Scribe:** records timestamps, evidence, commands, decisions, and action items.

## On-Call Rotation

The primary and secondary rotations change weekly. The secondary takes over if
the primary does not acknowledge within five minutes and becomes primary during
a handoff. Reservation/Checkout and Platform each maintain a specialist
escalation rotation. Handoffs review active incidents, disabled automation,
temporary capacity, recent deployments, and expiring certificates or secrets.

No responder should remain primary for more than 12 hours during a sustained
incident. The IC explicitly transfers command and records the new owner.

## Response Workflow

1. Alertmanager pages the primary with the affected SLO and runbook link.
2. The responder acknowledges, opens an incident channel and timeline, assigns
   severity, and names an IC.
3. The IC freezes unrelated deployments and chooses the lowest-risk mitigation:
   rollback, traffic shift, circuit breaker, capacity increase, or feature flag.
4. Operations protects invariants first. If seat ownership is uncertain, new
   locks or checkouts are rejected rather than guessed.
5. Communications posts updates at the matrix cadence, separating known facts,
   customer impact, mitigation, and next update time.
6. Recovery requires stable SLOs for 30 minutes, drained backlogs, reconciled
   reservations/payments, and confirmation that no duplicate tickets exist.
7. The IC closes the incident and schedules a blameless review within three
   business days for SEV-1/2 incidents.

## Escalation Triggers

- Suspected double booking, data loss, or unauthorized access: immediate SEV-1.
- Checkout error rate above 5% for five minutes: page Checkout and Platform.
- Seat-lock p95 above 750 ms or Redis unavailable: page Reservation and disable
  new admissions if database fallback approaches capacity.
- Kafka lag above two minutes: page Platform and scale consumers; above fifteen
  minutes, pause nonessential producers.
- Third-party payment outage: open provider case and enable the payment circuit
  breaker; do not retry ambiguous charges automatically.

## Post-Incident Standard

Reviews are based on system conditions and decision context, not individual
blame. Each corrective action has one owner, a due date, a measurable completion
condition, and a tracking ticket. The review verifies action completion after
30 days and updates runbooks, alerts, tests, and architecture where necessary.
