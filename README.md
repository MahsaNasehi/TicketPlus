# TicketPlus

Reference implementation of a high-concurrency event-ticketing platform:
seat locking, idempotent checkout, and ticket issuance, built with a
dependency-free Python backend (standard-library `http.server` + SQLite)
and a plain HTML/CSS/JS frontend.

> This is a **reference implementation**, not the full production
> architecture. The complete target design (Venue/Sector/Row/Seat catalog,
> `ORGANIZER` role, dynamic pricing, Kafka/Postgres/Redis) is documented in
> `docs/`, `diagrams/`, and `db/migrations/`; this codebase is a smaller,
> dependency-free stand-in used to prove out the critical concurrency and
> payment rules end to end.

## Architecture

- `src/ticketplus/auth.py` — email/password auth. Passwords hashed with
  PBKDF2-HMAC-SHA256 (200k iterations); signed, self-contained bearer tokens
  (HMAC-SHA256), 7-day TTL. Every user has a `role` of `user` or `admin`
  (default `user`, only settable at registration time via `{"role": "admin"}`
  in the request body — the frontend register form never sends this field,
  so self-service sign-up always creates a plain `user`); `require_admin()`
  gates admin-only endpoints. Not intended for real production use (no rate
  limiting, no email verification, no password reset).
- `src/ticketplus/catalog.py` — event (theater/show) catalog. An event has a
  `title`, `venue`, `dateLabel`, and one or more seating `rows` (each with a
  `label`, a seat count, and a per-seat `priceMinor`). Creating or editing
  an event (`create_event`/`update_event`) is restricted to `admin`
  accounts and requires every row's price to be strictly greater than
  100,000; no other constraint is placed on price or on the rest of the
  event fields. Backed by its own `events` table in the same SQLite
  database. A fresh catalog is seeded with a few demo theaters/concerts so
  the event list is never empty out of the box.
- `src/ticketplus/reservation.py` — seat-locking aggregate backed by SQLite.
  A unique index on `(event_id, seat_id)` in `reservation_seats` is what
  guarantees no two customers can lock the same seat, even under concurrent
  requests. Locks expire automatically after a TTL (default 600s).
- `src/ticketplus/checkout.py` — idempotent checkout saga: on payment
  success it confirms the reservation and issues a ticket; on failure it
  releases the seats back to the pool (compensation).
- `src/ticketplus/events.py` — small in-process, idempotent **domain event
  bus** (`ReservationCreated`, `ReservationConfirmed`, `PaymentSucceeded`,
  `TicketIssued`, ...), standing in for a Kafka-style broker. This is
  unrelated to the *ticket/theater* catalog in `catalog.py` — the name
  overlap is a known source of confusion, see "Known limitations" below.
- `src/ticketplus/http_api.py` — HTTP adapter exposing the above as a JSON
  API, with CORS enabled for the local frontend.
- `frontend/` — vanilla HTML/CSS/JS client (`index.html`, `app.js`,
  `styles.css`) served as static files. The account's `role` (from
  `/auth/login` or `/auth/register`, not a hardcoded email) decides what a
  logged-in user sees: an `admin` lands directly on the admin panel — a
  list of every existing theater/concert (with an "edit" button per event
  that reopens the form pre-filled, calling `PUT /events/{id}`) plus the
  "add a new theater" form — and never sees the customer booking flow; a
  plain `user` sees the event list and seat/checkout flow and never sees
  the admin panel. A user's pending (locked, unpaid) reservation is kept
  per theater (`localStorage`, keyed by user id): browsing away to a
  different theater and coming back restores the locked seats, countdown,
  and "pay now" button exactly as they were, as long as the reservation
  hasn't expired — the same applies across a page refresh.
- `db/migrations/`, `contracts/openapi/`, `diagrams/` /
  `rendered diagrams/`, `docs/`, `infra/terraform/`, `reports/` — schema
  migrations, API contracts, architecture diagrams, written documentation,
  IaC, and QA (coverage/mutation) reports for the *full* target
  architecture (not all of it is implemented in `src/ticketplus/` yet).

## API summary

| Method | Path                              | Notes                                   |
|--------|-----------------------------------|------------------------------------------|
| GET    | `/health/live`, `/health/ready`   | `{"status": "UP"}`                      |
| POST   | `/auth/register`                  | `{email, password, name, role?}` → token, user |
| POST   | `/auth/login`                     | `{email, password}` → token, user       |
| GET    | `/auth/me`                        | `Authorization: Bearer <token>`         |
| GET    | `/events`                         | `{events: [...]}` — every event in the catalog (seeded with a few demo theaters/concerts by default) |
| POST   | `/events`                         | **Admin only.** `{title, venue, dateLabel, rows: [{label, seats, priceMinor}, ...]}`; every row's `priceMinor` must be > 100,000. Returns `403` for non-admins, `401` if unauthenticated, `400` for invalid data |
| PUT    | `/events/{eventId}`                | **Admin only.** Same body shape as `POST /events`; overwrites the event in place (id/createdAt kept). `403`/`401` as above, `404` if the id doesn't exist, `400` for invalid data |
| GET    | `/events/{eventId}/seats`         | `{locked: [...], booked: [...]}`        |
| POST   | `/reservations`                   | Requires `Idempotency-Key` (≥8 chars)   |
| GET    | `/reservations/{id}`              |                                          |
| POST   | `/checkouts`                      | Requires `Idempotency-Key` (≥8 chars)   |
| GET    | `/tickets/by-reservation/{id}`    | 404 if no ticket yet                     |

`contracts/openapi/ticketplus.yaml` currently only documents the
reservation/checkout/ticket endpoints; the `/auth/*` and `/events`
endpoints above still need to be added to that contract.

## Environment variables

| Variable              | Default              | Purpose                                   |
|-----------------------|-----------------------|--------------------------------------------|
| `PORT`                | `8080`                | Backend HTTP port                          |
| `DATABASE_PATH`       | `/data/ticketplus.db` | SQLite file for reservations and the event catalog |
| `AUTH_DATABASE_PATH`  | value of `DATABASE_PATH` | SQLite file for users (can be separate)  |
| `AUTH_SECRET`         | dev default (change in real deployments) | HMAC signing secret for auth tokens |
| `PAYMENT_OUTCOME`     | `SUCCEEDED`           | Simulated payment gateway result (`SUCCEEDED`/`FAILED`/`UNKNOWN`) |

## Running locally

### 1. Start the backend

```bash
cd TicketPlus
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

### 3. Create the first admin account

There is no bootstrap admin; the first admin must be registered directly
with `role: "admin"` (no other user can promote themselves or anyone else):

```bash
curl -X POST http://127.0.0.1:9090/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"change-me-please","name":"Admin","role":"admin"}'
```

### 4. Start the frontend

```bash
cd TicketPlus/frontend
python3 -m http.server 5500
```

Leave this terminal open too. If the backend is on a different host/port,
update the API base URL in `frontend/app.js` accordingly.

### 5. Open the app

Go to <http://127.0.0.1:5500> in your browser. Log in with the admin
account above and you're taken straight to the admin panel: a list of every
existing theater/concert (each with an "ویرایش"/edit button that reopens
the form pre-filled with that event's data) plus the "add a new theater"
form below it — admins never see the customer booking flow. Register a
normal account instead (no `role` field) to see the event list and go
through booking a seat and checking out as a regular user.

## Tests

```bash
cd TicketPlus
PYTHONPATH=src python3 -m unittest discover -s tests -v
# or, if pytest is installed:
PYTHONPATH=src python3 -m pytest tests/
python3 quality/coverage/run.py
python3 quality/mutation/run.py
```

## Known limitations

- Auth has no rate limiting, email verification, or password-reset flow —
  by design, for a local reference environment.
- The payment gateway is simulated (`PAYMENT_OUTCOME` env var); no real
  payment provider is integrated.
- Roles are limited to `user`/`admin`; the `ORGANIZER` role from the full
  design docs is not implemented here.
- The "price must exceed 100,000" rule is enforced per seating row
  (`priceMinor`), since that's the level at which price actually varies in
  this reference implementation — there is no separate event-level price.
- `catalog.py`/`auth.py` are new additions and are not yet covered by the
  `quality/coverage` and `quality/mutation` runs whose last recorded
  results are in the design report.