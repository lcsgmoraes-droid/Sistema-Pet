import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import ts from "typescript";

function carregar(arquivo, dependencias = {}) {
  const fonte = readFileSync(new URL(`../src/${arquivo}`, import.meta.url), "utf8");
  const compilado = ts.transpileModule(fonte, { compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.React,
  } }).outputText;
  const modulo = { exports: {} };
  Function("exports", "module", "require", compilado)(modulo.exports, modulo, (id) => {
    if (!(id in dependencias)) throw new Error(`Dependencia sem mock: ${id}`);
    return dependencias[id];
  });
  return modulo.exports;
}

// Aciona a tela real com componentes nativos e rede controlados, sem aparelho.
function tela(servicos = {}) {
  const slots = [];
  let cursor = 0;
  const envios = [];
  const react = {
    createElement: (type, props, ...children) => ({ type, props: { ...props, children: children.flat(Infinity) } }),
    useState(inicial) {
      const pos = cursor++;
      if (!(pos in slots)) slots[pos] = typeof inicial === "function" ? inicial() : inicial;
      return [slots[pos], (valor) => { slots[pos] = valor; }];
    },
    useRef(inicial) { return slots[cursor++] ??= { current: inicial }; },
    useEffect() {},
  };
  const produto = (payload) => ({ ...payload, id: 17, codigo: payload.codigo || "APP-GERADO", codigo_barras: payload.codigo_barras || null, ativo: true, situacao: true });
  const componente = carregar("screens/funcionario/FuncionarioNovoProdutoScreen.tsx", {
    react: { ...react, default: react },
    "@expo/vector-icons": { Ionicons: "Ionicons" },
    "@react-navigation/native": { useIsFocused: () => true, useNavigation: () => ({ addListener() {} }) },
    "expo-camera": { useCameraPermissions: () => [{ granted: true }, async () => ({ granted: true })] },
    "react-native-safe-area-context": { useSafeAreaInsets: () => ({ top: 0, bottom: 0 }) },
    "react-native": Object.fromEntries(["ActivityIndicator", "Alert", "Linking", "Modal", "Text", "TextInput", "TouchableOpacity", "View"].map((nome) => [nome, nome])),
    "../../components/KeyboardSafeScrollView": { default: "Scroll" },
    "../../theme": { CORES: {} },
    "../../utils/format": { formatarMoeda: (valor) => String(valor) },
    "../../utils/produtoRapido": carregar("utils/produtoRapido.ts"),
    "./pdv/FuncionarioPdvScanner": { FuncionarioPdvScanner: "Scanner" },
    "./produto/NovoProdutoStyles": { novoProdutoStyles: {} },
    "./produto/ProdutoRapidoFotos": { ProdutoRapidoFotos: "Fotos" },
    "./produto/useSkuProdutoRapido": { useSkuProdutoRapido: () => ({ status: "disponivel", mensagem: "SKU disponível" }) },
    "./produto/useProdutoRapidoFotos": { useProdutoRapidoFotos: () => ({ fotos: [], ocupado: false, pendentes: false, enviar: async () => {}, limpar() {} }) },
    "../../services/funcionarioProdutos.service": {
      consultarCodigoProdutoRapido: async () => null,
      consultarSkuProdutoRapido: async (codigo) => ({ codigo: codigo.toUpperCase(), disponivel: true, produto: null }),
      criarProdutoRapido: async (payload) => { envios.push(payload); return produto(payload); },
      ...servicos,
    },
  }).default;
  function render() { cursor = 0; return componente(); }
  function elementos(no = render()) {
    return no && typeof no === "object" ? [no, ...no.props.children.flatMap((filho) => elementos(filho))] : [];
  }
  function texto(no) { return typeof no === "string" ? no : no?.props?.children?.map(texto).join("") || ""; }
  function encontrar(filtro) { const item = elementos().find(filtro); assert.ok(item, "Controle esperado deve estar visível"); return item; }
  return {
    envios,
    texto: () => texto(render()),
    input: (label) => encontrar((no) => no.type === "TextInput" && no.props.accessibilityLabel === label).props,
    clicar: async (label) => {
      const botao = encontrar((no) => no.type === "TouchableOpacity" && (no.props.accessibilityLabel === label || texto(no) === label));
      assert.equal(!!botao.props.disabled, false);
      await botao.props.onPress();
    },
  };
}

function preencherMinimo(app) {
  app.input("Nome do produto").onChangeText("Brinquedo artesanal");
  app.input("Preço de venda").onChangeText("1250");
}

test("cadastra sem barras e sem SKU e informa a ausência de EAN no resultado", async () => {
  const app = tela();
  await app.clicar("Adicionar sem código de barras");
  preencherMinimo(app);
  await app.clicar("Cadastrar produto");
  assert.equal(app.envios[0].codigo_barras, undefined);
  assert.equal(app.envios[0].codigo, undefined);
  assert.equal(app.envios[0].preco_venda, 12.5);
  assert.match(app.envios[0].chave_cadastro, /^[\da-f]{8}-(?:[\da-f]{4}-){3}[\da-f]{12}$/);
  assert.match(app.texto(), /Produto cadastrado!/);
  assert.match(app.texto(), /Código de barras: Não informado/);
});

test("inicia por SKU de 50 caracteres e preenche somente o código interno", async () => {
  const chamadas = [];
  const app = tela({ consultarSkuProdutoRapido: async (codigo) => {
    chamadas.push(codigo); return { codigo: codigo.toUpperCase(), disponivel: true, produto: null };
  } });
  await app.clicar("SKU / código interno");
  assert.equal(app.input("SKU para consulta").maxLength, 50);
  const sku = "sku/" + "a".repeat(46);
  app.input("SKU para consulta").onChangeText(sku);
  await app.clicar("Consultar SKU");
  assert.deepEqual(chamadas, [sku]);
  assert.equal(app.input("SKU do produto").value, sku.toUpperCase());
  assert.equal(app.input("Código de barras do produto").value, "");
  preencherMinimo(app);
  await app.clicar("Cadastrar produto");
  assert.equal(app.envios[0].codigo, sku.toUpperCase());
  assert.equal(app.envios[0].codigo_barras, undefined);
});

test("SKU existente com zeros à esquerda mostra o produto inativo", async () => {
  const app = tela({ consultarSkuProdutoRapido: async (codigo) => {
    assert.equal(codigo, "00123");
    return { codigo, disponivel: false, produto: { id: 2, codigo, nome: "Artesanal antigo", ativo: false, codigo_barras: null, preco_venda: 12, unidade: "UN" } };
  } });
  await app.clicar("SKU / código interno");
  app.input("SKU para consulta").onChangeText("00123");
  await app.clicar("Consultar SKU");
  assert.match(app.texto(), /Este produto já existe/);
  assert.match(app.texto(), /Produto inativo/);
  assert.equal(app.envios.length, 0);
});

test("busca por barras continua preenchendo EAN e permite removê-lo", async () => {
  const app = tela();
  app.input("Código de barras").onChangeText("7891234567890");
  await app.clicar("Consultar código");
  assert.equal(app.input("Código de barras do produto").value, "7891234567890");
  app.input("Código de barras do produto").onChangeText("");
  preencherMinimo(app);
  await app.clicar("Cadastrar produto");
  assert.equal(app.envios[0].codigo_barras, undefined);
});

test("falha na consulta de SKU mantém a busca e impede tratar erro como SKU livre", async () => {
  const app = tela({ consultarSkuProdutoRapido: async () => { throw new Error("offline"); } });
  await app.clicar("SKU / código interno");
  app.input("SKU para consulta").onChangeText("PET-1");
  await app.clicar("Consultar SKU");
  assert.equal(app.input("SKU para consulta").value, "PET-1");
  assert.match(app.texto(), /Não foi possível consultar o ERP/);
  assert.equal(app.envios.length, 0);
});

test("nova tentativa reutiliza a chave e outro produto recebe uma nova", async () => {
  const envios = [];
  const app = tela({ criarProdutoRapido: async (payload) => {
    envios.push(payload);
    if (envios.length === 1) throw new Error("timeout após gravar");
    return { ...payload, id: 10, codigo: "APP-GERADO", codigo_barras: null, ativo: true };
  } });
  await app.clicar("Adicionar sem código de barras");
  preencherMinimo(app);
  await app.clicar("Cadastrar produto");
  assert.match(app.texto(), /Seus dados foram mantidos/);
  await app.clicar("Cadastrar produto");
  assert.equal(envios[0].chave_cadastro, envios[1].chave_cadastro);
  await app.clicar("Cadastrar outro produto");
  await app.clicar("Adicionar sem código de barras");
  preencherMinimo(app);
  await app.clicar("Cadastrar produto");
  assert.notEqual(envios[1].chave_cadastro, envios[2].chave_cadastro);
});
