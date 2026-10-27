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

for (const modal of ["NFSaidaDetalhesModal", "NFSaidaCancelamentoModal"]) {
  for (const codigo of ["1848", undefined]) {
    test(`${modal} usa código público e nunca promove ID técnico quando código é ${codigo || "ausente"}`, () => {
      const nota = {
        id: 99,
        numero: 1,
        modelo: 55,
        tipo: "nfe",
        status: "autorizada",
        valor: 10,
        cliente_id: 47644,
        cliente: { id: 47644, nome: "Pessoa fictícia", ...(codigo ? { codigo } : {}) },
      };
      const harness = createControllerHarness(
        fileURLToPath(new URL(`./${modal}.jsx`, import.meta.url)),
        {
          props: {
            notaSelecionada: nota,
            modalCancelar: nota,
            justificativa: "",
            detalheNota: null,
          },
          mocks: new Map([
            ["lucide-react", new Proxy({}, { get: (_target, key) => String(key) })],
            ["../../components/ui/CustomerIdentity", "CustomerIdentity"],
            ["../../components/v2/BotaoCancelar/BotaoCancelar", "BotaoCancelar"],
            ["../../components/v2/BotaoInteracao/BotaoInteracao", "BotaoInteracao"],
            ["../../components/v2/InputTextoLongo/InputTextoLongo", "InputTextoLongo"],
            ["../../utils/formatters", { formatMoneyBRL: String }],
            [
              "../../utils/fiscalRejectionGuidance.mjs",
              { rejeicaoResponsavelTecnico: () => false },
            ],
            ["../../utils/pdvFiscalStatus", { obterPendenciaCancelamentoFiscal: () => null }],
            [
              "./centralNFSaidaUtils",
              {
                formatarDataBR: () => "",
                formatarValorDetalhe: String,
                getSituacaoCor: () => "",
                getSituacaoIcone: () => null,
                valorBooleanoLabel: String,
              },
            ],
          ]),
        },
      );
      const identidade = elements(harness.tree).find((node) => node.type === "CustomerIdentity");
      assert.ok(identidade);
      const renderIdentidade = createControllerHarness(
        fileURLToPath(new URL("../../components/ui/CustomerIdentity.jsx", import.meta.url)),
        {
          props: identidade.props,
          mocks: new Map([
            ["./CopyableCode", "CopyableCode"],
            ["./CopyableValue", "CopyableValue"],
          ]),
        },
      );
      const exibido = elements(renderIdentidade.tree).find((node) => node.type === "CopyableCode");
      assert.equal(exibido?.props.value, codigo);
      assert.notEqual(exibido?.props.value, "47644");
      renderIdentidade.unmount();
      harness.unmount();
    });
  }
}
