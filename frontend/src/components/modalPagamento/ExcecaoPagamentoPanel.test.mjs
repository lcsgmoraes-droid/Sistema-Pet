import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import {
  createControllerHarness,
  elements,
  elementText,
} from "../../../scripts/helpers/reactControllerHarness.mjs";
import {
  comporExcedentePagamento,
  excecaoPagamentoAutorizada,
  extrairExcecaoPagamento,
  usarContextoExcedenteServidor,
  validarTiposPagamentoExcedente,
} from "./modalPagamentoExcedente.js";

const pagamento = {
  forma_pagamento_id: 2,
  forma_pagamento_tipo: "cartao_credito",
  valor: 119.9,
  valor_recebido: 119.9,
  numero_parcelas: 3,
};
const modelo = () => comporExcedentePagamento({ valorTotal: 109.9, pagamentos: [pagamento] });

test("beneficio ou dinheiro valido mais excesso monetario independe da ordem do lote", () => {
  const pix = { forma_pagamento_tipo: "pix", valor: 100 };
  for (const fixo of [
    { forma_pagamento_tipo: "credito_cliente", valor: 10 },
    { forma_pagamento_tipo: "cashback", valor: 10 },
    { forma_pagamento_tipo: "dinheiro", valor: 10 },
  ]) {
    for (const pagamentos of [
      [pix, fixo],
      [fixo, pix],
    ]) {
      assert.equal(validarTiposPagamentoExcedente({ valorTotal: 100, pagamentos }), "");
    }
  }
  for (const tipo of ["crediario", "boleto"]) {
    const plano = { forma_pagamento_tipo: tipo, valor: 10 };
    for (const pagamentos of [
      [pix, plano],
      [plano, pix],
    ])
      assert.match(validarTiposPagamentoExcedente({ valorTotal: 100, pagamentos }), /parcelas/);
  }
});
test("autorizacao e vinculada aos valores/parcelas; contexto da API nunca e inventado", () => {
  const composicao = modelo();
  assert.equal(composicao.contexto, null);
  const autorizacao = { chave: composicao.chave, justificativa: "Conferido com o cliente." };
  assert.equal(excecaoPagamentoAutorizada(composicao, autorizacao), true);
  for (const atualizado of [
    comporExcedentePagamento({ valorTotal: 108.9, pagamentos: [pagamento] }),
    comporExcedentePagamento({
      valorTotal: 109.9,
      pagamentos: [{ ...pagamento, numero_parcelas: 1 }],
    }),
    comporExcedentePagamento({ valorTotal: 109.9, pagamentos: [{ ...pagamento, valor: 120 }] }),
  ])
    assert.equal(excecaoPagamentoAutorizada(atualizado, autorizacao), false);
});

test("409 fornece fotografia inteira com crediario separado e invalida confirmacao anterior", () => {
  const contexto = {
    total_venda: 109.9,
    total_ja_pago: 10,
    total_novos_pagamentos: 119.9,
    crediario_pendente: 0,
  };
  const detalhe = {
    code: "PAGAMENTO_EXCEDENTE_DESATUALIZADO",
    mensagem: "Os valores mudaram",
    contexto,
    excedente: 20,
  };
  assert.equal(
    extrairExcecaoPagamento({ response: { status: 409, data: { detail: detalhe } } }),
    detalhe,
  );
  assert.equal(extrairExcecaoPagamento({ response: { data: { detail: "Outra rejeição" } } }), null);
  const composicao = modelo();
  const canonica = usarContextoExcedenteServidor(composicao, { base: composicao.chave, detalhe });
  assert.equal(canonica.contexto, contexto, "Copia todos os campos do servidor sem reconstruir");
  assert.equal(canonica.excedente, 20);
  assert.equal(
    excecaoPagamentoAutorizada(canonica, {
      chave: composicao.chave,
      justificativa: "Motivo anterior",
    }),
    false,
  );
});

test("painel V2 exige motivo, confirmacao explicita e mantem texto ao receber fotografia atualizada", async () => {
  const confirmacoes = [];
  const mocks = new Map([
    ["../v2/BotaoInteracao/BotaoInteracao", { __esModule: true, default: "BotaoInteracao" }],
    ["../v2/InputTextoLongo/InputTextoLongo", { __esModule: true, default: "InputTextoLongo" }],
  ]);
  const h = createControllerHarness(
    fileURLToPath(new URL("./ExcecaoPagamentoPanel.jsx", import.meta.url)),
    {
      mocks,
      props: { composicao: modelo(), onConfirmar: (valor) => confirmacoes.push(valor) },
    },
  );
  const campo = () => elements(h.tree).find((el) => el.type === "InputTextoLongo");
  const botao = () => elements(h.tree).find((el) => el.type === "BotaoInteracao");
  assert.match(elementText(h.tree), /R\$ 109,90/);
  assert.match(elementText(h.tree), /R\$ 119,90/);
  assert.equal(campo().props.required, true);
  await h.act(() => botao().props.onClick());
  assert.equal(confirmacoes.length, 0);
  assert.match(campo().props.error, /10 a 1000/);
  await h.act(() => campo().props.onChange("  Cliente manteve o valor após o desconto.  "));
  await h.act(() => botao().props.onClick());
  assert.equal(confirmacoes[0].justificativa, "Cliente manteve o valor após o desconto.");
  assert.equal(confirmacoes[0].contexto, null);
  const novo = comporExcedentePagamento({ valorTotal: 108.9, pagamentos: [pagamento] });
  await h.update({ composicao: novo, autorizacao: confirmacoes[0] });
  assert.equal(campo().props.value, "  Cliente manteve o valor após o desconto.  ");
  assert.equal(confirmacoes.length, 1, "Recalculo nao confirma sozinho");
  await h.act(() => botao().props.onClick());
  await h.update({ autorizacao: confirmacoes[1] });
  assert.equal(campo(), undefined);
  assert.match(elementText(h.tree), /Exceção confirmada/);
});
