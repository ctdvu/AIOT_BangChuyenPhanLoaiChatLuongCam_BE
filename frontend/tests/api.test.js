import test from "node:test";
import assert from "node:assert/strict";
import { getAuthToken, setAuthToken, clearAuthToken } from "../src/api.js";

test("auth token storage management", () => {
  clearAuthToken();
  assert.equal(getAuthToken(), null);

  setAuthToken("test-jwt-token-12345");
  assert.equal(getAuthToken(), "test-jwt-token-12345");

  clearAuthToken();
  assert.equal(getAuthToken(), null);
});
