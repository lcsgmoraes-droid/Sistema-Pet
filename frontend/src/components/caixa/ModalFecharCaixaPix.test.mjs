import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
  elementText,
} from "../../../scripts/helpers/reactControllerHarness.mjs";

test("fechamento vincula identificacao apenas ao pagamento auditavel sem substituir OK ou expansoes", async () => {
  const pagamento = {
    id: 42,
    venda_id: 12,
    assinatura: "a".repeat(64),
    estado_conferencia: "ok",
    identificacao_pix: { estado: "nao_identificado", registro_id: 17 },
  };
  const salvar = () => true,
    salvarPix = () => true;
  const conferencia = {
    auditoria: {
      pagamentos: [pagamento],
      vendas: [{ id: 12, assinatura: "b".repeat(64) }],
      movimentacoes: [],
    },
    salvar,
    salvarPix,
    abrirVenda() {},
  };
  const padrao = (nome) => ({ __esModule: true, default: nome });
  const h = createControllerHarness(
    fileURLToPath(new URL("./ModalFecharCaixaPanels.jsx", import.meta.url)),
    {
      exportName: "PaymentBreakdownPanel",
      props: {
        conferencia,
        resumo: {
          caixa: { valor_abertura: 140 },
          totais: {},
          vendas_periodo: {},
          composicao_recebimentos: {},
        },
      },
      mocks: new Map([
        ["lucide-react", {}],
        ["../CurrencyInput", padrao("CurrencyInput")],
        ["./ImpressaoResumoCaixa", padrao("ImpressaoResumoCaixa")],
        ["../v2/BotaoInteracao/BotaoInteracao", padrao("BotaoInteracao")],
        ["../v2/ResumoFaturamento/ResumoFaturamento", padrao("ResumoFaturamento")],
        ["./RecebimentosCaixaPanel", padrao("RecebimentosCaixaPanel")],
        ["./ConferenciaCaixaItem", padrao("ConferenciaCaixaItem")],
        ["./IdentificacaoPixItem", padrao("IdentificacaoPixItem")],
      ]),
    },
  );
  const panel = () => elements(h.tree).find((el) => el.type === "RecebimentosCaixaPanel");
  const referencia = { origem: "pagamento", id: "pagamento-42", venda_id: 12 };
  const acoes = elements(panel().props.renderAcoesLancamento(referencia));
  assert.equal(acoes.find((el) => el.type === "ConferenciaCaixaItem").props.onSalvar, salvar);
  assert.equal(acoes.find((el) => el.type === "IdentificacaoPixItem").props.onSalvar, salvarPix);
  assert.equal(acoes.find((el) => el.type === "IdentificacaoPixItem").props.item, pagamento);
  assert.equal(acoes.find((el) => el.type === "IdentificacaoPixItem").props.bloqueado, false);
  assert.match(elementText(h.tree), /não impede o fechamento/);
  const chave = elements(h.tree).find((el) => el.type === "ResumoFaturamento").key;
  await h.update({ conferencia: { ...conferencia, atualizando: true } });
  const atualizadas = elements(panel().props.renderAcoesLancamento(referencia));
  assert.equal(atualizadas.find((el) => el.type === "IdentificacaoPixItem").props.bloqueado, true);
  assert.equal(elements(h.tree).find((el) => el.type === "ResumoFaturamento").key, chave);
  const venda = elements(h.tree)
    .find((el) => el.type === "ResumoFaturamento")
    .props.renderAcoesVenda({ venda_id: 12 });
  assert.equal(
    elements(venda).find((el) => el.type === "IdentificacaoPixItem"),
    undefined,
  );
});
