import fs from "node:fs";
import path from "node:path";
import process from "node:process";

const root = process.cwd();

function read(relativePath) {
  return fs.readFileSync(path.join(root, relativePath), "utf8");
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function lineCount(relativePath) {
  return read(relativePath).split(/\r?\n/).length;
}

const expectedFiles = [
  "src/pages/configuracoes/EntregasConfig.jsx",
  "src/pages/configuracoes/entregasConfig/useEntregasConfigController.js",
  "src/pages/configuracoes/entregasConfig/entregasConfigUtils.js",
  "src/pages/configuracoes/entregasConfig/EntregadorPadraoSection.jsx",
  "src/pages/configuracoes/entregasConfig/EnderecoLojaSection.jsx",
  "src/pages/configuracoes/entregasConfig/RegrasComerciaisSection.jsx",
  "src/pages/configuracoes/entregasConfig/MetodoDistanciaSection.jsx",
];

for (const relativePath of expectedFiles) {
  assert(
    fs.existsSync(path.join(root, relativePath)),
    `Missing delivery config file: ${relativePath}`,
  );
  assert(lineCount(relativePath) <= 420, `${relativePath} should stay at or below 420 lines`);
}

const facade = read("src/pages/configuracoes/EntregasConfig.jsx");
assert(
  facade.includes("useEntregasConfigController"),
  "Delivery config page should use its controller",
);
assert(
  facade.includes("EntregadorPadraoSection"),
  "Delivery config page should compose driver settings",
);
assert(
  facade.includes("EnderecoLojaSection"),
  "Delivery config page should compose address settings",
);
assert(
  facade.includes("RegrasComerciaisSection"),
  "Delivery config page should compose pricing settings",
);
assert(
  facade.includes("MetodoDistanciaSection"),
  "Delivery config page should compose distance settings",
);
assert(!facade.includes("api."), "Delivery config page should not own API calls");

const featureSource = expectedFiles.map(read).join("\n");
for (const literal of [
  "/configuracoes/entregas",
  "/clientes/",
  "https://viacep.com.br/ws/",
  "Informe um valor por km maior que zero.",
  "Para cobrar por distância, complete pelo menos logradouro e número da loja.",
  "Organize as faixas em ordem crescente, sem repetir a distância.",
  "Configurações salvas com sucesso",
  "Preço fixo por faixa de distância",
  "GPS via App Mobile",
]) {
  assert(featureSource.includes(literal), `Missing delivery config behavior: ${literal}`);
}

const utilsUrl = new URL(
  "../src/pages/configuracoes/entregasConfig/entregasConfigUtils.js",
  import.meta.url,
);
const {
  buildEntregasPayload,
  createInitialEntregasForm,
  nextTierLimit,
  normalizeEntregadores,
  normalizeEntregasConfig,
  validateEntregasForm,
} = await import(utilsUrl);

assert(nextTierLimit([]) === "1", "First distance tier should start at 1 km");
assert(nextTierLimit([{ ate_km: "2" }]) === "3", "Next distance tier should follow the last limit");

const initialForm = createInitialEntregasForm();
assert(initialForm.modalidade_cobranca === "fixa", "Default billing mode should remain fixed");
assert(initialForm.entrega_ativa === true, "Delivery should remain enabled by default");
assert(initialForm.retirada_ativa === true, "Pickup should remain enabled by default");

const normalized = normalizeEntregasConfig({
  entrega_ativa: false,
  retirada_ativa: false,
  faixas_distancia: [{ ate_km: 2.5, valor: "8.49" }],
});
assert(normalized.entrega_ativa === false, "Backend delivery flag should be preserved");
assert(normalized.retirada_ativa === false, "Backend pickup flag should be preserved");
assert(normalized.faixas_distancia[0].ate_km === "2.5", "Tier distance should be editable as text");
assert(normalized.faixas_distancia[0].valor === 8.49, "Tier price should be normalized as number");
assert(
  normalizeEntregadores({ clientes: [{ id: 1 }] })[0].id === 1,
  "Customer-list responses should expose delivery drivers",
);
assert(
  normalizeEntregadores({ items: [{ id: 2 }] })[0].id === 2,
  "Paginated responses should expose delivery drivers",
);
assert(
  normalizeEntregadores(null).length === 0,
  "Invalid driver responses should become an empty list",
);

assert(
  validateEntregasForm({ ...initialForm, modalidade_cobranca: "por_km" }) ===
    "Informe um valor por km maior que zero.",
  "Per-km pricing should require a positive price",
);
assert(
  validateEntregasForm({
    ...initialForm,
    modalidade_cobranca: "por_km",
    valor_por_km_cobrado: 2,
  }) === "Para cobrar por distância, complete pelo menos logradouro e número da loja.",
  "Distance pricing should require the store address",
);
assert(
  validateEntregasForm({
    ...initialForm,
    modalidade_cobranca: "por_faixa",
    logradouro: "Rua A",
    numero: "10",
    faixas_distancia: [{ ate_km: "0", valor: -1 }],
  }) === "Preencha todas as faixas com uma distância maior que zero e um preço válido.",
  "Invalid distance tiers should remain blocked",
);
assert(
  validateEntregasForm({
    ...initialForm,
    modalidade_cobranca: "por_faixa",
    logradouro: "Rua A",
    numero: "10",
    faixas_distancia: [
      { ate_km: "3", valor: 5 },
      { ate_km: "2", valor: 6 },
    ],
  }) === "Organize as faixas em ordem crescente, sem repetir a distância.",
  "Distance tiers should remain strictly increasing",
);

const payload = buildEntregasPayload({
  ...initialForm,
  entregador_padrao_id: "",
  prazo_entrega_texto: "  Entrega em até 2 horas  ",
  distancia_maxima_entrega_km: "12.5",
  frete_gratis_acima: 0,
});
assert(payload.entregador_padrao_id === null, "Empty default driver should be sent as null");
assert(
  payload.prazo_entrega_texto === "Entrega em até 2 horas",
  "Delivery estimate should be trimmed",
);
assert(payload.distancia_maxima_entrega_km === 12.5, "Positive distance limit should be numeric");
assert(payload.frete_gratis_acima === null, "Disabled free shipping should be sent as null");
assert(payload.valor_por_km_cobrado === null, "Fixed pricing should not send a per-km price");

console.log("Delivery config refactor contract OK");
