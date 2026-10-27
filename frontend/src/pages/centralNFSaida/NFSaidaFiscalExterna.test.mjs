import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
} from "../../../scripts/helpers/reactControllerHarness.mjs";

test("Central oferece apenas ações fiscais externas sem rotas de Venda ou clonagem", async () => {
  const note = {
    fiscal_order_id: 9,
    id: "fiscal-externa-9",
    numero: 9001,
    modelo: 55,
    provedor: "intnfe",
    status: "Autorizada",
    cliente: {},
  };
  const downloaded = [];
  const opened = [];
  const harness = createControllerHarness(
    fileURLToPath(new URL("./NFSaidaList.jsx", import.meta.url)),
    {
      props: {
        notasFiltradas: [note],
        totalNotas: 0,
        baixarXml: (value) => downloaded.push(value),
        abrirDetalhes: (value) => opened.push(value),
        reconciliarFluxoNota: () => {},
      },
      mocks: new Map([
        ["lucide-react", new Proxy({}, { get: (_target, key) => String(key) })],
        ["../../components/v2/BotaoInteracao/BotaoInteracao", "BotaoInteracao"],
        ["../../components/v2/BotaoMenuAcoes/BotaoMenuAcoes", "BotaoMenuAcoes"],
        ["../../components/ui/CustomerIdentity", "CustomerIdentity"],
        ["../../utils/formatters", { formatMoneyBRL: String }],
        ["../../utils/fiscalRejectionGuidance.mjs", { rejeicaoResponsavelTecnico: () => false }],
        ["../../utils/pdvFiscalStatus", { obterPendenciaCancelamentoFiscal: () => null }],
        [
          "./centralNFSaidaUtils",
          { formatarDataBR: () => "", getSituacaoCor: () => "", getSituacaoIcone: () => null },
        ],
      ]),
    },
  );
  const menu = elements(harness.tree).find((item) => item.type === "BotaoMenuAcoes");
  assert.deepEqual(
    menu.props.acoes.map((action) => action.label),
    ["Ver detalhes", "Atualizar situação da NF", "Baixar DANFE", "Baixar XML"],
  );
  await harness.act(() =>
    menu.props.acoes.find((action) => action.label === "Baixar XML").onClick(),
  );
  assert.equal(downloaded[0], note);
  await harness.act(() => menu.props.acoes[0].onClick());
  assert.equal(opened[0], note);
});

test("documentos externos usam ID fiscal estável e endpoint management", () => {
  const note = { provedor: "intnfe", fiscal_order_id: 9 };
  const harness = createControllerHarness(
    fileURLToPath(new URL("./centralNFSaidaUtils.jsx", import.meta.url)),
    {
      exportName: "rotaDocumentoFiscal",
      props: { note },
      invoke: (fn, props) => fn(props.note, "xml"),
      mocks: new Map([
        [
          "lucide-react",
          { AlertCircle: "AlertCircle", CheckCircle: "CheckCircle", FileText: "FileText", X: "X" },
        ],
      ]),
    },
  );
  assert.equal(harness.tree, "/integracoes/ecommerceai/fiscal/manage/orders/9/xml");
  assert.doesNotMatch(harness.tree, /vendas|undefined/);
});
