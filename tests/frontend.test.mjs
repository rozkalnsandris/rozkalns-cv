import assert from "node:assert/strict";
import test from "node:test";
import {
  buildChatPayload,
  normalizeCompletedHistory,
  validateStats
} from "../html/assets/app.d878d409f278.mjs";
import {
  contactPayloadIsValid,
  skillIconName
} from "../html/assets/enhancements.0027f066ac26.mjs";

const liveStats = {
  updated: "2026-08-06T12:00:00Z",
  uptime_30d: 99.9,
  docker_containers: 12,
  load1: 0.25,
  days_online: 9,
  cpu_usage: 14.2,
  ram_usage: 47.1,
  disk_usage: 35.4,
  cpu_temp: 52.3
};

test("chat payload contains the current question once", () => {
  const history = [
    { role: "user", content: "previous" },
    { role: "assistant", content: "answer" }
  ];
  const payload = buildChatPayload("current", history);
  assert.equal(payload.message, "current");
  assert.deepEqual(payload.history, history);
  assert.equal(
    JSON.stringify(payload).match(/current/g)?.length,
    1
  );
});

test("incomplete history is dropped", () => {
  const history = [
    { role: "user", content: "complete" },
    { role: "assistant", content: "answer" },
    { role: "user", content: "orphan" }
  ];
  assert.deepEqual(normalizeCompletedHistory(history), history.slice(0, 2));
});

test("valid recent stats are live", () => {
  const result = validateStats(liveStats, Date.parse("2026-08-06T12:05:00Z"));
  assert.equal(result.valid, true);
  assert.equal(result.state, "live");
});

test("old stats are stale", () => {
  const result = validateStats(liveStats, Date.parse("2026-08-06T12:20:01Z"));
  assert.equal(result.valid, true);
  assert.equal(result.state, "stale");
});

test("future, malformed, and non-finite stats are offline", () => {
  assert.equal(
    validateStats(liveStats, Date.parse("2026-08-06T11:50:00Z")).valid,
    false
  );
  assert.equal(validateStats({ ...liveStats, updated: "bad" }).valid, false);
  assert.equal(validateStats({ ...liveStats, load1: Number.NaN }).valid, false);
  const missing = { ...liveStats };
  delete missing.cpu_temp;
  assert.equal(validateStats(missing).valid, false);
});

test("skill chips map to meaningful SVG icon families", () => {
  assert.equal(skillIconName("Docker Compose"), "container");
  assert.equal(skillIconName("SSL/TLS"), "shield");
  assert.equal(skillIconName("Prometheus"), "chart");
  assert.equal(skillIconName("Home Assistant"), "home");
  assert.equal(skillIconName("ESP32 / IoT"), "chip");
  assert.equal(skillIconName("Terraform"), "cloud");
});

test("contact reveal payload must contain bounded contact shapes", () => {
  assert.equal(
    contactPayloadIsValid({
      email: "person@example.com",
      phone: "+49 123 456789",
      phone_uri: "+49123456789"
    }),
    true
  );
  assert.equal(
    contactPayloadIsValid({
      email: "not-an-email",
      phone: "123",
      phone_uri: "javascript:alert(1)"
    }),
    false
  );
});
