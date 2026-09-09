import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import ts from "typescript";

function executar(arquivo, deps, dev = false) {
  const slots = [];
  let cursor = 0;
  let efeitos = [];
  const react = {
    createElement: (type, props, ...children) => ({ type, props: { ...props, children } }),
    useState(inicial) {
      const pos = cursor++;
      if (!(pos in slots)) slots[pos] = inicial;
      return [slots[pos], (v) => { slots[pos] = v; }];
    },
    useRef(inicial) { return slots[cursor++] ??= { current: inicial }; },
    useCallback(fn) { cursor++; return fn; },
    useEffect(fn, deps) {
      const pos = cursor++;
      if (!slots[pos] || deps.some((v, i) => v !== slots[pos].deps[i])) {
        slots[pos]?.cleanup?.();
        efeitos.push(() => { slots[pos] = { deps, cleanup: fn() }; });
      }
    },
  };
  // Callbacks devem ter identidade estável, como no React, para testar listeners.
  react.useCallback = (fn, deps) => {
    const pos = cursor++;
    if (!slots[pos] || deps.some((v, i) => v !== slots[pos].deps[i])) slots[pos] = { deps, fn };
    return slots[pos].fn;
  };
  const codigo = ts.transpileModule(readFileSync(new URL(`../src/${arquivo}`, import.meta.url), "utf8"), {
    compilerOptions: { jsx: ts.JsxEmit.React, module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, esModuleInterop: true },
  }).outputText;
  const modulo = { exports: {} };
  Function("module", "exports", "require", "__DEV__", "console", codigo)(modulo, modulo.exports,
    (id) => { if (id === "react") return react; assert.ok(id in deps, id); return deps[id]; }, dev, { info() {} });
  return {
    render() {
      cursor = 0; efeitos = [];
      const resultado = (modulo.exports.default ?? modulo.exports.useAppUpdates)();
      efeitos.forEach((fn) => fn());
      return resultado;
    },
    cleanup() { slots.forEach((s) => s?.cleanup?.()); },
  };
}

const esperar = () => new Promise((resolve) => setImmediate(resolve));
function hook({ enabled = true, dev = false, startup = false, check, fetch, reload } = {}) {
  const chamadas = { check: 0, fetch: 0, reload: 0 };
  const estado = { currentlyRunning: { updateId: "em-uso", runtimeVersion: "1.0.4" },
    isStartupProcedureRunning: startup, isUpdatePending: false, isChecking: false, isDownloading: false, isRestarting: false };
  const listeners = new Set();
  const nativo = { currentState: "active", addEventListener(_event, fn) { listeners.add(fn); return { remove: () => listeners.delete(fn) }; } };
  const e = executar("hooks/useAppUpdates.ts", {
    "react-native": { AppState: nativo },
    "expo-updates": {
      isEnabled: enabled, useUpdates: () => ({ ...estado }),
      UpdateCheckResultNotAvailableReason: { UPDATE_PREVIOUSLY_FAILED: "failed" },
      checkForUpdateAsync: async () => { chamadas.check++; return check ? check() : { isAvailable: false }; },
      fetchUpdateAsync: async () => { chamadas.fetch++; return fetch ? fetch() : { isNew: true }; },
      reloadAsync: async () => { chamadas.reload++; if (reload) await reload(); },
    },
  }, dev);
  return { ...e, chamadas, estado, listeners, foreground() {
    for (const fn of listeners) fn("background");
    for (const fn of listeners) fn("active");
  } };
}

test("downloads ficam pendentes sem reiniciar o trabalho; aplicar só recarrega uma vez", async () => {
  const h = hook({ check: () => ({ isAvailable: true }) });
  h.render(); await esperar();
  assert.equal(h.render().pronto, true);
  assert.deepEqual(h.chamadas, { check: 1, fetch: 1, reload: 0 });
  await h.render().verificar(true);
  await h.render().aplicar();
  await h.render().aplicar();
  assert.equal(h.chamadas.reload, 1);
});

test("download nativo durante startup aparece como pronto sem baixar outra vez", async () => {
  const h = hook({ startup: true });
  h.render();
  await h.render().verificar(true);
  assert.equal(h.chamadas.check, 0);
  Object.assign(h.estado, { isStartupProcedureRunning: false, isUpdatePending: true });
  assert.equal(h.render().pronto, true);
  await h.render().aplicar();
  assert.deepEqual(h.chamadas, { check: 0, fetch: 0, reload: 1 });
});

test("voltar ao app verifica após intervalo; retorno rápido não repete e manual força consulta", async () => {
  const h = hook({ startup: true });
  h.render();
  Object.assign(h.estado, { isStartupProcedureRunning: false, lastCheckForUpdateTimeSinceRestart: new Date() });
  h.render(); h.foreground(); await esperar();
  assert.equal(h.chamadas.check, 0);
  h.estado.lastCheckForUpdateTimeSinceRestart = new Date(Date.now() - 16 * 60 * 1000);
  h.render(); h.foreground(); await esperar();
  assert.equal(h.chamadas.check, 1);
  h.foreground(); await esperar();
  assert.equal(h.chamadas.check, 1);
  await h.render().verificar(true);
  assert.equal(h.chamadas.check, 2);
  h.cleanup(); assert.equal(h.listeners.size, 0);
});

test("consulta em andamento bloqueia toque repetido e não permite aplicar", async () => {
  let concluir;
  const h = hook({ check: () => new Promise((resolve) => { concluir = resolve; }) });
  h.render();
  await h.render().verificar(true);
  await h.render().aplicar();
  assert.equal(h.render().ocupado, true);
  concluir({ isAvailable: false }); await esperar();
  assert.equal(h.chamadas.check, 1);
  assert.equal(h.chamadas.reload, 0);
  assert.equal(h.render().status, "Nenhuma atualização disponível");
});

test("offline informa falha sem afirmar atualizado e permite nova tentativa", async () => {
  let offline = true;
  const h = hook({ check: () => { if (offline) throw Error("offline"); return { isAvailable: false }; } });
  h.render(); await esperar();
  assert.match(h.render().erro, /internet/);
  assert.notEqual(h.render().status, "Nenhuma atualização disponível");
  offline = false; await h.render().verificar(true);
  assert.equal(h.render().erro, null);
  assert.equal(h.render().status, "Nenhuma atualização disponível");
});

test("falha ao baixar não libera reinício e falha ao reiniciar preserva pacote pronto", async () => {
  const h = hook({ check: () => ({ isAvailable: true }), fetch: () => { throw Error("offline"); } });
  h.render(); await esperar(); await h.render().aplicar();
  assert.equal(h.render().pronto, false);
  assert.equal(h.chamadas.reload, 0);
  const r = hook({ check: () => ({ isAvailable: true }), reload: () => { throw Error("reload"); } });
  r.render(); await esperar(); await r.render().aplicar();
  assert.equal(r.render().pronto, true);
  assert.equal(r.render().ocupado, false);
  assert.match(r.render().erro, /reiniciar/);
});

test("respeita rollback e distingue atualização que falhou antes", async () => {
  const h = hook({ check: () => ({ isRollBackToEmbedded: true }), fetch: () => ({ isRollBackToEmbedded: true }) });
  h.render(); await esperar();
  assert.equal(h.render().pronto, true);
  assert.equal(h.chamadas.reload, 0);
  const r = hook({ check: () => ({ isAvailable: false, reason: "failed" }) });
  r.render(); await esperar();
  assert.match(r.render().erro, /suporte/);
});

test("Expo Go e desenvolvimento não chamam APIs de atualização", async () => {
  for (const opts of [{ enabled: false }, { dev: true }]) {
    const h = hook(opts); h.render(); h.foreground();
    await h.render().verificar(true); await h.render().aplicar();
    assert.equal(h.render().enabled, false);
    assert.deepEqual(h.chamadas, { check: 0, fetch: 0, reload: 0 });
  }
});

test("aplicar na interface exige confirmação e continuar trabalhando não reinicia", () => {
  let applied = 0;
  let confirmacao;
  const update = { enabled: true, pronto: true, versao: {}, verificar() {}, aplicar() { applied++; } };
  const componentes = Object.fromEntries(["ActivityIndicator", "Modal", "ScrollView", "Text", "TouchableOpacity", "View"].map((k) => [k, k]));
  const e = executar("components/AppUpdateBar.tsx", {
    "../hooks/useAppUpdates": { useAppUpdates: () => update },
    "@expo/vector-icons": { Ionicons: "Icon" },
    "react-native-safe-area-context": { SafeAreaView: "SafeAreaView" },
    "react-native": { ...componentes, StyleSheet: { create: (v) => v },
      Keyboard: { addListener: () => ({ remove() {} }) }, Alert: { alert: (...args) => { confirmacao = args; } } },
  });
  const nos = (n) => !n || typeof n !== "object" ? [] : [n, ...(n.props?.children ?? []).flat(Infinity).flatMap(nos)];
  const botao = (texto) => nos(e.render()).find((n) => n.type === "TouchableOpacity" && JSON.stringify(n.props.children).includes(texto)).props;
  botao("Continuar trabalhando").onPress(); assert.equal(applied, 0);
  botao("Aplicar atualização").onPress(); assert.equal(applied, 0);
  assert.match(confirmacao[1], /Salve qualquer alteração/);
  confirmacao[2].find((b) => b.text === "Reiniciar e aplicar").onPress();
  assert.equal(applied, 1);
});
