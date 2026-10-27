import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
  elementText,
} from "../../../../scripts/helpers/reactControllerHarness.mjs";

function preparar(listarPendenciasFechamento) {
  const padrao = (nome) => ({ __esModule: true, default: nome });
  return createControllerHarness(
    fileURLToPath(new URL("./BanhoTosaFechamentosView.jsx", import.meta.url)),
    {
      props: {},
      mocks: new Map([
        [
          "lucide-react",
          {
            CheckCircle2: "CheckCircle2",
            ExternalLink: "ExternalLink",
            Receipt: "Receipt",
            RefreshCw: "RefreshCw",
            RotateCw: "RotateCw",
          },
        ],
        ["react-hot-toast", { __esModule: true, default: { success() {}, error() {} } }],
        ["../../../components/v2/BotaoInteracao/BotaoInteracao", padrao("BotaoInteracao")],
        ...["EmptyState", "MetricCard", "MetricGrid", "Panel"].map((nome) => [
          `../../../components/ui/${nome}`,
          padrao(nome),
        ]),
        ["../../../utils/formatters", { formatMoneyBRL: (valor) => String(valor) }],
        ["../banhoTosaApi", { banhoTosaApi: { listarPendenciasFechamento } }],
        ["../banhoTosaUtils", { getApiErrorMessage: (_erro, mensagem) => mensagem }],
        ["../../../services/corepetDialog", { confirmarCorePet: async () => true }],
      ]),
    },
  );
}

const pagina = (itens, proximoCursor = null) => ({
  data: { itens, proximo_cursor: proximoCursor, busca_incompleta: proximoCursor != null },
});
const conteudo = (app) =>
  elements(app.tree).find((item) => item.type?.name === "ConteudoFechamentos");
const continuar = (app) =>
  elements(app.tree).find(
    (item) =>
      item.type === "BotaoInteracao" && elementText(item) === "Buscar pendências anteriores",
  );

test("continuacao acumula sem duplicar e ignora clique duplo durante a consulta", async () => {
  const chamadas = [];
  let concluir;
  const resposta = new Promise((resolve) => {
    concluir = resolve;
  });
  const app = preparar(async (params) => {
    chamadas.push(params);
    if (params.cursor == null) return pagina([{ atendimento_id: 9 }], 9);
    return resposta;
  });
  await app.settle();
  const botao = continuar(app);
  await app.act(() => {
    botao.props.onClick();
    botao.props.onClick();
  });
  assert.equal(chamadas.length, 2);
  assert.equal(chamadas[1].cursor, 9);
  concluir(pagina([{ atendimento_id: 9 }, { atendimento_id: 5 }]));
  await app.settle();
  assert.deepEqual(
    conteudo(app).props.pendencias.map((item) => item.atendimento_id),
    [9, 5],
  );
  assert.equal(continuar(app), undefined);
});

test("busca incompleta sem linhas informa continuidade em vez de declarar ausencia de pendencias", async () => {
  const app = preparar(async (params) => pagina([], params.cursor == null ? 20 : null));
  await app.settle();
  assert.match(elementText(app.tree), /Ainda há histórico anterior para conferir/);
  let resultado = conteudo(app);
  assert.equal(resultado.type(resultado.props), null);
  await app.act(() => continuar(app).props.onClick());
  resultado = conteudo(app);
  assert.equal(resultado.type(resultado.props).type, "EmptyState");
});

test("resposta atrasada nao atualiza a central depois de desmontar", async () => {
  let concluir;
  const app = preparar(
    () =>
      new Promise((resolve) => {
        concluir = resolve;
      }),
  );
  app.unmount();
  concluir(pagina([{ atendimento_id: 7 }], 7));
  await app.settle();
  assert.deepEqual(conteudo(app).props.pendencias, []);
  assert.equal(continuar(app), undefined);
});
