import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
  elementText,
} from "../../../scripts/helpers/reactControllerHarness.mjs";

const file = fileURLToPath(new URL("./IfoodPedidoPdvPilot.jsx", import.meta.url));
const controls = ["BotaoInteracao", "LinkPadrao"];
const stubs = new Map([
  ...controls.map((name) => [`../v2/${name}/${name}`, { __esModule: true, default: name }]),
  ["lucide-react", {}],
]);

function setup(bridge, extra = {}) {
  let imports = 0;
  const harness = createControllerHarness(file, {
    mocks: stubs,
    props: { bridge, onImport: () => imports++, ...extra },
  });
  return { harness, imports: () => imports };
}

test("piloto fica ausente sem habilitacao explicita do servidor", () => {
  assert.equal(setup(undefined).harness.tree, null);
  assert.equal(setup({ enabled: false, eligible: true }).harness.tree, null);
});

test("pedido elegivel exige acao explicita e nao abre pagamento nem finaliza", async () => {
  const env = setup({ enabled: true, eligible: true, status: "not_imported", sale_id: null });
  const button = elements(env.harness.tree).find((item) => item.type === "BotaoInteracao");
  assert.equal(elementText(button), "Enviar ao PDV de teste");
  assert.equal(env.imports(), 0);
  assert.equal(
    elements(env.harness.tree).some((item) => item.type === "LinkPadrao"),
    false,
  );
  await env.harness.act(() => button.props.onClick());
  assert.equal(env.imports(), 1);
  assert.match(elementText(env.harness.tree), /A baixa acontece ao finalizar a venda no PDV/);
});

test("pedido bloqueado exibe motivo e nao oferece importacao", () => {
  const env = setup({
    enabled: true,
    eligible: false,
    status: "blocked",
    reason: "Pedido contém item fora do SKU autorizado.",
  });
  assert.match(elementText(env.harness.tree), /Pedido contém item fora do SKU autorizado/);
  assert.equal(
    elements(env.harness.tree).some((item) => item.type === "BotaoInteracao"),
    false,
  );
});

test("venda reservada oferece somente abrir a venda existente", () => {
  const env = setup({
    enabled: true,
    eligible: true,
    status: "reserved",
    sale_id: 42,
    reserved_quantity: "1.000",
    stock_decreased: false,
  });
  assert.equal(
    elements(env.harness.tree).some((item) => item.type === "BotaoInteracao"),
    false,
  );
  const link = elements(env.harness.tree).find((item) => item.type === "LinkPadrao");
  assert.equal(link.props.to, "/pdv?venda=42");
  assert.match(elementText(env.harness.tree), /Estoque reservado no CorePet/);
  assert.match(elementText(env.harness.tree), /Não realizada/);
});

test("estado vendido usa a prova de baixa recebida e nao permite nova importacao", () => {
  const env = setup({
    enabled: true,
    eligible: true,
    status: "sold",
    sale_id: 42,
    reserved_quantity: "0",
    stock_decreased: true,
  });
  assert.match(elementText(env.harness.tree), /Venda finalizada no CorePet/);
  assert.match(elementText(env.harness.tree), /Registrada/);
  assert.equal(
    elements(env.harness.tree).some((item) => item.type === "BotaoInteracao"),
    false,
  );
});

test("ausencia de prova de reserva e baixa nao vira zero ou confirmacao", () => {
  const env = setup({
    enabled: true,
    eligible: false,
    status: "sold",
    sale_id: 42,
    reserved_quantity: null,
    stock_decreased: null,
  });
  const text = elementText(env.harness.tree);
  assert.match(text, /Reserva ativa deste pedido\s+Não informada/);
  assert.match(text, /Baixa de estoque\s+Não informada/);
  assert.doesNotMatch(text, /Registrada|baixa registrada/);
});
