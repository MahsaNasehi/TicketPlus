# Architecture Defense Guide

## Demonstration Order

1. State the buyer/organizer problem and correctness objective.
2. Walk through discovery, waiting room, seat lock, checkout, and ticket issuance
   using the use-case and booking sequence diagrams.
3. Explain why Reservation, not Catalog, owns live availability.
4. Trace a successful and failed payment through saga compensation and Kafka.
5. Map services to Kubernetes, PostgreSQL, Redis, Kafka, and the load balancer.
6. Show how Terraform corresponds to the deployment model.
7. Present the QA integrity oracle, contention scenario, and mutation gates.
8. Walk through one incident timeline and the preventive follow-ups.

## Key Tradeoffs

### Redis Locks Plus Database Constraints

Redis provides fast TTL-based contention control, but it is not the final proof
of ownership. PostgreSQL confirmation constraints protect the invariant during
Redis failover. This adds implementation complexity but avoids treating a
transient cache as the durable source of truth.

### Saga Instead of Distributed Transactions

The external payment provider cannot participate in a database transaction.
Checkout therefore records explicit states and uses idempotent compensation.
The workflow can temporarily be pending, but it remains recoverable and avoids
holding distributed locks across a network call.

### Eventually Consistent Search

Catalog availability counts may lag because they are projections. Fast, scalable
search is preferred, while lock acquisition always revalidates against
Reservation. The UI must communicate conflicts without implying a guaranteed
seat before locking.

### At-Least-Once Messaging

At-least-once Kafka delivery is operationally realistic. Transactional outbox,
consumer inbox, stable event IDs, and unique business constraints make duplicate
delivery safe. Claiming exactly-once end-to-end behavior would hide provider and
database boundaries.

### Single Region, Multi-AZ Initial Deployment

Multi-AZ protects common infrastructure failures without the consistency and
cost burden of active-active multi-region seat ownership. Regional recovery is
a future milestone driven by business RTO and market scale.

## Expected Questions

| Question | Defensible answer and evidence |
|---|---|
| How is double booking prevented? | Atomic lock, ownership token, durable uniqueness/version check, and post-test integrity query. |
| What if payment times out after charging? | Mark unknown, query by idempotency key, then confirm/release/quarantine; never issue a new charge blindly. |
| What if Kafka is unavailable? | Business state and outbox commit together; publication resumes later while nonessential consumers remain decoupled. |
| Why not store availability in Catalog? | It creates circular ownership and mixes volatile concurrency state with search; Catalog consumes a projection. |
| How is queue fairness maintained? | Durable ordered position, signed token, per-class ordering audit, and admission governed by downstream capacity. |
| How does the system scale? | Stateless pods use HPA; waiting room throttles demand; Redis/Kafka/RDS are managed multi-AZ dependencies. |
| How is a bad release contained? | CI gates, canary traffic, SLO comparison, automatic rollback, and backward-compatible migrations. |
| What proves the tests are effective? | Mutation score complements coverage; contention tests query durable state rather than trusting HTTP results. |
| What remains externally supplied? | The final Product Vision, Risk Analysis, and Jira exports are maintained by the project team and added before packaging. |

## Team Preparation

Each member prepares one product workflow, one architecture decision, one
failure scenario, one QA control, and one operational tradeoff. Answers should
reference committed artifacts and acknowledge limitations rather than inventing
unimplemented behavior.
