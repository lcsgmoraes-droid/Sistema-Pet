import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
  elementText,
} from "../../../scripts/helpers/reactControllerHarness.mjs";

test("baixa reutiliza request_id após falha e troca a chave quando o valor muda", async () => {
  const envios = [];
  let chaves = 0;
  let fechamentos = 0;
  const api = {
    get: async () => ({
      data: {
        vendas: [
          {
            id: 11,
            numero_venda: "VEN-11",
            data_venda: "2026-10-18",
            total: 100,
            saldo_devedor: 100,
          },
        ],
        resumo: { total_vendas: 1, total_em_aberto: 100 },
      },
    }),
    post: async (_url, payload) => {
      envios.push(payload);
      if (envios.length < 3) throw { response: { data: { detail: "Tente novamente" } } };
      return {
        data: {
          vendas_quitadas: [],
          vendas_parciais: [],
          valor_total_baixado: payload.valor_total,
        },
      };
    },
  };
  const nomesV2 = [
    "BotaoCancelar",
    "BotaoInteracao",
    "InputCheckbox",
    "InputCombobox",
    "InputMoeda",
    "InputTexto",
    "InputTextoLongo",
  ];
  const harness = createControllerHarness(
    fileURLToPath(new URL("./VendasEmAberto.jsx", import.meta.url)),
    {
      mocks: new Map([
        ["../../api", api],
        [
          "lucide-react",
          Object.fromEntries(
            ["DollarSign", "CheckCircle", "AlertCircle", "History", "Loader"].map((name) => [
              name,
              name,
            ]),
          ),
        ],
        ["react-hot-toast", { toast: { success() {}, error() {} } }],
        ["../../contexts/ModulosContext", { useModulos: () => ({ moduloAtivo: () => false }) }],
        [
          "../../hooks/useShiftRangeSelection",
          {
            __esModule: true,
            default:
              ({ setSelectedIds }) =>
              (id) =>
                setSelectedIds([id]),
          },
        ],
        [
          "../clientes/ClienteBaixasLotePanel",
          { __esModule: true, default: "ClienteBaixasLotePanel" },
        ],
        ["../ui/CustomerIdentity", { __esModule: true, default: "CustomerIdentity" }],
        ["../ui/SaleReference", { __esModule: true, default: "SaleReference" }],
        ...nomesV2.map((name) => [`../v2/${name}/${name}`, { __esModule: true, default: name }]),
      ]),
      props: {
        clienteId: 5,
        clienteNome: "Cliente",
        onClose: () => {
          fechamentos += 1;
        },
      },
      globals: {
        console: { log() {}, error() {} },
        globalThis: { crypto: { randomUUID: () => `chave-${++chaves}` } },
      },
    },
  );
  await harness.settle();
  await harness.act(() =>
    elements(harness.tree)
      .find(
        (node) => node.type === "InputCheckbox" && node.props.rotulo === "Selecionar venda VEN-11",
      )
      .props.onChange({}),
  );
  const definirValor = (value) =>
    harness.act(() =>
      elements(harness.tree)
        .find((node) => node.type === "InputMoeda")
        .props.onChange(value),
    );
  const enviar = () =>
    harness.act(() =>
      elements(harness.tree)
        .find(
          (node) =>
            node.type === "BotaoInteracao" && elementText(node) === "Baixar Vendas Selecionadas",
        )
        .props.onClick(),
    );
  await definirValor(60);
  await enviar();
  await enviar();
  assert.equal(envios[0].request_id, envios[1].request_id);
  assert.equal(fechamentos, 0);
  await definirValor(70);
  await enviar();
  assert.notEqual(envios[2].request_id, envios[0].request_id);
  assert.equal(envios[2].valor_total, 70);
  assert.equal(fechamentos, 1);
});
