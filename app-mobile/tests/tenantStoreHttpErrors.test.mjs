import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import path from "node:path";
import vm from "node:vm";
import ts from "typescript";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const requireFromTest = createRequire(import.meta.url);

function carregarTenantStore(fetchImpl) {
  const arquivo = path.resolve(__dirname, "..", "src/store/tenant.store.ts");
  const fonte = readFileSync(arquivo, "utf8");
  const { outputText } = ts.transpileModule(fonte, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
      esModuleInterop: true,
    },
  });

  const module = { exports: {} };
  const estadoSeguro = new Map();

  function requireMock(specifier) {
    if (specifier === "expo-secure-store") {
      return {
        getItemAsync: async (key) => estadoSeguro.get(key) ?? null,
        setItemAsync: async (key, value) => estadoSeguro.set(key, value),
        deleteItemAsync: async (key) => estadoSeguro.delete(key),
      };
    }

    if (specifier === "react-native") {
      return { Linking: { getInitialURL: async () => null } };
    }

    if (specifier === "zustand") {
      return {
        create: () => (initializer) => {
          let state;
          const set = (patch) => {
            state = { ...state, ...patch };
          };
          state = initializer(set);
          const store = () => state;
          store.getState = () => state;
          return store;
        },
      };
    }

    if (specifier === "../config") {
      return { API_BASE_URL: "https://corepet.test/api" };
    }

    return requireFromTest(specifier);
  }

  vm.runInNewContext(
    outputText,
    {
      module,
      exports: module.exports,
      require: requireMock,
      URL,
      URLSearchParams,
      fetch: fetchImpl,
    },
    { filename: arquivo },
  );

  return module.exports.useTenantStore.getState();
}

function response(status, body = {}) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  };
}

test("buscar loja por codigo informa indisponibilidade quando API retorna 502", async () => {
  const store = carregarTenantStore(async () => response(502));

  await assert.rejects(
    () => store.buscarPorSlug("atacadao"),
    /temporariamente indisponivel/i,
  );
});

test("buscar lojas por localidade nao transforma 502 em lista vazia", async () => {
  const store = carregarTenantStore(async () => response(502));

  await assert.rejects(
    () => store.buscarPorLocalidade("Presidente Prudente", "SP"),
    /temporariamente indisponivel/i,
  );
});
