import assert from "node:assert/strict";
import test from "node:test";
import { recarregarPDVAposDevolucao } from "./pdvReturnRefresh.js";

const naoEsperado = async () => assert.fail("Consulta indevida ao atualizar a devolução");

test("devolução da venda exibida recarrega itens, status, pagamentos e crédito pelo carregamento existente", async () => {
  let venda = { id: 14, status: "finalizada", cliente: { id: 7, credito: 0 }, itens: [{ id: 3 }] };
  const chamadas = [];
  await recarregarPDVAposDevolucao({
    devolucao: { venda_id: "14", cliente_id: 7 },
    vendaAtual: venda,
    carregarVendaEspecifica: async (id) => {
      assert.equal(id, 14);
      chamadas.push("venda");
      venda = {
        id,
        status: "devolvida_total",
        itens: [{ id: 3, quantidade_devolvida: 1 }],
        cliente: { id: 7, credito: 56.9 },
        total_pago: 56.9,
      };
    },
    buscarClientePorId: naoEsperado,
    setVendaAtual: naoEsperado,
    recarregarContextoClientePorId: naoEsperado,
    carregarVendasRecentes: async () => chamadas.push("recentes"),
  });
  assert.equal(venda.status, "devolvida_total");
  assert.equal(venda.cliente.credito, 56.9);
  assert.equal(venda.itens[0].quantidade_devolvida, 1);
  assert.deepEqual(chamadas, ["venda", "recentes"]);
});

test("devolução de outra venda do mesmo cliente atualiza crédito e contexto preservando o carrinho", async () => {
  const itens = [{ produto_id: 5, quantidade: 2, subtotal: 90 }];
  const pet = { id: 8 };
  let venda = {
    cliente: { id: 7, credito: 0, campo_local: "preservado" },
    itens,
    pet,
    total: 90,
    observacoes: "pedido em edição",
  };
  const chamadas = [];
  await recarregarPDVAposDevolucao({
    devolucao: { venda_id: 20, cliente_id: "7" },
    vendaAtual: venda,
    carregarVendaEspecifica: naoEsperado,
    buscarClientePorId: async (id) => {
      assert.equal(id, "7");
      return { id: 7, credito: 56.9, nome: "Cliente atualizado" };
    },
    setVendaAtual: (atualizar) => {
      venda = atualizar(venda);
    },
    recarregarContextoClientePorId: async (id) => chamadas.push(["contexto", id]),
    carregarVendasRecentes: async () => chamadas.push(["recentes"]),
  });
  assert.equal(venda.cliente.credito, 56.9);
  assert.equal(venda.cliente.campo_local, "preservado");
  assert.equal(venda.itens, itens);
  assert.equal(venda.pet, pet);
  assert.equal(venda.total, 90);
  assert.equal(venda.observacoes, "pedido em edição");
  assert.deepEqual(chamadas, [["contexto", "7"], ["recentes"]]);
});

test("devolução de outro cliente mantém a venda selecionada e atualiza apenas a lista recente", async () => {
  const venda = { id: 14, cliente: { id: 7, credito: 0 }, itens: [{ produto_id: 1 }] };
  let recentesAtualizadas = false;
  await recarregarPDVAposDevolucao({
    devolucao: { venda_id: 20, cliente_id: 9 },
    vendaAtual: venda,
    carregarVendaEspecifica: naoEsperado,
    buscarClientePorId: naoEsperado,
    setVendaAtual: naoEsperado,
    recarregarContextoClientePorId: naoEsperado,
    carregarVendasRecentes: async () => {
      recentesAtualizadas = true;
    },
  });
  assert.equal(venda.id, 14);
  assert.equal(venda.cliente.credito, 0);
  assert.equal(recentesAtualizadas, true);
});
