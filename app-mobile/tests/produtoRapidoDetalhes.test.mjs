import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import ts from "typescript";

// Executa os hooks sem camera nativa: efeitos, respostas atrasadas e falhas sao controlados.
function carregarHook(arquivo, nome, dependencias) {
  const slots = [];
  const timers = new Map();
  let cursor = 0;
  let argumentos = [];
  let efeitoPendente = [];
  let timerId = 0;
  const react = {
    useState(inicial) {
      const pos = cursor++;
      if (!(pos in slots)) slots[pos] = typeof inicial === "function" ? inicial() : inicial;
      return [slots[pos], (valor) => { slots[pos] = typeof valor === "function" ? valor(slots[pos]) : valor; }];
    },
    useRef(inicial) { const pos = cursor++; return slots[pos] ??= { current: inicial }; },
    useEffect(callback, deps) {
      const pos = cursor++;
      if (!slots[pos] || deps.some((dep, i) => dep !== slots[pos].deps[i])) {
        slots[pos]?.cleanup?.();
        efeitoPendente.push(() => { slots[pos] = { deps, cleanup: callback() }; });
      }
    },
  };
  const modulo = { exports: {} };
  const fonte = readFileSync(new URL(`../src/screens/funcionario/produto/${arquivo}`, import.meta.url), "utf8");
  const compilado = ts.transpileModule(fonte, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
  Function("exports", "module", "require", "setTimeout", "clearTimeout", compilado)(
    modulo.exports, modulo,
    (id) => id === "react" ? react : dependencias[id] ?? (() => { throw new Error(`Mock ausente: ${id}`); })(),
    (callback) => { timers.set(++timerId, callback); return timerId; },
    (id) => timers.delete(id),
  );
  function render(...args) {
    if (args.length) argumentos = args;
    cursor = 0;
    efeitoPendente = [];
    const resultado = modulo.exports[nome](...argumentos);
    efeitoPendente.forEach((callback) => callback());
    return resultado;
  }
  return {
    render,
    get current() { return render(); },
    executarTimers() { const tarefas = [...timers.values()]; timers.clear(); return Promise.all(tarefas.map((fn) => fn())); },
  };
}

function fotosHook(upload, picker = {}) {
  let sequencia = 0;
  const imagem = async () => ({ canceled: false, assets: [{ uri: `file:///foto-${++sequencia}.jpg`, mimeType: "image/jpeg" }] });
  return carregarHook("useProdutoRapidoFotos.ts", "useProdutoRapidoFotos", {
    "expo-image-picker": {
      requestCameraPermissionsAsync: async () => ({ granted: true }),
      launchCameraAsync: imagem, launchImageLibraryAsync: imagem,
      UIImagePickerPreferredAssetRepresentationMode: { Compatible: "compatible" }, ...picker,
    },
    "react-native": { Alert: { alert() {} }, Linking: { openSettings() {} } },
    "../../../services/funcionarioProdutos.service": { enviarFotoProdutoRapido: upload },
    "../../../utils/produtoRapido": { erroCadastroProduto: (_e, mensagem) => mensagem },
  });
}

test("fotos com envio parcial preservam pendencias e repetem somente as que falharam", async () => {
  const chamadas = [];
  let falhar = true;
  const hook = fotosHook(async (id, foto) => {
    chamadas.push([id, foto.uri]);
    if (foto.uri.endsWith("2.jpg") && falhar) throw new Error("offline");
  });
  await hook.current.adicionar("camera");
  await hook.current.adicionar("galeria");
  await hook.current.enviar(42);
  assert.equal(hook.current.fotos[0].enviada, true);
  assert.equal(hook.current.fotos[1].enviada, undefined);
  assert.equal(hook.current.pendentes, true);
  assert.match(hook.current.erro, /produto foi salvo/);
  falhar = false;
  await hook.current.enviar(42);
  assert.deepEqual(chamadas, [[42, "file:///foto-1.jpg"], [42, "file:///foto-2.jpg"], [42, "file:///foto-2.jpg"]]);
  assert.equal(hook.current.pendentes, false);
  assert.equal(hook.current.ocupado, false);
});

test("cancelar foto ou negar camera nao cria arquivo pendente", async () => {
  let cameraAberta = false;
  const hook = fotosHook(async () => {}, {
    requestCameraPermissionsAsync: async () => ({ granted: false }),
    launchCameraAsync: async () => { cameraAberta = true; },
    launchImageLibraryAsync: async () => ({ canceled: true }),
  });
  await hook.current.adicionar("camera");
  await hook.current.adicionar("galeria");
  assert.equal(cameraAberta, false);
  assert.equal(hook.current.fotos.length, 0);
  assert.equal(hook.current.ocupado, false);
});

test("limita cinco fotos, permite remover e evita repetir clique durante upload", async () => {
  let concluir;
  let envios = 0;
  const hook = fotosHook(async () => { envios++; await new Promise((resolve) => { concluir = resolve; }); });
  for (let i = 0; i < 6; i++) await hook.current.adicionar("camera");
  assert.equal(hook.current.fotos.length, 5);
  for (const foto of hook.current.fotos.slice(1)) hook.current.remover(foto.uri);
  assert.equal(hook.current.fotos.length, 1);
  const envio = hook.current.enviar(7);
  await hook.current.enviar(7);
  assert.equal(envios, 1);
  concluir();
  await envio;
  hook.current.limpar();
  assert.equal(hook.current.fotos.length, 0);
});

test("resposta atrasada de um SKU anterior nao altera disponibilidade do atual", async () => {
  let respostaAntiga;
  const hook = carregarHook("useSkuProdutoRapido.ts", "useSkuProdutoRapido", {
    "../../../services/funcionarioProdutos.service": { consultarSkuProdutoRapido: (codigo) => codigo === "ANTIGO"
      ? new Promise((resolve) => { respostaAntiga = resolve; })
      : Promise.resolve({ codigo, disponivel: true }) },
  });
  hook.render("ANTIGO");
  const antiga = hook.executarTimers();
  hook.render("NOVO");
  await hook.executarTimers();
  respostaAntiga({ codigo: "ANTIGO", disponivel: false });
  await antiga;
  assert.equal(hook.current.status, "disponivel");
  assert.equal(hook.render("").status, "automatico");
});
