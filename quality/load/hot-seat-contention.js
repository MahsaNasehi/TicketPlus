import http from "k6/http";
import { check, sleep } from "k6";
import exec from "k6/execution";
import { Counter } from "k6/metrics";

const lockWinners = new Counter("lock_winners");
const expectedConflicts = new Counter("expected_lock_conflicts");

http.setResponseCallback(http.expectedStatuses(201, 409));

export const options = {
  scenarios: {
    hot_seat: {
      executor: "per-vu-iterations",
      vus: Number(__ENV.VUS || 1000),
      iterations: 1,
      maxDuration: "2m",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<750"],
    lock_winners: ["count==1"],
  },
};

const baseUrl = __ENV.BASE_URL || "http://localhost:8080";
const eventId = __ENV.EVENT_ID;
const seatId = __ENV.SEAT_ID;

export function setup() {
  if (!eventId || !seatId) {
    throw new Error("EVENT_ID and SEAT_ID are required");
  }
}

export default function () {
  const idempotencyKey = `load-${exec.scenario.iterationInTest}-${exec.vu.idInTest}`;
  const response = http.post(
    `${baseUrl}/reservations`,
    JSON.stringify({ eventId, seatIds: [seatId] }),
    {
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": idempotencyKey,
        Authorization: `Bearer ${__ENV.ACCESS_TOKEN || "synthetic-test-token"}`,
      },
      tags: { operation: "hot-seat-lock" },
    },
  );

  if (response.status === 201) {
    lockWinners.add(1);
  } else if (response.status === 409) {
    expectedConflicts.add(1);
  }

  check(response, {
    "request either wins or conflicts": (r) => r.status === 201 || r.status === 409,
  });
  sleep(Math.random() * 0.2);
}

export function handleSummary(data) {
  return {
    stdout: JSON.stringify(data, null, 2),
    "hot-seat-summary.json": JSON.stringify(data),
  };
}
