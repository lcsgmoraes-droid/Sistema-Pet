import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createControllerHarness } from "../../../scripts/helpers/reactControllerHarness.mjs";
import { montarPagamentoRecebido } from "../modalPagamentoUtils.js";
import {
  comporExcedentePagamento,
  usarContextoExcedenteServidor,
} from "./modalPagamentoExcedente.js";

const cartao = {
  id: 2,
  nome: "Cartão de crédito",
  tipo: "cartao_credito",
  permite_parcelamento: true,
};
const dinheiro = { id: 1, nome: "Dinheiro", tipo: "dinheiro" };
const operadora = { id: 7, nome: "Operadora DEV", max_parcelas: 12 };
const baseVenda = {
  id: 12,
  total: 119.9,
  desconto_valor: 0,
  desconto_venda_valor: 0,
  itens: [{ produto_id: 1, quantidade: 1, preco_unitario: 119.9, subtotal: 119.9 }],
  cliente: { id: 3 },
};
const montar = (forma, valor, restante, parcelas = 1) =>
  montarPagamentoRecebido({
    formaPagamento: forma,
    valor,
    valorRestante: restante,
    operadora,
    bandeira: "Visa",
    numeroParcelas: parcelas,
  });
const fotografia = {
  total_venda: 109.9,
  total_ja_pago: 0,
  total_novos_pagamentos: 119.9,
  crediario_pendente: 0,
};
function preparar({ props = {}, persistir, finalizar, recebido = 0 } = {}) {
  const alteracoes = {},
    chamadas = { persistir: [], finalizar: [], leituras: [] };
  const setters = Object.fromEntries(
    [
      "Bandeira",
      "Erro",
      "ErroJustificativa",
      "FormaPagamentoSelecionada",
      "Loading",
      "MostrarPerguntaNFe",
      "AutoEmitirTipo",
      "NsuCartao",
      "NumeroParcelas",
      "OperadoraSelecionada",
      "Pagamentos",
      "PagamentosExistentes",
      "TotalPagoExistente",
      "ValorRecebido",
      "VendaFinalizadaId",
      "VendaFinalizadaParaCupom",
      "VendaPersistida",
      "AutorizacaoExcedente",
      "ContextoExcedenteServidor",
      "ErroPagamentosExistentes",
    ].map((nome) => [
      `set${nome}`,
      (valor) => {
        alteracoes[nome] = valor;
      },
    ]),
  );
  const defaults = {
    ...setters,
    venda: baseVenda,
    pagamentos: [],
    totalPagoExistente: 0,
    formaPagamentoSelecionada: cartao,
    valorRecebido: 119.9,
    valorRestante: 119.9,
    bandeira: "Visa",
    nsuCartao: "",
    numeroParcelas: 1,
    operadoraSelecionada: operadora,
    operadoras: [operadora],
    parcelasDisponiveis: [1, 2, 3],
    podeConfirmarFinalizacao: true,
    naoGerarBeneficios: false,
    justificativaBeneficios: "",
    moduloFiscalAtivo: false,
    onConfirmar() {},
    revelarJustificativaObrigatoria() {},
    ...props,
  };
  const api = {
    get(url) {
      chamadas.leituras.push(url);
      return Promise.resolve({ data: { pagamentos: [], total_recebido: recebido } });
    },
  };
  const h = createControllerHarness(
    fileURLToPath(new URL("./useModalPagamentoActions.js", import.meta.url)),
    {
      props: defaults,
      exportName: "useModalPagamentoActions",
      globals: { console: { log() {}, error() {} } },
      mocks: new Map([
        ["react-router-dom", { useNavigate: () => () => {} }],
        ["../../api", { __esModule: true, default: api }],
        ["../../api/alertasEstoque", { verificarEstoqueNegativo: async () => ({ data: [] }) }],
        [
          "../../api/vendas",
          {
            atualizarVenda: async (id, payload) => {
              chamadas.persistir.push({ id, payload });
              return persistir ? persistir(id, payload) : { id, total: defaults.venda.total };
            },
            criarVenda: async () => ({ id: 12, total: defaults.venda.total }),
            finalizarVenda: async (id, pagamentos, options) => {
              chamadas.finalizar.push({ id, pagamentos, options });
              return finalizar
                ? finalizar(id, pagamentos, options)
                : { status: "baixa_parcial", pagamentos };
            },
          },
        ],
        ["../../utils/nfeFiscalAssistida", {}],
        ["../../utils/fiscalRejectionGuidance.mjs", {}],
        [
          "../../services/corepetDialog",
          { confirmarCorePet: async () => true, perguntarCorePet: async () => null },
        ],
      ]),
    },
  );
  return { h, alteracoes, chamadas };
}

test("cartao119,90 com saldo109,90 e bloqueado sem justificativa; excecao preserva integral sem troco", async () => {
  const venda = { ...baseVenda, total: 109.9, desconto_valor: 10, desconto_venda_valor: 10 };
  const c = preparar({ props: { venda, valorRestante: 109.9 } });
  await c.h.act(() => c.h.tree.adicionarPagamento());
  assert.match(c.alteracoes.Erro, /excede o restante/);
  assert.match(c.alteracoes.Erro, /confirme a exceção com justificativa no painel/);
  assert.equal(c.alteracoes.Pagamentos, undefined);
  const candidato = montar(cartao, 119.9, 109.9);
  const modelo = comporExcedentePagamento({ valorTotal: 109.9, pagamentos: [candidato] });
  await c.h.update({
    autorizacaoExcedente: {
      chave: modelo.chave,
      justificativa: "Cliente autorizou o excedente no cartão.",
    },
  });
  await c.h.act(() => c.h.tree.adicionarPagamento());
  assert.equal(c.alteracoes.Pagamentos[0].valor, 119.9);
  assert.equal(c.alteracoes.Pagamentos[0].valor_recebido, 119.9);
  assert.equal(c.alteracoes.Pagamentos[0].troco, null);
  assert.equal(c.chamadas.finalizar.length, 0);
});

test("dinheiro120 para109,90 separa entregue, aplicado109,90 e troco10,10 sem excecao", async () => {
  const c = preparar({
    props: { formaPagamentoSelecionada: dinheiro, valorRecebido: 120, valorRestante: 109.9 },
  });
  await c.h.act(() => c.h.tree.adicionarPagamento());
  assert.equal(c.alteracoes.Pagamentos[0].valor, 109.9);
  assert.equal(c.alteracoes.Pagamentos[0].valor_recebido, 120);
  assert.equal(c.alteracoes.Pagamentos[0].troco, 10.1);
});

test("pagamento misto e parcial usa saldo e parcelas do cartao sem criar plano crediario", async () => {
  const entrada = montar(dinheiro, 40, 109.9);
  const c = preparar({
    props: {
      venda: { ...baseVenda, total: 109.9 },
      pagamentos: [entrada],
      numeroParcelas: 3,
      valorRecebido: 69.9,
      valorRestante: 69.9,
    },
  });
  await c.h.act(() => c.h.tree.adicionarPagamento());
  assert.equal(c.alteracoes.Pagamentos.length, 2);
  assert.equal(c.alteracoes.Pagamentos[1].valor, 69.9);
  assert.equal(c.alteracoes.Pagamentos[1].numero_parcelas, 3);
  assert.equal(c.alteracoes.Pagamentos[1].forma_pagamento_tipo, "cartao_credito");
  assert.equal(c.alteracoes.Pagamentos[1].intervalo_crediario, undefined);
});

test("desconto persistido119,90 para109,90 impede finalizar sem rever e copiar contexto canonico", async () => {
  let tentativas = 0;
  const pagamento = montar(cartao, 119.9, 119.9);
  const c = preparar({
    props: { pagamentos: [pagamento] },
    persistir: async () => ({ ...baseVenda, total: 109.9, desconto_valor: 10 }),
    finalizar: async (_id, pagamentos, options) => {
      tentativas += 1;
      if (!options.contexto_pagamento_excedente)
        throw {
          response: {
            status: 409,
            data: {
              detail: {
                code: "PAGAMENTO_EXCEDENTE_REQUER_JUSTIFICATIVA",
                mensagem: "Confirme o excedente canônico.",
                excedente: 10,
                contexto_pagamento_excedente: fotografia,
              },
            },
          },
        };
      return { status: "baixa_parcial", pagamentos };
    },
  });
  await c.h.act(() => c.h.tree.handleFinalizar());
  assert.equal(c.chamadas.finalizar.length, 0);
  assert.equal(c.alteracoes.VendaPersistida.total, 109.9);
  assert.equal(c.alteracoes.Pagamentos[0].valor, 119.9);
  assert.match(c.alteracoes.Erro, /Nenhum novo pagamento foi registrado/);
  const venda = { ...baseVenda, total: 109.9, desconto_valor: 10 };
  const modelo = comporExcedentePagamento({ valorTotal: 109.9, pagamentos: [pagamento] });
  await c.h.update({ venda, composicaoFinalizacao: modelo });
  await c.h.act(() => c.h.tree.handleFinalizar());
  assert.equal(c.chamadas.finalizar.length, 0);
  await c.h.update({
    autorizacaoExcedente: {
      chave: modelo.chave,
      justificativa: "Pagamento excedente confirmado pelo cliente.",
      contexto: null,
    },
  });
  await c.h.act(() => c.h.tree.handleFinalizar());
  assert.equal(tentativas, 1);
  assert.equal(c.alteracoes.AutorizacaoExcedente, null);
  const canonico = usarContextoExcedenteServidor(modelo, c.alteracoes.ContextoExcedenteServidor);
  assert.equal(canonico.contexto, fotografia);
  await c.h.update({
    composicaoFinalizacao: canonico,
    autorizacaoExcedente: {
      chave: canonico.chave,
      justificativa: "Pagamento excedente confirmado pelo cliente.",
      contexto: canonico.contexto,
    },
  });
  await c.h.act(() => c.h.tree.handleFinalizar());
  assert.equal(tentativas, 2);
  assert.equal(c.chamadas.finalizar.at(-1).options.contexto_pagamento_excedente, fotografia);
  assert.equal(c.chamadas.finalizar.at(-1).pagamentos[0].valor, 119.9);
});

test("leitura nova de pagamentos antes da gravacao invalida total existente antigo", async () => {
  const pagamento = montar(cartao, 119.9, 119.9);
  const c = preparar({ props: { pagamentos: [pagamento] }, recebido: 40 });
  await c.h.act(() => c.h.tree.handleFinalizar());
  assert.equal(c.alteracoes.TotalPagoExistente, 40);
  assert.equal(c.chamadas.finalizar.length, 0);
  assert.match(c.alteracoes.Erro, /pagamentos já registrados R\$ 40,00/);
});

test("recebimentos indisponiveis bloqueiam adicionar e finalizar antes de qualquer gravacao", async () => {
  const c = preparar({ props: { bloqueado: true } });
  await c.h.act(() => c.h.tree.adicionarPagamento());
  await c.h.act(() => c.h.tree.handleFinalizar());
  assert.equal(c.chamadas.persistir.length, 0);
  assert.equal(c.chamadas.finalizar.length, 0);
  assert.equal(c.alteracoes.Pagamentos, undefined);
});

test("recebimento parcial e registrado sem exigir quitar todo saldo nem justificar valor normal", async () => {
  const pagamento = montar({ id: 4, nome: "Pix", tipo: "pix" }, 50, 119.9);
  const c = preparar({ props: { pagamentos: [pagamento] } });
  await c.h.act(() => c.h.tree.handleFinalizar());
  assert.equal(c.chamadas.finalizar.length, 1);
  assert.equal(c.chamadas.finalizar[0].pagamentos[0].valor, 50);
  assert.equal(c.chamadas.finalizar[0].options.contexto_pagamento_excedente, undefined);
});

test("409 de pagamento legado exibe orientacao sem autorizar excedente ou repetir a gravacao", async () => {
  const pagamento = montar({ id: 4, nome: "Pix", tipo: "pix" }, 50, 119.9);
  const mensagem = "Confira os vínculos dos recebimentos antigos antes de finalizar a venda.";
  const c = preparar({
    props: { pagamentos: [pagamento] },
    finalizar() {
      throw {
        response: {
          status: 409,
          data: { detail: { code: "PAGAMENTO_LEGADO_SEM_VINCULO", mensagem } },
        },
      };
    },
  });
  await c.h.act(() => c.h.tree.handleFinalizar());
  await c.h.settle();
  assert.equal(c.alteracoes.Erro, mensagem);
  assert.equal(c.chamadas.persistir.length, 1);
  assert.equal(c.chamadas.finalizar.length, 1);
  assert.equal(c.alteracoes.ContextoExcedenteServidor, undefined);
  assert.equal(c.alteracoes.AutorizacaoExcedente, undefined);
  assert.equal(c.alteracoes.Pagamentos, undefined);
  assert.equal(c.alteracoes.Loading, false);
});

test("justificativa de excedente nao autoriza beneficio, dinheiro aplicado ou plano acima do saldo", async () => {
  for (const tipo of ["credito_cliente", "cashback", "crediario", "boleto", "dinheiro"]) {
    const pagamento = { forma_pagamento_tipo: tipo, valor: 119.9, valor_recebido: 119.9 };
    const composicao = comporExcedentePagamento({ valorTotal: 109.9, pagamentos: [pagamento] });
    const c = preparar({
      props: {
        venda: { ...baseVenda, total: 109.9 },
        pagamentos: [pagamento],
        composicaoFinalizacao: composicao,
        autorizacaoExcedente: {
          chave: composicao.chave,
          justificativa: "Não deve liberar tipo restrito.",
        },
      },
    });
    await c.h.act(() => c.h.tree.handleFinalizar());
    assert.equal(c.chamadas.finalizar.length, 0);
    assert.match(
      c.alteracoes.Erro,
      tipo === "dinheiro" ? /troco/ : /não libera benefícios ou planos/,
    );
  }
});

test("saldo ja coberto impede novo pagamento mesmo com justificativa de excedente", async () => {
  const novo = montar(cartao, 10, 0);
  const composicao = comporExcedentePagamento({
    valorTotal: 119.9,
    totalPagoExistente: 119.9,
    pagamentos: [novo],
  });
  const c = preparar({
    props: {
      valorRestante: 0,
      totalPagoExistente: 119.9,
      valorRecebido: 10,
      autorizacaoExcedente: {
        chave: composicao.chave,
        justificativa: "Esta justificativa não libera duplicata.",
      },
    },
  });
  await c.h.act(() => c.h.tree.adicionarPagamento());
  assert.match(c.alteracoes.Erro, /totalmente paga/);
  assert.equal(c.alteracoes.Pagamentos, undefined);
  assert.equal(c.chamadas.persistir.length, 0);
});
