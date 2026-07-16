# Gateway-to-Reservation Network Partition Postmortem

**Severity:** SEV-2  
**Duration:** 31 minutes  
**Status:** Resolved (scenario analysis)

## Summary and Impact

A network policy rollout blocked traffic from new API Gateway pods to the
Reservation service. Catalog and authentication remained healthy, but seat maps
and lock requests failed. Fifteen percent of requests reached old Gateway pods
and succeeded, producing inconsistent customer behavior. A total of 8,420 lock
attempts failed; no double booking occurred because the Gateway did not infer
availability when Reservation was unreachable.

## Timeline

| Time | Event |
|---|---|
| 14:20 | Network policy deployment completes. |
| 14:23 | Seat-map error rate warning fires. |
| 14:26 | New Gateway pods show connection timeouts to Reservation. |
| 14:29 | Incident declared SEV-2; policy rollout paused. |
| 14:34 | Traffic shifted to the previous Gateway replica set. |
| 14:40 | Faulty egress selector identified and policy rolled back. |
| 14:46 | Connectivity and lock success recover. |
| 14:51 | Held traffic released gradually; incident enters monitoring. |

## Root Cause

The policy selected Gateway pods by an obsolete `app` label, while the new
deployment used the standardized `app.kubernetes.io/name` label. Default-deny
egress therefore applied without the intended Reservation exception. Policy
validation checked syntax but did not execute a cross-service connectivity test.

## Contributing Factors

- Gateway retries multiplied requests during the partition.
- The canary check exercised `/healthz` but not a Reservation dependency probe.
- Alerts grouped failures by Gateway status code rather than dependency name.
- The rollout reached all namespaces before the first analysis window completed.

## Resolution

Traffic was returned to the prior Gateway replica set and the policy was rolled
back. Lock requests failed closed throughout the event. Clients received a
retryable dependency error; existing Redis locks continued expiring normally,
and a reconciliation query confirmed no orphaned confirmed reservations.

## Corrective Actions

| Action | Owner | Due | Verification |
|---|---|---|---|
| Add policy contract tests using deployed pod labels | Platform team | 5 days | CI connectivity matrix |
| Canary network policies by namespace and zone | SRE | 10 days | Staged rollout exercise |
| Add bounded retry budgets and circuit breaking at Gateway | Edge team | 7 days | Partition fault test |
| Trace dependency failures with service labels | Observability team | 7 days | Dashboard and alert review |
| Add synthetic seat-map and lock checks to canary analysis | QA | 10 days | Automatic rollback demonstration |
