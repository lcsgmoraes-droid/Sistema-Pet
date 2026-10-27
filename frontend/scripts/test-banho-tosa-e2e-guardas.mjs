import assert from "node:assert/strict";
import test from "node:test";
import { URL } from "node:url";
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

// O destino remoto existe apenas como entrada rejeitada; nenhuma requisição é feita.
const subdominioRemoto = new URL("http://localhost:5173");
subdominioRemoto.hostname = "localhost.exemplo.com";

for (const [caso, url] of [
  ["domínio de produção", "https://corepet.com.br"],
  ["localhost usado como subdomínio remoto", subdominioRemoto.href],
  ["origem sem porta", "http://127.0.0.1"],
  ["HTTPS local", "https://localhost:5173"],
  ["caminho adicional", "http://localhost:5173/api"],
  ["parâmetro de consulta", "http://localhost:5173?destino=remoto"],
  ["fragmento", "http://localhost:5173#remoto"],
  ["credenciais na URL", "http://operador:teste@localhost:5173"],
]) {
  test(`recusa ${caso}`, () => {
    assert.throws(() => urlLocal(url, "E2E_BASE_URL"));
  });
}
