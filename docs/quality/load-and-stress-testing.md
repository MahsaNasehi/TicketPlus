# Load and Stress Testing Plan

## Workload Model

| Scenario | Purpose | Profile | Pass criteria |
|---|---|---|---|
| Baseline browse | Establish normal latency | 500 virtual users for 15 minutes | Search p95 < 400 ms; errors < 0.5% |
| Flash crowd | Validate waiting room and throttling | 0 to 10,000 users in 30 seconds | Core services remain healthy; signed positions preserved |
| Hot-seat contention | Prove lock integrity | 5,000 attempts against one seat | Exactly one lock winner; at most one confirmation |
| Broad reservation peak | Validate planned capacity | 3,000 lock requests/s across 50,000 seats | Lock p95 < 300 ms; errors < 1% excluding conflicts |
| Checkout peak | Validate saga and gateway pool | 500 checkouts/s with controlled outcomes | No duplicate charge; technical success >= 99% |
| Soak | Find leaks and backlog drift | 60% peak for 8 hours | Stable memory/connections; lag < 30 seconds |
| Spike and recovery | Test elasticity | 150% peak for 10 minutes then normal | No invariant failure; backlog drains within 15 minutes |
| Dependency degradation | Validate safe failure | Inject Redis/Kafka/payment latency and errors | Circuit breakers operate; no corrupt state |

Forecast peak is updated before every major event sale. Release testing runs at
forecast plus 50% headroom with the same pod limits, database class, Redis
topology, partitions, and autoscaling thresholds planned for production.

## Execution

1. Seed an isolated event, venue, and synthetic accounts.
2. Warm caches with a separately measured browsing phase.
3. Record the application version, configuration, infrastructure size, data
   volume, and generator capacity.
4. Run one scenario at a time for diagnostic baselines, then the mixed workload.
5. Capture client timings, server RED metrics, database/Redis saturation, Kafka
   lag, autoscaling activity, and traces.
6. Run the integrity oracle from `qa-strategy.md` after every reservation or
   checkout scenario.
7. Archive raw results and a signed summary; never report only averages.

## Failure Injection

- Add 1–5 seconds of payment-provider latency and ambiguous timeouts.
- Terminate a Reservation pod while it owns in-flight requests.
- Trigger Redis primary failover and verify lock ownership after recovery.
- Pause Kafka consumers, build lag, resume, and verify idempotent replay.
- Block Gateway-to-Reservation traffic and confirm bounded retries/fail-closed.
- Exhaust database connections and verify admission reduction.

Experiments begin below saturation, have a named abort owner, and define a
maximum duration. Stop immediately on a duplicate booking, duplicate charge,
unexpected data loss, or load-generator instability.

## Reporting Template

- Commit SHA and environment configuration
- Scenario, data set, duration, and achieved request rate
- p50/p95/p99 latency and error categories
- Saturation, HPA behavior, Kafka lag, and recovery time
- Integrity-oracle query results
- Bottleneck and supporting trace/metric evidence
- Comparison with previous baseline
- Corrective actions, owners, and retest decision

The executable high-contention scenario is
[`../../quality/load/hot-seat-contention.js`](../../quality/load/hot-seat-contention.js).

