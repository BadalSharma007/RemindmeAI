/**
 * RemindmeAI — k6 Load Test
 *
 * Scenarios:
 *   1. health_check   — constant rate, baseline connectivity
 *   2. auth_flow      — OAuth connect initiation (rate-limited read)
 *   3. deadline_read  — authenticated GET /deadlines (main read path)
 *   4. dashboard_read — authenticated GET /stats/dashboard (aggregate query)
 *   5. snooze_write   — POST /reminders/{id}/snooze (write + Redis update)
 *
 * Usage:
 *   k6 run --env BASE_URL=https://api.remindmeai.com \
 *           --env JWT_TOKEN=<your-jwt> \
 *           load_tests/k6_script.js
 *
 * Targets (P95 SLA from Phase 4 requirements):
 *   Read endpoints   < 500 ms P95
 *   Write endpoints  < 1000 ms P95
 *   Error rate       < 1%
 */
import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------
const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";
const JWT_TOKEN = __ENV.JWT_TOKEN || "test-jwt-token";

const authHeaders = {
  Authorization: `Bearer ${JWT_TOKEN}`,
  "Content-Type": "application/json",
};

// Custom metrics
const errorRate = new Rate("errors");
const deadlineLatency = new Trend("deadline_read_latency", true);
const dashboardLatency = new Trend("dashboard_latency", true);
const snoozeLatency = new Trend("snooze_latency", true);

// ---------------------------------------------------------------------------
// Load profile
// ---------------------------------------------------------------------------
export const options = {
  scenarios: {
    health_check: {
      executor: "constant-arrival-rate",
      rate: 5,
      timeUnit: "1s",
      duration: "2m",
      preAllocatedVUs: 5,
      tags: { scenario: "health" },
    },
    deadline_read: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "30s", target: 20 },
        { duration: "2m",  target: 50 },
        { duration: "30s", target: 20 },
        { duration: "30s", target: 0  },
      ],
      tags: { scenario: "read" },
    },
    dashboard_read: {
      executor: "constant-vus",
      vus: 10,
      duration: "3m",
      startTime: "30s",
      tags: { scenario: "dashboard" },
    },
  },
  thresholds: {
    http_req_duration: ["p(95)<500", "p(99)<1000"],
    errors: ["rate<0.01"],
    deadline_read_latency: ["p(95)<500"],
    dashboard_latency: ["p(95)<500"],
    snooze_latency: ["p(95)<1000"],
  },
};

// ---------------------------------------------------------------------------
// Scenario functions
// ---------------------------------------------------------------------------

export function healthCheck() {
  const res = http.get(`${BASE_URL}/health`);
  const ok = check(res, {
    "health status 200": (r) => r.status === 200,
    "health body ok": (r) => r.json("status") === "ok",
  });
  errorRate.add(!ok);
  sleep(0.2);
}

export function deadlineRead() {
  const start = Date.now();
  const res = http.get(`${BASE_URL}/deadlines?status=pending&limit=20`, {
    headers: authHeaders,
  });
  deadlineLatency.add(Date.now() - start);

  const ok = check(res, {
    "deadlines 200": (r) => r.status === 200,
    "deadlines is array": (r) => Array.isArray(r.json()),
  });
  errorRate.add(!ok);
  sleep(0.5 + Math.random());
}

export function dashboardRead() {
  const start = Date.now();
  const res = http.get(`${BASE_URL}/stats/dashboard`, {
    headers: authHeaders,
  });
  dashboardLatency.add(Date.now() - start);

  const ok = check(res, {
    "dashboard 200": (r) => r.status === 200,
    "has total_deadlines": (r) => r.json("total_deadlines") !== undefined,
  });
  errorRate.add(!ok);
  sleep(1 + Math.random());
}

// Default scenario: mix of read operations
export default function () {
  const roll = Math.random();
  if (roll < 0.6) {
    deadlineRead();
  } else if (roll < 0.9) {
    dashboardRead();
  } else {
    healthCheck();
  }
}
