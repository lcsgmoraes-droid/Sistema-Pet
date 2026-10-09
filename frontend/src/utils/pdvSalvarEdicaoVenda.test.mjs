import assert from "node:assert/strict";
import { test } from "node:test";
import { montarVendaPersistidaParaEdicao, salvarEdicaoVenda } from "./pdvSalvarEdicaoVenda.js";
import { montarPayloadVenda } from "./pdvVendaPayload.js";
import { recalcularSubtotalItem } from "./pdvCarrinhoItensUtils.js";
import { recalcularVendaComDescontos } from "./pdvDescontosUtils.js";

const venda = { id: 34, total: 165, status: "aberta" };
const payload = {
  itens: [
    { produto_id: 1, desconto_item: 20, subtotal: 80 },
    { produto_id: 2, desconto_item: 0, subtotal: 100 },
  ],
  desconto_venda_valor: 10,
  desconto_valor: 35,
  cupom_code: "CUPOM5",
  cupom_discount_applied: 5,
};

function dependencias({ total = 165, recebido = 180, erroPagamento, erroFechamento } = {}) {
  const chamadas = [];
  return {
    chamadas,
    argumentos: {
      vendaAtual: venda,
      payloadVenda: payload,
      atualizarVenda: async (id, dados) => {
        chamadas.push({ metodo: "PUT", id, dados });
        return {
          id,
          total,
          status: "aberta",
          nao_gerar_beneficios: true,
          justificativa_nao_gerar_beneficios: "Pedido do cliente",
        };
      },
      buscarPagamentos: async (id) => {
        chamadas.push({ metodo: "GET", id });
        if (erroPagamento) throw erroPagamento;
        return { total_recebido: recebido, total_pago: Math.min(recebido, 100) };
      },
      finalizarVenda: async (id, pagamentos, opcoes) => {
        chamadas.push({ metodo: "POST_FINALIZAR", id, pagamentos, opcoes });
        if (erroFechamento) throw erroFechamento;
        return { venda: { id, total, status: "finalizada" } };
      },
    },
  };
}

test("salvar reaberta quitada fecha pelo orquestrador sem repetir recebimento ou alterar Di/G/C", async () => {
  const { chamadas, argumentos } = dependencias();
  const resultado = await salvarEdicaoVenda(argumentos);
  assert.deepEqual(
    chamadas.map((chamada) => chamada.metodo),
    ["PUT", "GET", "POST_FINALIZAR"],
  );
  assert.deepEqual(chamadas[0].dados, payload);
  assert.deepEqual(chamadas[2].pagamentos, []);
  assert.deepEqual(chamadas[2].opcoes, {
    cupom_code: "CUPOM5",
    cupom_discount_applied: 5,
    nao_gerar_beneficios: true,
    justificativa_nao_gerar_beneficios: "Pedido do cliente",
  });
  assert.equal(resultado.finalizada, true);
  assert.equal(resultado.recebido, 180);
  assert.equal(resultado.venda.status, "finalizada");
});

test("saldo pendente fica aberto sem PATCH status ou fechamento automatico", async () => {
  const { chamadas, argumentos } = dependencias({ total: 200 });
  const resultado = await salvarEdicaoVenda(argumentos);
  assert.deepEqual(
    chamadas.map((chamada) => chamada.metodo),
    ["PUT", "GET"],
  );
  assert.equal(resultado.finalizada, false);
  assert.equal(resultado.venda.status, "aberta");
  assert.equal(resultado.venda.total - resultado.recebido, 20);
});

test("decisao de fechar usa total persistido e efetivo recebido, nao plano de pagamento", async () => {
  const { chamadas, argumentos } = dependencias({ total: 225, recebido: 0 });
  const resultado = await salvarEdicaoVenda(argumentos);
  assert.equal(resultado.finalizada, false);
  assert.equal(resultado.venda.total, 225);
  assert.deepEqual(
    chamadas.map((chamada) => chamada.metodo),
    ["PUT", "GET"],
  );
});

test("falha ao buscar pagamentos conserva erro sem finalizar por suposicao", async () => {
  const erroPagamento = new Error("Recebimentos indisponiveis");
  const { chamadas, argumentos } = dependencias({ erroPagamento });
  await assert.rejects(salvarEdicaoVenda(argumentos), erroPagamento);
  assert.deepEqual(
    chamadas.map((chamada) => chamada.metodo),
    ["PUT", "GET"],
  );
});

test("erro do orquestrador permanece visivel e nao retorna sucesso de fechamento", async () => {
  const erroFechamento = new Error("Cupom invalido");
  const { chamadas, argumentos } = dependencias({ erroFechamento });
  await assert.rejects(salvarEdicaoVenda(argumentos), erroFechamento);
  assert.deepEqual(
    chamadas.map((chamada) => chamada.metodo),
    ["PUT", "GET", "POST_FINALIZAR"],
  );
});

test("dois saves atualizam IDs do servidor sem misturar linhas do mesmo SKU nem origens de desconto", async () => {
  let estado = {
    id: 34,
    status: "aberta",
    total_pago: 165,
    desconto_venda_valor: 10,
    cupom_code: "CUPOM5",
    cupom_discount_applied: 5,
    cupons_detalhes: [{ code: "CUPOM5", coupon_type: "fixed", discount_value: 5 }],
    cliente: { id: 35, nome: "Cliente", credito: { limite: 1000 } },
    pagamentos: [{ id: 1, valor: 165 }],
    entrega: { endereco_completo: "Endereco selecionado", taxa_entrega_total: 0 },
    itens: [
      {
        id: 50,
        venda_id: 34,
        produto_id: 85,
        quantidade: 2,
        preco_unitario: 100,
        desconto_valor: 20,
        subtotal: 180,
      },
      {
        id: 55,
        venda_id: 34,
        produto_id: 85,
        quantidade: 1,
        preco_unitario: 100,
        desconto_valor: 0,
        subtotal: 100,
      },
    ],
    subtotal: 280,
    total: 265,
  };
  const idsRecebidos = [];
  let ordem = 0;
  const atualizarVenda = async (id, dados) => {
    idsRecebidos.push(dados.itens.map((item) => item.item_id));
    ordem += 1;
    return {
      id,
      status: "aberta",
      subtotal: ordem === 1 ? 280 : 180,
      total: ordem === 1 ? 265 : 165,
      desconto_venda_valor: 10,
      desconto_valor: 35,
      cupom_code: "CUPOM5",
      cupom_discount_applied: 5,
      itens: dados.itens.map((item, indice) => ({
        ...item,
        id: indice === 0 ? (ordem === 1 ? 91 : 92) : 55,
        venda_id: id,
      })),
      cliente: { id: 35 },
    };
  };
  const persistir = async () =>
    salvarEdicaoVenda({
      vendaAtual: estado,
      payloadVenda: montarPayloadVenda(estado),
      atualizarVenda,
      buscarPagamentos: async () => ({ total_recebido: 165 }),
      finalizarVenda: async () => ({ venda: { id: 34, status: "finalizada", total: 165 } }),
      onVendaPersistida: (dados) => {
        estado = montarVendaPersistidaParaEdicao(estado, dados);
      },
    });
  const primeira = await persistir();
  assert.equal(primeira.finalizada, false);
  assert.deepEqual(
    estado.itens.map((item) => item.id),
    [91, 55],
  );
  assert.deepEqual(
    estado.itens.map((item) => item.desconto_valor),
    [20, 0],
  );
  assert.equal(estado.cliente.credito.limite, 1000);
  assert.equal(estado.cupons_detalhes[0].discount_value, 5);
  assert.equal(estado.desconto_venda_valor, 10);
  estado = recalcularVendaComDescontos(estado, [
    recalcularSubtotalItem(estado.itens[0], 1),
    estado.itens[1],
  ]);
  const segunda = await persistir();
  assert.equal(segunda.finalizada, true);
  assert.deepEqual(idsRecebidos, [
    [50, 55],
    [91, 55],
  ]);
  assert.deepEqual(
    estado.itens.map((item) => item.id),
    [92, 55],
  );
  assert.deepEqual(
    estado.itens.map((item) => item.desconto_valor),
    [20, 0],
  );
});

test("PUT sucedido sincroniza IDs antes de erro de recebimentos para permitir retentar", async () => {
  const erro = new Error("Rede indisponivel");
  const { argumentos } = dependencias({ erroPagamento: erro });
  let atualizado = false;
  argumentos.onVendaPersistida = async () => {
    atualizado = true;
  };
  await assert.rejects(salvarEdicaoVenda(argumentos), erro);
  assert.equal(atualizado, true);
});

test("PUT com ID alterado conserva percentual nominal e calcula proxima quantidade", () => {
  const anterior = {
    id: 34,
    desconto_venda_valor: 0,
    itens: [
      {
        id: 50,
        venda_id: 34,
        produto_id: 85,
        preco_unitario: 100,
        quantidade: 2,
        desconto_valor: 20,
        subtotal: 180,
        tipo_desconto_aplicado: "percentual",
        desconto_percentual: 10,
      },
    ],
  };
  const dto = {
    id: 34,
    desconto_venda_valor: 0,
    subtotal: 180,
    total: 180,
    itens: [
      {
        id: 91,
        item_id_anterior: 50,
        venda_id: 34,
        produto_id: 85,
        preco_unitario: 100,
        quantidade: 2,
        desconto_item: 20,
        subtotal: 180,
      },
    ],
  };
  const sincronizada = montarVendaPersistidaParaEdicao(anterior, dto);
  assert.equal(sincronizada.itens[0].id, 91);
  assert.equal(sincronizada.itens[0].desconto_percentual, 10);
  assert.equal(sincronizada.itens[0].tipo_desconto_aplicado, "percentual");
  assert.equal(recalcularSubtotalItem(sincronizada.itens[0], 3).desconto_valor, 30);
  const sincronizadaDeNovo = montarVendaPersistidaParaEdicao(sincronizada, dto);
  assert.equal(sincronizadaDeNovo.itens[0].desconto_percentual, 10);
});

test("linhas do mesmo SKU conservam seus metodos por ID anterior mesmo com ordem trocada", () => {
  const anterior = {
    id: 34,
    desconto_venda_valor: 0,
    itens: [
      {
        id: 50,
        venda_id: 34,
        produto_id: 85,
        preco_unitario: 100,
        quantidade: 2,
        desconto_valor: 20,
        subtotal: 180,
        tipo_desconto_aplicado: "percentual",
        desconto_percentual: 10,
      },
      {
        id: 55,
        venda_id: 34,
        produto_id: 85,
        preco_unitario: 100,
        quantidade: 2,
        desconto_valor: 7,
        subtotal: 193,
        tipo_desconto_aplicado: "valor",
        desconto_percentual: 3.5,
      },
    ],
  };
  const sincronizada = montarVendaPersistidaParaEdicao(anterior, {
    id: 34,
    desconto_venda_valor: 0,
    subtotal: 373,
    total: 373,
    itens: [
      {
        id: 92,
        item_id_anterior: 55,
        venda_id: 34,
        produto_id: 85,
        preco_unitario: 100,
        quantidade: 2,
        desconto_item: 7,
        subtotal: 193,
      },
      {
        id: 91,
        item_id_anterior: 50,
        venda_id: 34,
        produto_id: 85,
        preco_unitario: 100,
        quantidade: 2,
        desconto_item: 20,
        subtotal: 180,
      },
    ],
  });
  assert.equal(sincronizada.itens[0].tipo_desconto_aplicado, "valor");
  assert.equal(recalcularSubtotalItem(sincronizada.itens[0], 3).desconto_valor, 7);
  assert.equal(sincronizada.itens[1].tipo_desconto_aplicado, "percentual");
  assert.equal(recalcularSubtotalItem(sincronizada.itens[1], 3).desconto_valor, 30);
});

test("centavos preservam 10% escolhido sem inferir percentual efetivo do valor arredondado", () => {
  const anterior = {
    id: 34,
    desconto_venda_valor: 0,
    itens: [
      { id: 50, venda_id: 34, tipo_desconto_aplicado: "percentual", desconto_percentual: 10 },
    ],
  };
  const sincronizada = montarVendaPersistidaParaEdicao(anterior, {
    id: 34,
    desconto_venda_valor: 0,
    subtotal: 3.37,
    total: 3.37,
    itens: [
      {
        id: 91,
        item_id_anterior: 50,
        venda_id: 34,
        quantidade: 0.375,
        preco_unitario: 9.99,
        desconto_item: 0.38,
        subtotal: 3.37,
      },
    ],
  });
  assert.equal(sincronizada.itens[0].desconto_percentual, 10);
  assert.equal(sincronizada.itens[0].desconto_valor, 0.38);
  assert.equal(recalcularSubtotalItem(sincronizada.itens[0], 1).desconto_valor, 1);
});

test("ausencia de identidade ou financeiro divergente mantem Di autoritativo como valor", () => {
  const anterior = {
    id: 34,
    desconto_venda_valor: 0,
    itens: [
      {
        id: 50,
        venda_id: 34,
        produto_id: 85,
        tipo_desconto_aplicado: "percentual",
        desconto_percentual: 10,
      },
    ],
  };
  const dto = {
    id: 34,
    desconto_venda_valor: 0,
    subtotal: 187,
    total: 187,
    itens: [
      {
        id: 91,
        venda_id: 34,
        produto_id: 85,
        quantidade: 2,
        preco_unitario: 100,
        desconto_item: 13,
        subtotal: 187,
      },
    ],
  };
  const semIdentidade = montarVendaPersistidaParaEdicao(anterior, dto);
  assert.equal(semIdentidade.itens[0].tipo_desconto_aplicado, undefined);
  assert.equal(recalcularSubtotalItem(semIdentidade.itens[0], 3).desconto_valor, 13);
  const divergente = montarVendaPersistidaParaEdicao(anterior, {
    ...dto,
    itens: [{ ...dto.itens[0], item_id_anterior: 50 }],
  });
  assert.equal(divergente.itens[0].desconto_valor, 13);
  assert.equal(divergente.itens[0].tipo_desconto_aplicado, undefined);
  assert.equal(recalcularSubtotalItem(divergente.itens[0], 3).desconto_valor, 13);
});
