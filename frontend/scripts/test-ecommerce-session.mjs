import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import {
  clearEcommerceTokens,
  getEcommerceAccessToken,
  getEcommerceRefreshToken,
  setEcommerceTokens,
} from "../src/auth/ecommerceTokenStorage.js";

const __dirname = dirname(fileURLToPath(import.meta.url));

class MemoryStorage {
  constructor() {
    this.map = new Map();
  }

  getItem(key) {
    return this.map.has(key) ? this.map.get(key) : null;
  }

  setItem(key, value) {
    this.map.set(key, String(value));
  }

  removeItem(key) {
    this.map.delete(key);
  }
}

globalThis.localStorage = new MemoryStorage();

setEcommerceTokens({
  accessToken: "access-cliente",
  refreshToken: "refresh-cliente",
});

assert.equal(getEcommerceAccessToken(), "access-cliente");
assert.equal(getEcommerceRefreshToken(), "refresh-cliente");

clearEcommerceTokens();

assert.equal(getEcommerceAccessToken(), "");
assert.equal(getEcommerceRefreshToken(), "");

const apiSource = readFileSync(resolve(__dirname, "../src/services/ecommerceApi.js"), "utf8");
const customerSource = readFileSync(
  resolve(__dirname, "../src/pages/ecommerce/useEcommerceCustomer.js"),
  "utf8",
);

assert.match(apiSource, /\/api\/ecommerce\/auth\/refresh/);
assert.match(apiSource, /refreshManager\.refreshAccessToken\(\)/);
assert.match(customerSource, /refreshToken:\s*response\?\.data\?\.refresh_token/);
assert.match(customerSource, /subscribeEcommerceSession/);
