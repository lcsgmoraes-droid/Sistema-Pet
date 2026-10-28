const assert = require("node:assert/strict");
const { readFileSync, realpathSync } = require("node:fs");
const { resolve } = require("node:path");
const test = require("node:test");
const { compileFunction } = require("node:vm");
const ts = require("typescript");

const sourceRoot = realpathSync(resolve(__dirname, "../src/screens/benefits"));
const allowedSources = new Set([
  resolve(sourceRoot, "BeneficiosScreen.tsx"),
  resolve(sourceRoot, "beneficios/BeneficiosUtils.ts"),
  resolve(sourceRoot, "beneficios/BeneficiosStampAndLevelsSections.tsx"),
]);

function carregar(relativePath, mocks = {}) {
  const filename = resolve(sourceRoot, relativePath);
  if (!allowedSources.has(filename) || realpathSync(filename) !== filename) {
    throw new Error("O harness aceita somente os três arquivos locais de benefícios autorizados.");
  }
  const { outputText, diagnostics } = ts.transpileModule(readFileSync(filename, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.React, esModuleInterop: true },
    fileName: filename,
    reportDiagnostics: true,
  });
  assert.equal(diagnostics.filter((item) => item.category === ts.DiagnosticCategory.Error).length, 0);
  const module = { exports: {} };
  const requireMock = (name) => {
    if (!Object.hasOwn(mocks, name)) throw new Error(`Importação inesperada no teste: ${name}`);
    return mocks[name];
  };
  // Compila apenas fonte fixa da whitelist acima, com imports explicitamente simulados.
  compileFunction(outputText, ["require", "module", "exports"], { filename })(
    requireMock,
    module,
    module.exports,
  );
  return module.exports;
}

const utils = carregar("beneficios/BeneficiosUtils.ts");
const React = {
  createElement: (type, props, ...children) => ({ type, props: { ...props, children } }),
  useState: (initial) => [initial, () => {}],
  useRef: (initial) => ({ current: initial }),
  useCallback: (callback) => callback,
};
const styles = { beneficiosStyles: new Proxy({}, { get: (_, name) => String(name) }) };
const theme = { CORES: { pontos: "#123", erro: "#900" }, ESPACO: {} };
function nos(node) {
  if (!node || typeof node !== "object") return [];
  if (Array.isArray(node)) return node.flatMap(nos);
  return [node, ...nos(node.props?.children)];
}
function texto(node) {
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(texto).join("");
  return node ? texto(node.props?.children) : "";
}

test("carimbo manual aparece no cartão sem compras ou progresso de ranking", () => {
  const { BeneficiosStampSection } = carregar("beneficios/BeneficiosStampAndLevelsSections.tsx", {
    react: React,
    "@expo/vector-icons": { Ionicons: "Ionicons" },
    "react-native": { Text: "Text", TouchableOpacity: "TouchableOpacity", View: "View" },
    "../../../theme": theme,
    "./BeneficiosStyles": styles,
    "./BeneficiosUtils": utils,
  });
  const dados = utils.normalizarBeneficios({
    carimbos: { total_geral: 1, carimbos_no_cartao: 1, carimbos_ativos_brutos: 1, meta: 10 },
    ranking: { total_purchases: 0 },
  });
  const tree = BeneficiosStampSection({ carimbos: dados.carimbos });
  assert.equal(nos(tree).filter((node) => node.type === "Ionicons" && node.props.name === "paw").length, 1);
  assert.match(texto(tree), /1\/10 carimbos/);
  assert.match(texto(tree), /Saldo atual: 1/);
});

test("voltar à tela consulta novamente os benefícios", async () => {
  let aoFocar;
  const chamadas = [];
  const placeholder = { default: "Componente" };
  const { default: BeneficiosScreen } = carregar("BeneficiosScreen.tsx", {
    react: React,
    "@expo/vector-icons": { Ionicons: "Ionicons" },
    "@react-navigation/native": { useNavigation: () => ({}), useFocusEffect: (callback) => { aoFocar = callback; } },
    "react-native": { ActivityIndicator: "ActivityIndicator", RefreshControl: "RefreshControl", ScrollView: "ScrollView", Text: "Text", TouchableOpacity: "TouchableOpacity", View: "View" },
    "./beneficios/BeneficiosCashbackSection": placeholder,
    "./beneficios/BeneficiosCouponsSection": placeholder,
    "./beneficios/BeneficiosRankingSection": placeholder,
    "./beneficios/BeneficiosStyles": styles,
    "./beneficios/BeneficiosStampAndLevelsSections": placeholder,
    "./beneficios/BeneficiosUtils": utils,
    "../../services/api": { get: async (url) => { chamadas.push(url); return { data: {} }; } },
    "../../theme": theme,
  });
  BeneficiosScreen();
  const limpar = aoFocar();
  await Promise.resolve();
  limpar();
  aoFocar();
  await Promise.resolve();
  assert.deepEqual(chamadas, ["/ecommerce/auth/meus-beneficios", "/ecommerce/auth/meus-beneficios"]);
});
