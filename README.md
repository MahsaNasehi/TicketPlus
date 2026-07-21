# TicketPlus

Reference implementation of a high-concurrency event-ticketing platform:
seat locking, idempotent checkout, and ticket issuance, built with a
dependency-free Python backend (standard-library `http.server` + SQLite)
and a plain HTML/CSS/JS frontend.

## Architecture

- `src/ticketplus/auth.py` — email/password auth. Passwords hashed with
  PBKDF2-HMAC-SHA256 (200k iterations); signed, self-contained bearer tokens
  (HMAC-SHA256), 7-day TTL. Not intended for real production use (no rate
  limiting, no email verification, no password reset).
- `src/ticketplus/reservation.py` — seat-locking aggregate backed by SQLite.
  A unique index on `(event_id, seat_id)` in `reservation_seats` is what
  guarantees no two customers can lock the same seat, even under concurrent
  requests. Locks expire automatically after a TTL (default 600s).
- `src/ticketplus/checkout.py` — idempotent checkout saga: on payment
  success it confirms the reservation and issues a ticket; on failure it
  releases the seats back to the pool (compensation).
- `src/ticketplus/events.py` — small in-process, idempotent event bus
  (`ReservationCreated`, `ReservationConfirmed`, `PaymentSucceeded`,
  `TicketIssued`, ...), standing in for a Kafka-style broker.
- `src/ticketplus/http_api.py` — HTTP adapter exposing the above as a JSON
  API, with CORS enabled for the local frontend.
- `frontend/` — vanilla HTML/CSS/JS client (`index.html`, `app.js`,
  `styles.css`) served as static files.
- `db/migrations/`, `contracts/openapi/`, `diagrams/` /
  `rendered diagrams/`, `docs/`, `infra/terraform/`, `reports/` — schema
  migrations, API contracts, architecture diagrams, written documentation,
  IaC, and QA (coverage/mutation) reports.

## API summary

| Method | Path                              | Notes                                   |
|--------|-----------------------------------|------------------------------------------|
| GET    | `/health/live`, `/health/ready`   | `{"status": "UP"}`                      |
| POST   | `/auth/register`                  | `{email, password, name}` → token, user |
| POST   | `/auth/login`                     | `{email, password}` → token, user       |
| GET    | `/auth/me`                        | `Authorization: Bearer <token>`         |
| GET    | `/events/{eventId}/seats`         | `{locked: [...], booked: [...]}`        |
| POST   | `/reservations`                   | Requires `Idempotency-Key` (≥8 chars)   |
| GET    | `/reservations/{id}`              |                                          |
| POST   | `/checkouts`                      | Requires `Idempotency-Key` (≥8 chars)   |
| GET    | `/tickets/by-reservation/{id}`    | 404 if no ticket yet                     |

## Environment variables

| Variable              | Default              | Purpose                                   |
|-----------------------|-----------------------|--------------------------------------------|
| `PORT`                | `8080`                | Backend HTTP port                          |
| `DATABASE_PATH`       | `/data/ticketplus.db` | SQLite file for reservations               |
| `AUTH_DATABASE_PATH`  | value of `DATABASE_PATH` | SQLite file for users (can be separate)  |
| `AUTH_SECRET`         | dev default (change in real deployments) | HMAC signing secret for auth tokens |
| `PAYMENT_OUTCOME`     | `SUCCEEDED`           | Simulated payment gateway result (`SUCCEEDED`/`FAILED`/`UNKNOWN`) |

## Running locally

### 1. Start the backend (port 9090)

```bash
cd ~/Desktop/New\ Folder/TicketPlus
PYTHONPATH=src DATABASE_PATH=./ticketplus.db PORT=9090 python3 -m ticketplus.http_api
```

If it starts correctly the terminal will stay silent — that's expected,
it means the server is running. Leave this terminal open.

### 2. Verify the backend (new terminal)

```bash
curl http://127.0.0.1:9090/health/ready
```

Expected response:

```json
{"status": "UP"}
```

### 3. Start the frontend

```bash
cd ~/Desktop/New\ Folder/TicketPlus/frontend
python3 -m http.server 5500
```

Leave this terminal open too.

### 4. Open the app

Go to <http://127.0.0.1:5500> in your browser.

## Tests

```bash
cd ~/Desktop/New\ Folder/TicketPlus
PYTHONPATH=src python3 -m pytest tests/
```

## Known limitations

- Auth has no rate limiting, email verification, or password-reset flow —
  by design, for a local reference environment.
- The payment gateway is simulated (`PAYMENT_OUTCOME` env var); no real
  payment provider is integrated.