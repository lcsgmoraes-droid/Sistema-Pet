import assert from "node:assert/strict";
import test from "node:test";
import { ambienteBanhoTosa, urlLocal } from "../tests/e2e/banho-tosa/ambiente.mjs";

test("suite sem autorizacao explicita nao cria identidade", () => {
  assert.equal(ambienteBanhoTosa({}), null);
});

test("defaults sao origens DEV locais com portas explicitas", () => {
  assert.deepEqual(ambienteBanhoTosa({ E2E_CREATE_TEST_IDENTITY: "1" }), {
    baseURL: "http://127.0.0.1:5173",
    apiURL: "http://127.0.0.1:8000",
  });
});

for (const url of [
  "https://corepet.com.br",
  "http://localhost.exemplo.com:5173",
  "http://127.0.0.1",
  "https://localhost:5173",
  "http://localhost:5173/api",
  "http://localhost:5173?destino=remoto",
  "http://localhost:5173#remoto",
  "http://operador:teste@localhost:5173",
]) {
  test(`recusa destino inseguro ${url.replace(/\/\/[^@]+@/, "//[redigido]@")}`, () => {
    assert.throws(() => urlLocal(url, "E2E_BASE_URL"));
  });
}
