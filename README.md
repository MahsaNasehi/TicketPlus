# TicketPlus Architecture Project

TicketPlus is an event-ticketing architecture and reference implementation for
high-demand sales. It demonstrates concurrency-safe seat reservation,
idempotent checkout, payment compensation, asynchronous ticket fulfillment,
production deployment design, quality assurance, and incident handling.

The executable application is a backend reference API. It proves the critical
booking rules; it is not a graphical customer-facing website.

## Repository Map

| Area | Current location |
|---|---|
| UML sources | [`diagrams/`](diagrams/) |
| Rendered UML diagrams | [`rendered diagrams/`](rendered%20diagrams/) |
| Product documents | [`docs/product/`](docs/product/) |
| Production architecture and incidents | [`docs/architecture-and-operations/`](docs/architecture-and-operations/) |
| QA, load, mutation, and coverage documentation | [`docs/quality/`](docs/quality/) |
| Reference application | [`src/ticketplus/`](src/ticketplus/) |
| Unit and integration tests | [`tests/`](tests/) |
| OpenAPI and event contracts | [`contracts/`](contracts/) |
| PostgreSQL migrations | [`db/migrations/`](db/migrations/) |
| Terraform infrastructure | [`infra/terraform/`](infra/terraform/) |
| Load, coverage, and mutation tools | [`quality/`](quality/) |
| Generated quality evidence | [`reports/`](reports/) |
| Team roles and engineering standards | [`docs/project-governance/`](docs/project-governance/) |
| Contribution and review workflow | [`CONTRIBUTING.md`](CONTRIBUTING.md) |
| Submission status | [`docs/submission-checklist.md`](docs/submission-checklist.md) |

## Prerequisites

- Docker Engine with the Compose plugin
- `curl`
- Python 3.12 or newer for running tests directly
- XeLaTeX and `latexmk` only when rebuilding the Persian report

## Start the Reference API

Run Compose in detached mode so the terminal remains available for the demo:

```bash
docker compose up --build -d
docker compose ps
docker compose logs -f reference-api
```

The first build may take time while the Python image is downloaded. Wait until
`docker compose ps` shows `reference-api` as `healthy`. Leave the log command
with `Ctrl+C`; this stops log following, not the container.

Then verify readiness:

```bash
curl http://localhost:8080/health/ready
```

Expected response:

```json
{"status": "UP"}
```

## Demo

### 1. Reserve a seat

```bash
RESERVATION_JSON=$(curl -sS -X POST http://localhost:8080/reservations \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: presentation-reservation-001' \
  -d '{"userId":"student-1","eventId":"concert-1","seatIds":["A-10"]}')

echo "$RESERVATION_JSON"
RESERVATION_ID=$(printf '%s' "$RESERVATION_JSON" | \
  python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
echo "Reservation: $RESERVATION_ID"
```

The reservation should have status `PENDING` and a ten-minute expiry time.

### 2. Prove idempotency

Repeat exactly the same command with the same `Idempotency-Key`. The API returns
the same reservation ID instead of creating a duplicate reservation.

### 3. Prove double-booking protection

```bash
curl -i -X POST http://localhost:8080/reservations \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: competing-buyer-002' \
  -d '{"userId":"student-2","eventId":"concert-1","seatIds":["A-10"]}'
```

Expected result: HTTP `409 Conflict` with `seat_unavailable`. The database
uniqueness constraint allows only one active owner for an event seat.

### 4. Complete checkout

```bash
curl -sS -X POST http://localhost:8080/checkouts \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: presentation-payment-001' \
  -d "{\"reservationId\":\"$RESERVATION_ID\",\"amountMinor\":500000,\"currency\":\"IRR\"}"
```

The default local payment outcome is `SUCCEEDED`. Checkout confirms the
reservation, publishes `PaymentSucceeded`, and causes one ticket to be issued.

### 5. Retrieve the confirmed reservation and ticket

```bash
curl -sS "http://localhost:8080/reservations/$RESERVATION_ID"
curl -sS "http://localhost:8080/tickets/by-reservation/$RESERVATION_ID"
```

The first response should show `CONFIRMED`; the second contains the ticket ID
and generated QR hash.

### 6. Stop and reset

```bash
docker compose down
```

Use `docker compose down -v` only when you intentionally want to delete the
demonstration SQLite database and all Compose volumes.

## Troubleshooting Port 8080

If `curl` reports `Failed to connect`, the API is not listening yet. Check it in
this order:

```bash
docker compose ps
docker compose logs reference-api
docker compose up -d
docker compose port reference-api 8080
```

Do not run the readiness request while `docker compose up --build` is still
downloading or building images. If the container exited, the log output shows
the actual startup error. If port 8080 is already occupied, identify the owner
with `ss -ltnp | grep ':8080'` before changing the Compose port mapping.

## Production-Parity Dependencies

The optional profile also starts PostgreSQL, Redis, and Kafka for adapter work:

```bash
docker compose --profile production-parity up --build -d
docker compose --profile production-parity ps
```

The reference API itself intentionally remains dependency-free and uses SQLite
plus an in-process event bus. The production architecture separates the bounded
contexts and uses PostgreSQL, Redis, Kafka, Kubernetes, and the infrastructure
described in `infra/terraform/`.

## Run Verification

No third-party Python package is required for the core verification commands:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 quality/coverage/run.py
python3 quality/mutation/run.py
```

The current evidence records 9 passing tests, 93.07% statement coverage across
the critical transactional modules, and a 100% score for six targeted
mutations. The HTTP test may be skipped in sandboxes that forbid loopback
sockets; it runs normally where local sockets are permitted.
