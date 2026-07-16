CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE SCHEMA IF NOT EXISTS identity;
CREATE SCHEMA IF NOT EXISTS catalog;
CREATE SCHEMA IF NOT EXISTS reservation;
CREATE SCHEMA IF NOT EXISTS checkout;
CREATE SCHEMA IF NOT EXISTS ticketing;
CREATE SCHEMA IF NOT EXISTS notification;

CREATE TABLE IF NOT EXISTS identity.users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email text NOT NULL UNIQUE,
    display_name text NOT NULL,
    role text NOT NULL CHECK (role IN ('BUYER', 'ORGANIZER', 'ADMIN')),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS catalog.events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organizer_id uuid NOT NULL,
    title text NOT NULL,
    category text NOT NULL,
    location text NOT NULL,
    starts_at timestamptz NOT NULL,
    status text NOT NULL CHECK (status IN ('PLANNED', 'ON_SALE', 'SOLD_OUT', 'CANCELLED'))
);

CREATE TABLE IF NOT EXISTS catalog.seats (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    venue_id uuid NOT NULL,
    sector text NOT NULL,
    row_label text NOT NULL,
    seat_number text NOT NULL,
    UNIQUE (venue_id, sector, row_label, seat_number)
);

CREATE TABLE IF NOT EXISTS reservation.reservations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL,
    event_id uuid NOT NULL,
    status text NOT NULL CHECK (status IN ('PENDING', 'CONFIRMED', 'EXPIRED', 'CANCELLED')),
    expires_at timestamptz NOT NULL,
    idempotency_key text NOT NULL UNIQUE,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS reservation.reservation_seats (
    reservation_id uuid NOT NULL REFERENCES reservation.reservations(id),
    event_id uuid NOT NULL,
    seat_id uuid NOT NULL,
    PRIMARY KEY (reservation_id, seat_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS confirmed_event_seat_owner
ON reservation.reservation_seats(event_id, seat_id);

CREATE TABLE IF NOT EXISTS checkout.payment_attempts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    reservation_id uuid NOT NULL,
    idempotency_key text NOT NULL UNIQUE,
    amount_minor bigint NOT NULL CHECK (amount_minor > 0),
    currency char(3) NOT NULL,
    provider_reference text,
    status text NOT NULL CHECK (status IN ('SUCCEEDED', 'FAILED', 'UNKNOWN')),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ticketing.tickets (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    reservation_id uuid NOT NULL UNIQUE,
    qr_hash text NOT NULL UNIQUE,
    status text NOT NULL DEFAULT 'VALID' CHECK (status IN ('VALID', 'REVOKED', 'USED')),
    issued_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS notification.deliveries (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id uuid NOT NULL UNIQUE,
    channel text NOT NULL CHECK (channel IN ('EMAIL', 'SMS', 'PUSH')),
    status text NOT NULL CHECK (status IN ('PENDING', 'SENT', 'FAILED')),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS checkout.outbox (
    event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type text NOT NULL,
    aggregate_id uuid NOT NULL,
    schema_version integer NOT NULL DEFAULT 1,
    payload jsonb NOT NULL,
    occurred_at timestamptz NOT NULL DEFAULT now(),
    published_at timestamptz
);

