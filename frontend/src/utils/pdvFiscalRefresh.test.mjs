import assert from "node:assert/strict";
import test from "node:test";
import { atualizarSituacaoFiscalVenda, mesclarSituacaoFiscalVenda } from "./pdvFiscalRefresh.js";
import { podeCancelarVendaComNotaCancelada } from "./pdvFiscalStatus.js";

const vendaEmitida = {
  id: 12,
  status: "pago_nf",
  nfe_tipo: "nfce",
  nfe_numero: 18574,
  nfe_status: "autorizada",
  nfe_provider: "intnfe",
  nfe_correlation_id: "documento-12",
};
const indevido = async () => assert.fail("Não deveria consultar este emissor");

test("abrir venda atualiza nota autorizada antiga para cancelada confirmada pelo emissor", async () => {
  const chamadas = [];
  const venda = await atualizarSituacaoFiscalVenda(vendaEmitida, {
    consultarIntNFe: async (id) => chamadas.push(["emissor", id]),
    sincronizarBling: indevido,
    buscarVenda: async (id) => {
      chamadas.push(["venda", id]);
      return { ...vendaEmitida, nfe_status: "cancelada", status: "finalizada" };
    },
  });
  assert.deepEqual(chamadas, [
    ["emissor", 12],
    ["venda", 12],
  ]);
  assert.equal(venda.nfe_status, "cancelada");
  assert.equal(venda.status, "finalizada");
  assert.equal(podeCancelarVendaComNotaCancelada(venda), true);
});

test("nota Bling usa sincronização de status e recarrega a venda", async () => {
  let sincronizou = false;
  const inicial = {
    ...vendaEmitida,
    nfe_provider: "bling",
    nfe_correlation_id: null,
    nfe_bling_id: 81,
  };
  const venda = await atualizarSituacaoFiscalVenda(inicial, {
    consultarIntNFe: indevido,
    sincronizarBling: async (id) => {
      assert.equal(id, 12);
      sincronizou = true;
    },
    buscarVenda: async () => {
      assert.equal(sincronizou, true);
      return { ...inicial, nfe_status: "Cancelada", status: "finalizada" };
    },
  });
  assert.equal(podeCancelarVendaComNotaCancelada(venda), true);
});

test("solicitação de cancelamento ainda pendente não libera cancelar a venda", async () => {
  const venda = await atualizarSituacaoFiscalVenda(vendaEmitida, {
    consultarIntNFe: async () => ({ cancelamento_solicitado: true, processando: true }),
    sincronizarBling: indevido,
    buscarVenda: async () => vendaEmitida,
  });
  assert.equal(venda.nfe_status, "autorizada");
  assert.equal(podeCancelarVendaComNotaCancelada(venda), false);
});

test("falha do emissor mantém a última situação e sinaliza consulta indisponível", async () => {
  const venda = await atualizarSituacaoFiscalVenda(vendaEmitida, {
    consultarIntNFe: async () => {
      throw new Error("Indisponível");
    },
    sincronizarBling: indevido,
    buscarVenda: indevido,
  });
  assert.equal(venda.nfe_status, "autorizada");
  assert.equal(venda.nfe_atualizacao_falhou, true);
  assert.equal(podeCancelarVendaComNotaCancelada(venda), false);
});

test("não faz consulta fiscal para venda sem nota ou com cancelamento já confirmado", async () => {
  for (const venda of [
    { id: 13, status: "aberta" },
    { ...vendaEmitida, nfe_status: "cancelada" },
  ]) {
    assert.equal(
      await atualizarSituacaoFiscalVenda(venda, {
        consultarIntNFe: indevido,
        sincronizarBling: indevido,
        buscarVenda: indevido,
      }),
      venda,
    );
  }
});

test("atualização ao retornar de outra aba preserva itens e dados locais da venda", () => {
  const atual = { ...vendaEmitida, itens: [{ id: 8 }], cliente: { id: 2 }, observacoes: "Manter" };
  const venda = mesclarSituacaoFiscalVenda(atual, {
    ...vendaEmitida,
    nfe_status: "cancelada",
    status: "finalizada",
    itens: [],
  });
  assert.equal(venda.nfe_status, "cancelada");
  assert.equal(venda.status, "finalizada");
  assert.equal(venda.itens, atual.itens);
  assert.equal(venda.cliente, atual.cliente);
  assert.equal(venda.observacoes, "Manter");
});

test("consulta atrasada não sobrescreve outra venda selecionada nem reativa venda cancelada", () => {
  const outra = { id: 50, status: "aberta", itens: [] };
  assert.equal(mesclarSituacaoFiscalVenda(outra, vendaEmitida), outra);
  const cancelada = { ...vendaEmitida, status: "cancelada", nfe_status: "cancelada" };
  assert.equal(mesclarSituacaoFiscalVenda(cancelada, vendaEmitida), cancelada);
});

test("resposta atrasada não regride cancelamento confirmado da mesma nota", () => {
  const cancelada = { ...vendaEmitida, status: "finalizada", nfe_status: "cancelada" };
  assert.equal(mesclarSituacaoFiscalVenda(cancelada, vendaEmitida), cancelada);
  const novaNota = { ...vendaEmitida, nfe_correlation_id: "nova-emissao" };
  assert.equal(mesclarSituacaoFiscalVenda(cancelada, novaNota).nfe_status, "autorizada");
});
