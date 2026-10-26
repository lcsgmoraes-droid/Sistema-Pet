import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { compileFunction } from "node:vm";
import ts from "typescript";
import { isDynamicImportError, recoverFromChunkError } from "./chunkRecovery.js";

const CHUNK_ERROR = new Error("Failed to fetch dynamically imported module: /assets/route-old.js");
const STORAGE_KEY = "corepet:chunk-recovery";
const RETRY_PARAM = "__corepet_chunk_retry";

function browser({
  href = "https://corepet.test/produtos/analise?fornecedor=7&busca=a%20b#resultado",
  entry = "/assets/index-antigo.js",
  online = true,
  storage = new Map(),
  failRead = false,
  failWrite = false,
} = {}) {
  const navigations = [];
  const reloads = [];
  const runtime = {
    navigator: { onLine: online },
    document: {
      querySelector(selector) {
        assert.equal(selector, 'script[type="module"][src]');
        return entry ? { src: entry } : null;
      },
    },
    location: {
      href,
      replace: (url) => navigations.push(url),
      reload: () => reloads.push(true),
    },
    sessionStorage: {
      getItem(key) {
        if (failRead) throw new Error("Storage indisponível");
        return storage.get(key) ?? null;
      },
      setItem(key, value) {
        if (failWrite) throw new Error("Storage cheio");
        storage.set(key, value);
      },
    },
  };
  return { runtime, navigations, reloads, storage };
}

test("reconhece falhas de imports JS/CSS sem tratar erros comuns de API como atualização", () => {
  for (const message of [
    CHUNK_ERROR.message,
    "Importing a module script failed",
    "error loading dynamically imported module: /assets/route-old.js",
    "ChunkLoadError: Loading chunk 42 failed",
    "Unable to preload CSS for /assets/route-old.css",
  ]) {
    assert.equal(isDynamicImportError(new Error(message)), true);
  }
  for (const error of [new TypeError("Failed to fetch"), new Error("API retornou 500"), null]) {
    assert.equal(isDynamicImportError(error), false);
    const env = browser();
    assert.equal(recoverFromChunkError(error, env.runtime, 100_000), false);
    assert.deepEqual(env.navigations, []);
  }
});

test("navegação de recuperação preserva rota, filtros e âncora e força uma URL nova", () => {
  const env = browser();
  assert.equal(recoverFromChunkError(CHUNK_ERROR, env.runtime, 100_000), true);
  assert.equal(env.navigations.length, 1);
  const url = new URL(env.navigations[0]);
  assert.equal(url.origin, "https://corepet.test");
  assert.equal(url.pathname, "/produtos/analise");
  assert.equal(url.searchParams.get("fornecedor"), "7");
  assert.equal(url.searchParams.get("busca"), "a b");
  assert.equal(url.hash, "#resultado");
  assert.equal(url.searchParams.get(RETRY_PARAM), "/assets/index-antigo.js");
  assert.deepEqual(env.reloads, []);
});

test("uma mesma página e uma mesma versão não entram em recarregamento repetido", () => {
  const env = browser();
  assert.equal(recoverFromChunkError(CHUNK_ERROR, env.runtime, 100_000), true);
  assert.equal(recoverFromChunkError(CHUNK_ERROR, env.runtime, 500_000), false);
  assert.equal(env.navigations.length, 1);

  const sameVersion = browser({ storage: env.storage });
  assert.equal(recoverFromChunkError(CHUNK_ERROR, sameVersion.runtime, 500_000), false);
  assert.deepEqual(sameVersion.navigations, []);
});

test("troca de versão respeita intervalo curto e pode se recuperar antes dos antigos cinco minutos", () => {
  const env = browser();
  recoverFromChunkError(CHUNK_ERROR, env.runtime, 100_000);
  const tooSoon = browser({ entry: "/assets/index-novo.js", storage: env.storage });
  assert.equal(recoverFromChunkError(CHUNK_ERROR, tooSoon.runtime, 109_999), false);

  const nextVersion = browser({ entry: "/assets/index-novo.js", storage: env.storage });
  assert.equal(recoverFromChunkError(CHUNK_ERROR, nextVersion.runtime, 110_000), true);
  assert.equal(nextVersion.navigations.length, 1);
  assert.equal(
    new URL(nextVersion.navigations[0]).searchParams.get(RETRY_PARAM),
    "/assets/index-novo.js",
  );
});

test("offline não recarrega nem consome a tentativa da versão", () => {
  const env = browser({ online: false });
  assert.equal(recoverFromChunkError(CHUNK_ERROR, env.runtime, 100_000), false);
  assert.equal(env.storage.size, 0);
  assert.deepEqual(env.navigations, []);
  env.runtime.navigator.onLine = true;
  assert.equal(recoverFromChunkError(CHUNK_ERROR, env.runtime, 110_000), true);
});

test("URL de recuperação impede repetição mesmo quando storage está bloqueado ou corrompido", () => {
  for (const config of [
    { failRead: true, failWrite: true },
    { failWrite: true },
    { storage: new Map([[STORAGE_KEY, "JSON inválido"]]) },
  ]) {
    const first = browser(config);
    assert.equal(recoverFromChunkError(CHUNK_ERROR, first.runtime, 100_000), true);
    const afterNavigation = browser({ ...config, href: first.navigations[0] });
    assert.equal(recoverFromChunkError(CHUNK_ERROR, afterNavigation.runtime, 500_000), false);
    assert.deepEqual(afterNavigation.navigations, []);
  }
});

test("storage indisponível também impede loop quando a navegação já recebeu uma versão nova", () => {
  const first = browser({ failRead: true, failWrite: true });
  recoverFromChunkError(CHUNK_ERROR, first.runtime, 100_000);
  const next = browser({
    href: first.navigations[0],
    entry: "/assets/index-novo.js",
    failRead: true,
    failWrite: true,
  });
  assert.equal(recoverFromChunkError(CHUNK_ERROR, next.runtime, 500_000), false);
  assert.deepEqual(next.navigations, []);
});

test("sem script identificado usa guarda segura e localização inválida não gera falha adicional", () => {
  const missingEntry = browser({ entry: null });
  assert.equal(recoverFromChunkError(CHUNK_ERROR, missingEntry.runtime, 100_000), true);
  const afterNavigation = browser({ href: missingEntry.navigations[0], entry: null });
  assert.equal(recoverFromChunkError(CHUNK_ERROR, afterNavigation.runtime, 500_000), false);

  const invalidLocation = browser({ href: "endereço inválido" });
  assert.equal(recoverFromChunkError(CHUNK_ERROR, invalidLocation.runtime, 100_000), false);
  assert.deepEqual(invalidLocation.navigations, []);
});

// Run both real class implementations with explicit browser/component imports;
// importing a failure into a rendered route must invoke the shared recovery.
function loadBoundary(extension, runtime) {
  const path = fileURLToPath(new URL(`../components/ErrorBoundary.${extension}`, import.meta.url));
  class Component {
    constructor(props) {
      this.props = props;
    }
    setState(next) {
      this.state = { ...this.state, ...next };
    }
  }
  const react = { Component };
  const jsx = (type, props) => ({ type, props });
  const imports = new Map([
    ["react", { __esModule: true, default: react, Component }],
    ["react/jsx-runtime", { jsx, jsxs: jsx }],
    ["lucide-react", {}],
    ["./v2/BotaoCancelar/BotaoCancelar", { default: "BotaoCancelar" }],
    ["./v2/BotaoInteracao/BotaoInteracao", { default: "BotaoInteracao" }],
    [
      "../utils/chunkRecovery",
      {
        isDynamicImportError,
        recoverFromChunkError: (error) => recoverFromChunkError(error, runtime, 100_000),
      },
    ],
  ]);
  const { outputText, diagnostics } = ts.transpileModule(readFileSync(path, "utf8"), {
    fileName: path,
    reportDiagnostics: true,
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2022,
      jsx: ts.JsxEmit.ReactJSX,
      esModuleInterop: true,
    },
  });
  assert.equal(
    diagnostics?.filter((item) => item.category === ts.DiagnosticCategory.Error).length,
    0,
  );
  const module = { exports: {} };
  const requireMock = (name) => {
    assert.ok(imports.has(name), `Import inesperado: ${name}`);
    return imports.get(name);
  };
  compileFunction(outputText, ["require", "module", "exports", "window", "console"], {
    filename: path,
  })(requireMock, module, module.exports, runtime, { error() {} });
  return extension === "jsx" ? module.exports.default : module.exports.ErrorBoundary;
}

for (const extension of ["jsx", "tsx"]) {
  test(`ErrorBoundary.${extension} recupera import falho e mantém erros comuns sem navegação`, () => {
    const env = browser();
    const Boundary = loadBoundary(extension, env.runtime);
    const boundary = new Boundary({ children: "conteúdo" });
    boundary.componentDidCatch(new Error("Erro comum de renderização"), {});
    assert.deepEqual(env.navigations, []);
    boundary.componentDidCatch(CHUNK_ERROR, {});
    boundary.componentDidCatch(CHUNK_ERROR, {});
    assert.equal(env.navigations.length, 1);
    assert.deepEqual(env.reloads, []);
  });
}
