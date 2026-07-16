# Waiting Room Worker Failure Postmortem

**Severity:** SEV-1  
**Duration:** 27 minutes  
**Status:** Resolved (scenario analysis)

## Summary and Impact

At the start of a popular event sale, queue workers exhausted memory while
rebuilding an oversized in-memory priority index. Admission token issuance
stopped and the API Gateway returned HTTP 503 after its waiting-room timeout.
Approximately 64,000 users received errors and 11,500 valid queue positions were
temporarily delayed. Existing admitted users could continue checkout, and no
reservation-integrity violation occurred.

## Timeline

| Time | Event |
|---|---|
| 10:00 | Sale opens; arrival rate reaches 18,000 requests/second. |
| 10:02 | Queue lag and worker restart alerts fire. |
| 10:05 | Incident declared SEV-1; admission rate reduced. |
| 10:09 | Repeated OOM kills traced to priority-index rebuilds. |
| 10:12 | Queue writes remain durable; workers switched to FIFO recovery mode. |
| 10:17 | Additional workers start with bounded index configuration. |
| 10:22 | Token issuance resumes; clients receive retry-after responses. |
| 10:27 | Normal weighted-fair admission restored. |

## Root Cause

Each worker rebuilt the complete queue priority index locally after a partition
rebalance. Concurrent rebalances multiplied memory consumption beyond pod
limits, causing another restart and a feedback loop. Gateway timeout handling
translated this dependency failure to generic 503 responses without preserving
the user's durable queue token.

## Contributing Factors

- The load test ramped gradually and did not model an instantaneous sale opening.
- Autoscaling used CPU but ignored queue lag and restart rate.
- All worker partitions rebalanced together during scale-out.
- The client fallback lacked jitter and caused synchronized retries.

## Resolution

Admission was reduced to protect Reservation, and workers entered a degraded FIFO
mode backed by the durable queue. The Gateway returned `429 Retry-After` with the
existing signed queue token instead of losing the user's place. Workers were
scaled only after deploying a bounded, incremental index rebuild configuration.

## Corrective Actions

| Action | Owner | Due | Verification |
|---|---|---|---|
| Replace full index rebuild with bounded incremental restoration | Queue team | 14 days | Peak-size recovery benchmark |
| Scale workers on queue lag and memory headroom | Platform team | 7 days | Autoscaling game day |
| Preserve queue token and return jittered retry guidance | Edge team | 7 days | Browser/API resilience test |
| Add flash-crowd and rebalance-storm load scenarios | QA | 10 days | 25,000 RPS test report |
| Stagger partition reassignment during scale-out | Queue team | 14 days | Failure-injection test |
