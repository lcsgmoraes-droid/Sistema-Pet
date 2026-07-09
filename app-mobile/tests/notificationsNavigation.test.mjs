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

test("extrai produto da notificacao de estoque por produto_id ou product_id", () => {
  const { stockNotificationToProductId } = carregarModuloTs(
    "src/utils/notificationNavigation.ts",
  );

  assert.equal(
    stockNotificationToProductId({
      source: "stock_waitlist",
      kind: "stock_available",
      produto_id: "6089",
    }),
    6089,
  );
  assert.equal(
    stockNotificationToProductId({
      source: "stock_waitlist",
      kind: "stock_available",
      product_id: 1715,
    }),
    1715,
  );
  assert.equal(stockNotificationToProductId({ source: "order" }), null);
  assert.equal(
    stockNotificationToProductId({
      source: "stock_waitlist",
      kind: "stock_available",
      produto_id: "abc",
    }),
    null,
  );
});

test("central de notificacoes mobile chama endpoints do app", () => {
  const serviceSource = readFileSync(
    path.resolve(__dirname, "../src/services/appNotifications.service.ts"),
    "utf8",
  );
  const screenSource = readFileSync(
    path.resolve(__dirname, "../src/screens/notifications/NotificationsScreen.tsx"),
    "utf8",
  );

  assert.match(serviceSource, /api\.get\(["']\/app\/notificacoes["']\)/);
  assert.match(serviceSource, /api\.post\(`\/app\/notificacoes\/\$\{id\}\/lida`\)/);
  assert.match(serviceSource, /api\.delete\(["']\/app\/notificacoes["']\)/);
  assert.match(screenSource, /limparNotificacoesApp/);
  assert.match(screenSource, /markNotificationAsRead/);
  assert.match(screenSource, /stockNotificationToProductId/);
});
