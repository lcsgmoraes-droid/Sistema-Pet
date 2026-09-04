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

test("distingue envio real de resposta para conta inexistente", () => {
  const { passwordResetEmailWasSent } = carregarModuloTs(
    "src/utils/passwordRecovery.ts",
  );

  assert.equal(passwordResetEmailWasSent({ expires_in_minutes: 30 }), true);
  assert.equal(passwordResetEmailWasSent({}), false);
  assert.equal(passwordResetEmailWasSent(null), false);
});

test("recuperacao avisa conta nao cadastrada e oferece cadastro", () => {
  const source = readFileSync(
    path.resolve(__dirname, "../src/screens/auth/ForgotPasswordScreen.tsx"),
    "utf8",
  );

  assert.match(source, /passwordResetEmailWasSent\(data\)/);
  assert.match(source, /Conta não cadastrada/);
  assert.match(source, /Criar conta/);
  assert.match(source, /navigation\.navigate\(['"]Register['"]\)/);
});
