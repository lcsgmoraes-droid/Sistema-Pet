import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import path from "node:path";
import vm from "node:vm";
import ts from "typescript";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);

function carregarModuloTs(relativo) {
  const arquivo = path.resolve(__dirname, "..", relativo);
  const fonte = readFileSync(arquivo, "utf8");
  const { outputText } = ts.transpileModule(fonte, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
    },
  });
  const module = { exports: {} };
  vm.runInNewContext(
    outputText,
    {
      module,
      exports: module.exports,
      require,
    },
    { filename: arquivo },
  );
  return module.exports;
}

test("identifica retorno de email confirmado vindo do deep link", () => {
  const { isEmailVerificationSuccess } = carregarModuloTs(
    "src/utils/emailVerificationLoginLink.ts",
  );

  assert.equal(isEmailVerificationSuccess({ emailVerified: "1" }), true);
  assert.equal(isEmailVerificationSuccess({ emailVerified: "true" }), true);
  assert.equal(isEmailVerificationSuccess({ emailVerified: true }), true);
  assert.equal(isEmailVerificationSuccess({}), false);
});

test("normaliza email recebido no deep link para preencher o login", () => {
  const { normalizeVerifiedEmailParam } = carregarModuloTs(
    "src/utils/emailVerificationLoginLink.ts",
  );

  assert.equal(
    normalizeVerifiedEmailParam(" JulianaDuarteFS1990@gmail.com "),
    "julianaduartefs1990@gmail.com",
  );
  assert.equal(normalizeVerifiedEmailParam(null), "");
});

test("navegacao e login mobile mostram sucesso de confirmacao", () => {
  const navigatorSource = readFileSync(
    path.resolve(__dirname, "../src/navigation/AppNavigator.tsx"),
    "utf8",
  );
  const loginSource = readFileSync(
    path.resolve(__dirname, "../src/screens/auth/LoginScreen.tsx"),
    "utf8",
  );

  assert.match(navigatorSource, /Login:\s*["']login["']/);
  assert.match(loginSource, /isEmailVerificationSuccess/);
  assert.match(loginSource, /E-mail confirmado/);
});
