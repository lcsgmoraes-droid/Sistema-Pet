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
function preparar({ props = {}, persistir, finalizar, buscar, recebido = 0 } = {}) {
  const alteracoes = {},
    chamadas = { persistir: [], finalizar: [], leituras: [] };
  const emissoes = [];
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
    // Adicionar um pagamento limpa a selecao e o valor no modal real.
    formaPagamentoSelecionada: props.pagamentos?.length ? null : cartao,
    valorRecebido: props.pagamentos?.length ? 0 : 119.9,
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
            buscarVenda: async (id) => {
              chamadas.leituras.push(`/vendas/${id}`);
              return buscar ? buscar(id) : { ...defaults.venda, id };
            },
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
        [
          "../../utils/nfeFiscalAssistida",
          {
            emitirNotaFiscalAssistida: async (payload) => {
              emissoes.push(payload);
              return { data: {} };
            },
          },
        ],
        ["../../utils/fiscalRejectionGuidance.mjs", {}],
        [
          "../../services/corepetDialog",
          { confirmarCorePet: async () => true, perguntarCorePet: async () => null },
        ],
      ]),
    },
  );
  return { h, alteracoes, chamadas, emissoes };
}

test("iFood nao inicia emissao fiscal automatica e preserva a emissao manual", async () => {
  const pagamento = montar(dinheiro, 119.9, 119.9);
  const c = preparar({
    props: {
      venda: {
        ...baseVenda,
        canal: "ifood",
        ifood_pdv_pilot: { enabled: true, payment_mode: "offline" },
      },
      pagamentos: [pagamento],
      moduloFiscalAtivo: true,
      emissaoAutomatica: { ativa: true, tipo: "nfce" },
    },
    finalizar: async (id, pagamentos) => ({ id, status: "finalizada", pagamentos }),
  });
  await c.h.act(() => c.h.tree.handleFinalizar());
  assert.equal(c.alteracoes.AutoEmitirTipo, null);
  assert.equal(c.alteracoes.MostrarPerguntaNFe, true);
  assert.deepEqual(c.emissoes, []);
  await c.h.update({ vendaFinalizadaId: 12 });
  await c.h.act(() => c.h.tree.emitirNFe("nfce"));
  assert.deepEqual(c.emissoes, [{ vendaId: 12, tipoNota: "nfce", semInteracao: false }]);
});

test("emissao automatica configurada continua disponivel para app e ecommerce", async () => {
  for (const canal of ["app", "ecommerce"]) {
    const c = preparar({
      props: {
        venda: { ...baseVenda, canal },
        pagamentos: [montar(dinheiro, 119.9, 119.9)],
        moduloFiscalAtivo: true,
        emissaoAutomatica: { ativa: true, tipo: "nfce" },
      },
      finalizar: async (id, pagamentos) => ({ id, status: "finalizada", pagamentos }),
    });
    await c.h.act(() => c.h.tree.handleFinalizar());
    assert.equal(c.alteracoes.AutoEmitirTipo, "nfce");
    assert.equal(c.alteracoes.MostrarPerguntaNFe, true);
  }
});

test("DELIVERY iFood finaliza a venda existente sem PUT, entregador local ou duplicacao", async () => {
  const pagamento = montar(dinheiro, 119.9, 119.9);
  const venda = {
    ...baseVenda,
    canal: "ifood",
    ifood_pdv_pilot: { enabled: true, payment_mode: "offline" },
    tem_entrega: true,
    entregador_id: null,
    entrega: { taxa_entrega_total: 0 },
  };
  const c = preparar({
    props: { venda, pagamentos: [pagamento] },
    finalizar: async (id, pagamentos) => ({
      id,
      status: "finalizada",
      tem_entrega: true,
      pagamentos,
    }),
  });
  const first = c.h.tree.handleFinalizar();
  const second = c.h.tree.handleFinalizar();
  await c.h.act(() => Promise.all([first, second]));
  assert.deepEqual(c.chamadas.persistir, []);
  assert.equal(c.chamadas.finalizar.length, 1);
  assert.equal(c.chamadas.finalizar[0].id, 12);
  assert.equal(venda.tem_entrega, true);
  assert.equal(venda.entregador_id, null);
  assert.equal(c.alteracoes.Erro, "");
});

test("DELIVERY iFood com frete positivo recebe o total exato sem sobrescrever a venda", async () => {
  const venda = {
    ...baseVenda,
    canal: "ifood",
    ifood_pdv_pilot: { enabled: true, payment_mode: "offline" },
    tem_entrega: true,
    entregador_id: null,
    subtotal: 65,
    total: 73.9,
    entrega: { taxa_entrega_total: 8.9, taxa_loja: 0, taxa_entregador: 0 },
    itens: [{ produto_id: 1, quantidade: 1, preco_unitario: 65, subtotal: 65 }],
  };
  const antes = structuredClone(venda);
  const c = preparar({
    props: {
      venda,
      pagamentos: [montar(dinheiro, 73.9, 73.9)],
      valorRestante: 0,
    },
    finalizar: async (id, pagamentos) => ({
      id,
      status: "finalizada",
      total: 73.9,
      tem_entrega: true,
      pagamentos,
    }),
  });
  await c.h.act(() => Promise.all([c.h.tree.handleFinalizar(), c.h.tree.handleFinalizar()]));
  assert.deepEqual(c.chamadas.persistir, []);
  assert.equal(c.chamadas.finalizar.length, 1);
  assert.equal(c.chamadas.finalizar[0].id, 12);
  assert.equal(c.chamadas.finalizar[0].pagamentos.length, 1);
  assert.equal(c.chamadas.finalizar[0].pagamentos[0].valor, 73.9);
  assert.equal(c.chamadas.finalizar[0].pagamentos[0].valor_recebido, 73.9);
  assert.deepEqual(venda, antes);
  assert.equal(c.alteracoes.Erro, "");
});

test("pagamento online ou desconhecido iFood nunca adiciona, exclui ou finaliza pela cobranca manual", async () => {
  for (const summary of [
    { enabled: true, payment_mode: "online" },
    { enabled: false, payment_mode: "unknown" },
    undefined,
  ]) {
    const c = preparar({
      props: {
        venda: { ...baseVenda, canal: "ifood", ifood_pdv_pilot: summary },
        pagamentos: [montar(dinheiro, 119.9, 119.9)],
        formaPagamentoSelecionada: dinheiro,
      },
    });
    await c.h.act(() => c.h.tree.adicionarPagamento());
    await c.h.act(() => c.h.tree.removerPagamento(0));
    await c.h.act(() => c.h.tree.excluirPagamentoExistente(1));
    await c.h.act(() => c.h.tree.handleFinalizar());
    assert.deepEqual(c.chamadas, { persistir: [], finalizar: [], leituras: [] });
    assert.equal(c.alteracoes.Pagamentos, undefined);
    assert.match(c.alteracoes.Erro, /Cobrança manual iFood bloqueada/);
  }
});

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
      formaPagamentoSelecionada: cartao,
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

test("cashback selecionado nao e ignorado ao registrar pagamento misto de R$ 93,90", async () => {
  const pix = montar({ id: 4, nome: "Pix", tipo: "pix" }, 87, 93.9);
  const c = preparar({
    props: {
      venda: { ...baseVenda, total: 93.9 },
      pagamentos: [pix],
      formaPagamentoSelecionada: { id: "cashback", nome: "Cashback", tipo: "cashback" },
      valorRecebido: 6.9,
      valorRestante: 6.9,
      saldoCashback: 6.9,
    },
  });
  await c.h.act(() => c.h.tree.handleFinalizar());
  assert.match(c.alteracoes.Erro, /pagamento selecionado ainda não foi adicionado/);
  assert.match(c.alteracoes.Erro, /Adicionar Pagamento/);
  assert.deepEqual(c.chamadas, { persistir: [], finalizar: [], leituras: [] });
  assert.equal(c.alteracoes.Pagamentos, undefined);

  await c.h.act(() => c.h.tree.adicionarPagamento());
  assert.equal(c.alteracoes.Pagamentos.length, 2);
  assert.equal(c.alteracoes.Pagamentos[1].valor, 6.9);
  assert.equal(c.alteracoes.Pagamentos[1].is_cashback, true);
  await c.h.update({
    pagamentos: c.alteracoes.Pagamentos,
    formaPagamentoSelecionada: c.alteracoes.FormaPagamentoSelecionada,
    valorRecebido: c.alteracoes.ValorRecebido,
    valorRestante: 0,
  });
  await c.h.act(() => c.h.tree.handleFinalizar());
  assert.equal(c.chamadas.finalizar.length, 1);
  assert.deepEqual(
    c.chamadas.finalizar[0].pagamentos.map((p) => p.valor),
    [87, 6.9],
  );
  assert.equal(c.alteracoes.Erro, "");
});

test("pagamento integral com cashback adicionado e enviado sem criar outro recebimento", async () => {
  const cashback = montar({ id: "cashback", nome: "Cashback", tipo: "cashback" }, 93.9, 93.9);
  const c = preparar({
    props: { venda: { ...baseVenda, total: 93.9 }, pagamentos: [cashback], valorRestante: 0 },
  });
  await c.h.act(() => c.h.tree.handleFinalizar());
  assert.equal(c.chamadas.finalizar.length, 1);
  assert.deepEqual(c.chamadas.finalizar[0].pagamentos, [cashback]);
  assert.equal(c.alteracoes.Erro, "");
});

test("selecao pendente exige adicionar antes de registrar mesmo sem outro pagamento", async () => {
  for (const forma of [
    { id: "cashback", nome: "Cashback", tipo: "cashback" },
    { id: "credito_cliente", nome: "Crédito Cliente", tipo: "credito_cliente" },
    { id: 4, nome: "Pix", tipo: "pix" },
  ]) {
    const c = preparar({
      props: {
        formaPagamentoSelecionada: forma,
        valorRecebido: 10,
        podeConfirmarFinalizacao: false,
      },
    });
    await c.h.act(() => c.h.tree.handleFinalizar());
    assert.match(c.alteracoes.Erro, /Adicionar Pagamento/);
    assert.deepEqual(c.chamadas, { persistir: [], finalizar: [], leituras: [] });
  }
});

test("complementa80mais120 numa venda parcial200 sem tentar editar a venda", async () => {
  const venda = {
    ...baseVenda,
    status: "baixa_parcial",
    total: 200,
    itens: [
      {
        tipo: "servico",
        servico_descricao: "Pacote4banhos",
        quantidade: 1,
        preco_unitario: 200,
        subtotal: 200,
      },
    ],
  };
  const c = preparar({
    props: { venda, totalPagoExistente: 80, pagamentos: [montar(dinheiro, 120, 120)] },
    recebido: 80,
    persistir: async () => {
      throw {
        response: {
          data: {
            detail:
              'Não é possível atualizar venda com status "baixa_parcial". Apenas vendas abertas podem ser atualizadas.',
          },
        },
      };
    },
    finalizar: async (id, pagamentos) => ({ id, status: "finalizada", total: 200, pagamentos }),
  });
  await c.h.act(() => c.h.tree.handleFinalizar());
  assert.equal(c.chamadas.persistir.length, 0);
  assert.equal(c.chamadas.finalizar.length, 1);
  assert.deepEqual(c.chamadas.leituras, ["/vendas/12", "/vendas/12/pagamentos"]);
  assert.equal(c.chamadas.finalizar[0].pagamentos.length, 1);
  assert.equal(c.chamadas.finalizar[0].pagamentos[0].valor, 120);
  assert.equal(c.alteracoes.VendaFinalizadaParaCupom.status, "finalizada");
});

test("recebimento parcial relê total do servidor antes de aceitar complemento", async () => {
  const c = preparar({
    props: {
      venda: { ...baseVenda, status: "baixa_parcial", total: 200 },
      totalPagoExistente: 80,
      pagamentos: [montar(dinheiro, 120, 120)],
    },
    recebido: 80,
    buscar: async () => ({ ...baseVenda, status: "baixa_parcial", total: 210 }),
  });
  await c.h.act(() => c.h.tree.handleFinalizar());
  assert.equal(c.chamadas.persistir.length, 0);
  assert.equal(c.chamadas.finalizar.length, 0);
  assert.equal(c.alteracoes.VendaPersistida.total, 210);
  assert.match(c.alteracoes.Erro, /Nenhum novo pagamento foi registrado/);
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
