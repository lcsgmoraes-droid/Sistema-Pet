import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import path from "node:path";

import { buildCorePetLoginUrl } from "./emailVerificationLinks.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

test("monta deep link para abrir o login do app apos confirmar email", () => {
  const url = buildCorePetLoginUrl(" JulianaDuarteFS1990@gmail.com ");

  assert.equal(url, "corepet://app/login?emailVerified=1&email=julianaduartefs1990%40gmail.com");
});

test("pagina de verificacao redireciona fluxo do app para o login confirmado", () => {
  const source = readFileSync(path.join(__dirname, "EmailVerification.jsx"), "utf8");

  assert.match(source, /buildCorePetLoginUrl/);
  assert.match(source, /window\.location\.assign/);
  assert.match(source, /Abrindo o app para login/);
});
