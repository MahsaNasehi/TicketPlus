# Asynchronous Messaging Layout

Kafka buffers transaction outcomes so payment completion is not coupled to
ticket generation, notification providers, or analytics. Topics are partitioned
by aggregate identifier to preserve ordering for a reservation or order.

| Topic | Key | Producer | Consumers | Retention |
|---|---|---|---|---|
| `reservation.events.v1` | `reservationId` | Reservation | Checkout, Catalog projection | 7 days |
| `payment.events.v1` | `orderId` | Checkout | Ticketing, Notification, Analytics | 30 days |
| `ticket.events.v1` | `ticketId` | Ticketing | Notification, Validation projection | 30 days |
| `notification.commands.v1` | `userId` | Checkout/Ticketing | Notification | 7 days |
| `*.dlq.v1` | original key | Consumer retry handler | Operations replay tool | 30 days |

## Successful Transaction

1. Checkout writes `PAID` and an outbox record in one database transaction.
2. The outbox relay publishes `PaymentSucceeded` with the order correlation ID.
3. Ticketing idempotently issues the QR-backed ticket and publishes
   `TicketIssued`.
4. Notification consumes the events and sends the confirmation. Notification
   failure cannot roll back a paid order or issued ticket.

## Failure and Delivery Controls

- Delivery is at least once; handlers must be idempotent.
- Consumers retry transient failures with exponential backoff and jitter.
- After five unsuccessful attempts, the message and failure metadata move to a
  dead-letter topic and trigger an alert.
- Consumers reject unsupported schema versions without discarding the message.
- Lag thresholds provide backpressure signals and drive worker autoscaling.
- Payment events contain gateway references but never card data or secrets.
- A replay tool requires an audited operator action and preserves the original
  `eventId` to prevent duplicated business effects.

The end-to-end trace, including a notification failure path, is in
[`diagrams/async-transaction-flow.puml`](diagrams/async-transaction-flow.puml).
