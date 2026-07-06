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

function carregarTenantStore({ apiGet, fetchImpl } = {}) {
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

    if (specifier === "../services/api") {
      return {
        __esModule: true,
        default: {
          get:
            apiGet ??
            (async () => {
              throw new Error("api.get nao configurado no teste");
            }),
        },
      };
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
      fetch:
        fetchImpl ??
        (async () => {
          throw new Error("fetch direto nao deve ser usado");
        }),
    },
    { filename: arquivo },
  );

  return module.exports.useTenantStore.getState();
}

function apiError(status, body = {}) {
  const error = new Error("Request failed");
  error.response = { status, data: body };
  return error;
}

test("buscar loja por codigo usa o cliente HTTP central", async () => {
  const chamadas = [];
  const tenant = {
    id: "tenant-1",
    slug: "atacadao",
    nome: "Atacadao",
    logo_url: null,
    cidade: "Presidente Prudente",
    uf: "SP",
  };
  const store = carregarTenantStore({
    apiGet: async (url) => {
      chamadas.push(url);
      return { data: tenant };
    },
  });

  const resultado = await store.buscarPorSlug("https://corepet.com.br/loja/atacadao");

  assert.deepEqual(resultado, tenant);
  assert.deepEqual(chamadas, ["/ecommerce/tenant-slug/atacadao"]);
});

test("buscar loja por codigo informa indisponibilidade quando API retorna 502", async () => {
  const store = carregarTenantStore({
    apiGet: async () => {
      throw apiError(502);
    },
  });

  await assert.rejects(
    () => store.buscarPorSlug("atacadao"),
    /temporariamente indisponivel/i,
  );
});

test("buscar lojas por localidade nao transforma 502 em lista vazia", async () => {
  const store = carregarTenantStore({
    apiGet: async () => {
      throw apiError(502);
    },
  });

  await assert.rejects(
    () => store.buscarPorLocalidade("Presidente Prudente", "SP"),
    /temporariamente indisponivel/i,
  );
});
