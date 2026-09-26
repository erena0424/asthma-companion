import test from "node:test";
import assert from "node:assert/strict";
import { requestProfile } from "./profileRequest.js";

test("successful profile fetch sends credentials and accepts a missing name", async () => {
  const profile = { id: 7, name: null };
  const result = await requestProfile("https://example.test", "jwt", async (url, options) => {
    assert.equal(url, "https://example.test/v1/users/me");
    assert.equal(options.headers.Authorization, "Bearer jwt");
    return { ok: true, status: 200, json: async () => profile };
  });
  assert.deepEqual(result, { status: "ready", profile });
});

test("only a confirmed 401 invalidates authentication", async () => {
  for (const status of [401, 403, 404, 429, 500, 503]) {
    const result = await requestProfile("", "jwt", async () => ({ ok: false, status }));
    assert.equal(result.status, status === 401 ? "unauthorized" : "error");
  }
});

test("network and malformed response errors are retryable, not logout", async () => {
  const responses = [
    async () => { throw new TypeError("offline"); },
    async () => ({ ok: true, json: async () => { throw new SyntaxError("bad JSON"); } }),
    async () => ({ ok: true, json: async () => null }),
  ];
  for (const fetcher of responses) {
    const result = await requestProfile("", "jwt", fetcher);
    assert.equal(result.status, "error");
    assert.ok(result.message);
  }
});
