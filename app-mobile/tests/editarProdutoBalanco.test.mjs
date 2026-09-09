import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import ts from "typescript";

// Executa os handlers das telas com camera/API controladas, sem runtime nativo.
function tela(arquivo, deps, props = {}) {
  const slots = [];
  let cursor = 0;
  let efeitos = [];
  const react = {
    createElement: (type, props, ...children) => ({ type, props: { ...props, children } }),
    useState(inicial) {
      const pos = cursor++;
      if (!(pos in slots)) slots[pos] = inicial;
      return [slots[pos], (v) => { slots[pos] = typeof v === "function" ? v(slots[pos]) : v; }];
    },
    useRef(inicial) { const pos = cursor++; return slots[pos] ??= { current: inicial }; },
    useMemo(callback) { cursor++; return callback(); },
    useEffect(callback, deps) {
      const pos = cursor++;
      if (!slots[pos] || deps.some((d, i) => d !== slots[pos].deps[i])) {
        slots[pos]?.cleanup?.();
        efeitos.push(() => { slots[pos] = { deps, cleanup: callback() }; });
      }
    },
  };
  const nativo = Object.fromEntries(["ActivityIndicator", "Image", "Text", "TextInput", "TouchableOpacity", "View", "Modal"].map((v) => [v, v]));
  const comuns = {
    "react": react,
    "react-native": { ...nativo, StyleSheet: { create: (v) => v, absoluteFill: {} },
      Alert: { alert() {} }, Vibration: { vibrate() {} }, Keyboard: { dismiss() {} }, Linking: { openSettings() {} } },
    "@expo/vector-icons": { Ionicons: "Icon" },
    "@react-navigation/native": { useIsFocused: () => true },
    "react-native-safe-area-context": { SafeAreaView: "SafeAreaView" },
  };
  const codigo = ts.transpileModule(readFileSync(new URL(`../src/screens/funcionario/${arquivo}`, import.meta.url), "utf8"), {
    compilerOptions: { jsx: ts.JsxEmit.React, module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, esModuleInterop: true },
  }).outputText;
  const modulo = { exports: {} };
  Function("exports", "module", "require", "setTimeout", "clearTimeout", codigo)(modulo.exports, modulo, (id) => {
    if (id in deps) return deps[id];
    if (id in comuns) return comuns[id];
    if (id.endsWith("/theme")) return { CORES: {}, ESPACO: {}, FONTE: {}, RAIO: {}, SOMBRA: {} };
    if (id.endsWith("KeyboardSafeScrollView")) return "Scroll";
    if (id.endsWith("/utils/produtoRapido")) return { erroCadastroProduto: (e, fallback) => e?.response?.data?.detail || fallback };
    throw new Error(`Dependencia ausente: ${id}`);
  }, () => 1, () => {});
  function render() {
    cursor = 0;
    efeitos = [];
    const arvore = modulo.exports.default(props);
    efeitos.forEach((fn) => fn());
    return arvore;
  }
  function elementos(no = render()) {
    if (!no || typeof no !== "object") return [];
    return [no, ...[no.props?.children ?? []].flat(Infinity).flatMap((filho) => elementos(filho))];
  }
  return {
    render,
    find: (predicado) => { const el = elementos().find(predicado); assert.ok(el, "Elemento deve existir"); return el.props; },
    label: (label) => elementos().find((e) => e.props?.accessibilityLabel === label)?.props,
    button: (texto) => {
      const el = elementos().find((e) => e.type === "TouchableOpacity" && JSON.stringify(e.props.children).includes(texto));
      assert.ok(el, `Botao ${texto} deve existir`);
      return el.props;
    },
    has: (type) => elementos().some((e) => e.type === type),
  };
}

const original = { id: 42, nome: "Ração", codigo: "SKU42", codigo_barras: "7891234567890", descricao_curta: "Descrição existente" };
const esperar = () => new Promise((resolve) => setImmediate(resolve));

async function editor({ granted = true, carregar, salvar } = {}) {
  const chamadas = [];
  const salvos = [];
  let fechados = 0;
  const instancia = tela("produto/EditarProdutoBalanco.tsx", {
    "expo-camera": { CameraView: "Camera", useCameraPermissions: () => [{ granted }, async () => ({ granted })] },
    "../../../services/funcionarioProdutos.service": {
      obterCadastroProdutoFuncionario: carregar ?? (async () => original),
      atualizarCadastroProdutoFuncionario: async (id, payload) => {
        chamadas.push([id, payload]);
        return salvar ? salvar(id, payload) : { ...original, ...payload };
      },
    },
  }, { produtoId: 42, onClose: () => fechados++, onSaved: (p) => salvos.push(p) });
  instancia.render();
  await esperar();
  return { ...instancia, chamadas, salvos, get fechados() { return fechados; } };
}

test("camera preenche somente o EAN, ignora leitura repetida e salva apenas ao confirmar", async () => {
  const e = await editor();
  await e.label("Ler EAN com a câmera").onPress();
  const camera = e.find((n) => n.type === "Camera");
  camera.onBarcodeScanned({ data: "0012345678905" });
  camera.onBarcodeScanned({ data: "7899999999999" });
  assert.equal(e.label("EAN / código de barras").value, "0012345678905");
  assert.equal(e.label("Nome do produto").value, original.nome);
  assert.equal(e.chamadas.length, 0);
  await e.button("Salvar cadastro").onPress();
  assert.deepEqual(e.chamadas, [[42, { codigo_barras: "0012345678905" }]]);
  assert.equal(e.salvos[0].id, 42);
});

test("cancelar camera preserva campos e cancelar edicao nao chama API", async () => {
  const e = await editor();
  e.label("Nome do produto").onChangeText("Nome corrigido");
  await e.label("Ler EAN com a câmera").onPress();
  e.find((n) => n.type === "Modal").onRequestClose();
  assert.equal(e.fechados, 0);
  assert.equal(e.label("Nome do produto").value, "Nome corrigido");
  assert.equal(e.label("EAN / código de barras").value, original.codigo_barras);
  e.button("Cancelar").onPress();
  assert.equal(e.fechados, 1);
  assert.equal(e.chamadas.length, 0);
});

test("camera negada mantem digitacao disponivel; codigo invalido nao sobrescreve campo", async () => {
  const negado = await editor({ granted: false });
  await negado.label("Ler EAN com a câmera").onPress();
  assert.equal(negado.has("Camera"), false);
  negado.label("EAN / código de barras").onChangeText("12345678");
  await negado.button("Salvar cadastro").onPress();
  assert.equal(negado.salvos[0].codigo_barras, "12345678");
  const e = await editor();
  await e.label("Ler EAN com a câmera").onPress();
  e.find((n) => n.type === "Camera").onBarcodeScanned({ data: "https://site@qr" });
  assert.equal(e.label("EAN / código de barras").value, original.codigo_barras);
  assert.equal(e.chamadas.length, 0);
});

test("falha de salvamento preserva rascunho e permite corrigir e repetir", async () => {
  let falhar = true;
  const e = await editor({ salvar: async (_id, payload) => {
    if (falhar) throw { response: { data: { detail: "Código já pertence a outro produto" } } };
    return { ...original, ...payload };
  } });
  e.label("Nome do produto").onChangeText("Nome corrigido");
  e.label("EAN / código de barras").onChangeText("12345678");
  await e.button("Salvar cadastro").onPress();
  assert.equal(e.salvos.length, 0);
  assert.equal(e.label("Nome do produto").value, "Nome corrigido");
  assert.match(JSON.stringify(e.render()), /Código já pertence/);
  falhar = false;
  e.label("EAN / código de barras").onChangeText("87654321");
  await e.button("Salvar cadastro").onPress();
  assert.equal(e.salvos[0].codigo_barras, "87654321");
});

test("salvamento em andamento bloqueia toque duplo e fechamento", async () => {
  let concluir;
  const e = await editor({ salvar: () => new Promise((resolve) => { concluir = resolve; }) });
  e.label("Descrição complementar").onChangeText("Outra descrição");
  const onPress = e.button("Salvar cadastro").onPress;
  const pendente = onPress();
  await onPress();
  e.find((n) => n.type === "Modal").onRequestClose();
  assert.equal(e.chamadas.length, 1);
  assert.equal(e.fechados, 0);
  concluir({ ...original, descricao_curta: "Outra descrição" });
  await pendente;
  assert.equal(e.salvos.length, 1);
});

test("falha ao carregar exige nova leitura antes de permitir edicao", async () => {
  let leituras = 0;
  const e = await editor({ carregar: async () => {
    if (++leituras === 1) throw new Error("offline");
    return original;
  } });
  assert.equal(e.label("Nome do produto"), undefined);
  e.button("Tentar novamente").onPress();
  e.render();
  await esperar();
  assert.equal(e.label("Descrição complementar").value, original.descricao_curta);
});

test("voltar da edicao atualiza identificacao e preserva saldo, lote, validade e observacao", async () => {
  const b = tela("FuncionarioBalancoScreen.tsx", {
    "expo-camera": { CameraView: "Camera", useCameraPermissions: () => [{ granted: true }, async () => ({ granted: true })] },
    "../../services/funcionarioEstoque.service": { buscarProdutosFuncionario: async () => [{ ...original, unidade: "UN", permite_balanco: true }] },
    "../../utils/format": { formatarMoeda: () => "R$ 10,00" },
    "./produto/EditarProdutoBalanco": "Editor",
  });
  b.find((n) => n.props?.placeholder === "Buscar produto por nome, codigo ou barras").onChangeText("Ração");
  await b.find((n) => n.props?.returnKeyType === "search").onSubmitEditing();
  b.find((n) => n.type === "TouchableOpacity" && n.props.key === 42).onPress();
  b.find((n) => n.props?.placeholder === "Ex: 12").onChangeText("12,5");
  b.find((n) => n.props?.autoCapitalize === "characters").onChangeText("LOTE-A");
  b.find((n) => n.props?.placeholder === "DD/MM/AAAA ou AAAA-MM-DD").onChangeText("10/12/2026");
  b.find((n) => n.type === "TextInput" && n.props.multiline).onChangeText("Conferido");
  b.button("Editar cadastro").onPress();
  b.find((n) => n.type === "Editor").onSaved({ ...original, nome: "Nome corrigido", codigo_barras: "12345678" });
  assert.equal(b.has("Editor"), false);
  assert.equal(b.find((n) => n.props?.placeholder === "Ex: 12").value, "12,5");
  assert.equal(b.find((n) => n.props?.autoCapitalize === "characters").value, "LOTE-A");
  assert.equal(b.find((n) => n.props?.placeholder === "DD/MM/AAAA ou AAAA-MM-DD").value, "10/12/2026");
  assert.equal(b.find((n) => n.type === "TextInput" && n.props.multiline).value, "Conferido");
  assert.match(JSON.stringify(b.render()), /Nome corrigido/);
  assert.match(JSON.stringify(b.render()), /12345678/);
});
