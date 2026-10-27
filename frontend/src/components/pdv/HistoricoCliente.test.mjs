import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
  elementText,
} from "../../../scripts/helpers/reactControllerHarness.mjs";

function preparar(get) {
  const mocks = new Map([
    ["lucide-react", {}],
    ["react-hot-toast", { toast: { error() {} } }],
    ["../../api", { __esModule: true, default: { get } }],
    ["../../utils/formatters", { formatMoneyBRL: (value) => String(value) }],
  ]);
  for (const [modulo, componente] of [
    ["../ui/CustomerIdentity", "CustomerIdentity"],
    ["../ui/SaleReference", "SaleReference"],
    ["../v2/BotaoInteracao/BotaoInteracao", "BotaoInteracao"],
    ["../v2/BotaoCancelar/BotaoCancelar", "BotaoCancelar"],
    ["../v2/InputCombobox/InputCombobox", "InputCombobox"],
  ])
    mocks.set(modulo, { __esModule: true, default: componente });
  return createControllerHarness(
    fileURLToPath(new URL("./HistoricoCliente.jsx", import.meta.url)),
    {
      props: { clienteId: 2292, onClose() {} },
      mocks,
    },
  );
}

test("histórico solicita páginas e filtra no servidor, voltando à primeira página", async () => {
  const chamadas = [];
  const harness = preparar(async (url, config) => {
    chamadas.push({ url, params: { ...config.params } });
    return {
      data: {
        vendas: [],
        total_compras: 45,
        paginacao: {
          total_itens: 45,
          total_paginas: 3,
          tem_proxima: true,
          tem_anterior: config.params.page > 1,
        },
      },
    };
  });
  await harness.settle();
  assert.equal(chamadas[0].params.per_page, 20);
  const proxima = elements(harness.tree).find(
    (node) => node.type === "BotaoInteracao" && elementText(node) === "Próxima",
  );
  await harness.act(() => proxima.props.onClick());
  assert.equal(chamadas.at(-1).params.page, 2);
  const filtro = elements(harness.tree).find((node) => node.type === "InputCombobox");
  await harness.act(() => filtro.props.onChange("parcial"));
  assert.deepEqual(chamadas.at(-1).params, { page: 1, per_page: 20, status_pagamento: "parcial" });
});

test("timeout mantém erro visível e permite tentar novamente", async () => {
  let chamadas = 0;
  const harness = preparar(async () => {
    chamadas++;
    if (chamadas === 1) throw new Error("timeout");
    return { data: { vendas: [], paginacao: {} } };
  });
  await harness.settle();
  assert.match(elementText(harness.tree), /Não foi possível carregar/);
  const retentar = elements(harness.tree).find((node) => node.type === "BotaoInteracao");
  await harness.act(() => retentar.props.onClick());
  assert.equal(chamadas, 2);
  assert.doesNotMatch(elementText(harness.tree), /Não foi possível carregar/);
});
