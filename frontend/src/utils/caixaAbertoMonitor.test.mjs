import assert from "node:assert/strict";
import test from "node:test";
import {
  criarMonitorCaixaAberto,
  mensagemCaixaIndisponivel,
  opcoesSincronizacaoCaixa,
  precisaConsultarResumoCaixa,
  validarRespostaCaixaAberto,
} from "./caixaAbertoMonitor.js";

const caixa = { id: 9, numero_caixa: 3, status: "aberto" };
const timeout = () => Object.assign(new Error("timeout"), { code: "ECONNABORTED" });

function preparar(consultar) {
  const estados = [];
  const monitor = criarMonitorCaixaAberto({
    consultar,
    onEstado: (estado) => estados.push(estado),
    esperar: async () => {},
  });
  return { monitor, estados, ultimo: () => estados.at(-1) };
}

test("caixa confirmado aberto não vira fechado com timeout e volta a consultar", async () => {
  let falhar = false;
  let chamadas = 0;
  const caso = preparar(async (opcoes) => {
    assert.equal(opcoes.compact, true);
    assert.ok(opcoes.signal instanceof AbortSignal);
    chamadas += 1;
    if (falhar) throw timeout();
    return caixa;
  });
  await caso.monitor.atualizar();
  falhar = true;
  await caso.monitor.atualizar();
  assert.equal(chamadas, 3); // uma confirmação e, depois, tentativa + uma repetição.
  assert.deepEqual(caso.ultimo(), { caixa, status: "erro", atualizando: false });
  falhar = false;
  await caso.monitor.atualizar();
  assert.deepEqual(caso.ultimo(), { caixa, status: "pronto", atualizando: false });
});

test("falha na primeira consulta mantém estado desconhecido e bloqueia ações", async () => {
  const caso = preparar(async () => {
    throw timeout();
  });
  await caso.monitor.atualizar();
  assert.equal(caso.estados[0].status, "carregando");
  assert.equal(caso.ultimo().status, "erro");
  assert.equal(caso.ultimo().caixa, null);
  assert.doesNotMatch(mensagemCaixaIndisponivel(caso.ultimo().status), /fechado|Abra o caixa/);
});

test("somente ausência confirmada fecha o caixa depois de uma consulta bem-sucedida", async () => {
  let aberto = true;
  const caso = preparar(async () => (aberto ? caixa : null));
  await caso.monitor.atualizar();
  aberto = false;
  await caso.monitor.atualizar();
  assert.deepEqual(caso.ultimo(), { caixa: null, status: "pronto", atualizando: false });
  assert.match(mensagemCaixaIndisponivel(caso.ultimo().status), /Caixa fechado/);
});

test("204, JSON vazio e objeto inválido não confirmam fechamento", async () => {
  for (const resposta of [
    { status: 204, data: null },
    { status: 204, data: "" },
    { status: 200, data: undefined },
    { status: 200, data: "" },
    { status: 200, data: {} },
    { status: 200, data: { id: 9, status: "fechado" } },
  ]) {
    assert.throws(() => validarRespostaCaixaAberto(resposta), /confirmar o estado/);
  }
  assert.equal(validarRespostaCaixaAberto({ status: 200, data: null }), null);
  assert.equal(validarRespostaCaixaAberto({ status: 200, data: caixa }), caixa);
  let chamadas = 0;
  const caso = preparar(async () => {
    chamadas += 1;
    return validarRespostaCaixaAberto({ status: 204, data: "" });
  });
  await caso.monitor.atualizar();
  assert.equal(chamadas, 2);
  assert.equal(caso.ultimo().status, "erro");
});

test("GET transitório repete apenas uma vez; erro de permissão não repete nem mantém acesso", async () => {
  for (const status of [502, 503, 504, 401, 403, 422, 500]) {
    let chamadas = 0;
    let falhar = false;
    const caso = preparar(async () => {
      if (!falhar) return caixa;
      chamadas += 1;
      throw Object.assign(new Error("HTTP"), { response: { status } });
    });
    await caso.monitor.atualizar();
    falhar = true;
    await caso.monitor.atualizar();
    assert.equal(chamadas, [502, 503, 504].includes(status) ? 2 : 1);
    assert.equal(caso.ultimo().status, "erro");
    assert.equal(Boolean(caso.ultimo().caixa), ![401, 403].includes(status));
  }
});

test("consultas simultâneas compartilham chamada e cancelamento não apresenta falha", async () => {
  let resolver;
  let chamadas = 0;
  let signal;
  const caso = preparar((opcoes) => {
    chamadas += 1;
    signal = opcoes.signal;
    return new Promise((resolve) => {
      resolver = resolve;
    });
  });
  const primeira = caso.monitor.atualizar();
  assert.equal(primeira, caso.monitor.atualizar());
  await Promise.resolve();
  assert.equal(chamadas, 1);
  caso.monitor.cancelar();
  assert.equal(signal.aborted, true);
  resolver(caixa);
  await primeira;
  assert.equal(caso.estados.length, 1);
  assert.equal(caso.ultimo().status, "carregando");
});

test("fechamento ou mudança de contexto invalida resposta antiga sem reabrir a tela", async () => {
  let resolverAntigo;
  let chamadas = 0;
  const caso = preparar(() => {
    chamadas += 1;
    if (chamadas === 1)
      return new Promise((resolve) => {
        resolverAntigo = resolve;
      });
    return Promise.resolve(null);
  });
  const antiga = caso.monitor.atualizar();
  await Promise.resolve();
  await caso.monitor.atualizar({ invalidar: true });
  resolverAntigo(caixa);
  await antiga;
  assert.deepEqual(caso.ultimo(), { caixa: null, status: "pronto", atualizando: false });
});

test("cancelamento durante intervalo de retry impede nova consulta", async () => {
  let retomar;
  let chamadas = 0;
  const estados = [];
  const monitor = criarMonitorCaixaAberto({
    consultar: async () => {
      chamadas += 1;
      throw timeout();
    },
    onEstado: (estado) => estados.push(estado),
    esperar: () =>
      new Promise((resolve) => {
        retomar = resolve;
      }),
  });
  const andamento = monitor.atualizar();
  while (!retomar) await Promise.resolve();
  monitor.cancelar();
  retomar();
  await andamento;
  assert.equal(chamadas, 1);
  assert.equal(estados.length, 1);
});

test("movimentação de outra aba revalida sem perder caixa ou desmontar modal na falha", async () => {
  let falhar = false;
  const caso = preparar(async () => {
    if (falhar) throw timeout();
    return caixa;
  });
  await caso.monitor.atualizar();
  const anteriores = caso.estados.length;
  falhar = true;
  await caso.monitor.sincronizar(JSON.stringify({ tipo: "movimentacao" }), "7:tenant-atual");
  assert.ok(caso.estados.slice(anteriores).every((estado) => estado.caixa?.id === caixa.id));
  assert.equal(caso.ultimo().status, "erro");
  assert.equal(caso.ultimo().caixa, caixa);
});

test("eventos respeitam tenant/caixa e mantêm compatibilidade com eventos antigos", () => {
  const contexto = { contextoCaixa: "7:tenant-atual", caixaId: 9 };
  assert.deepEqual(opcoesSincronizacaoCaixa('{"tipo":"movimentacao"}', contexto), {
    invalidar: false,
  });
  assert.deepEqual(opcoesSincronizacaoCaixa('{"tipo":"fechamento"}', contexto), {
    invalidar: true,
  });
  assert.deepEqual(opcoesSincronizacaoCaixa('{"tipo":"abertura"}', contexto), { invalidar: true });
  assert.equal(
    opcoesSincronizacaoCaixa('{"tipo":"movimentacao","tenant_id":"outro"}', contexto),
    null,
  );
  assert.equal(opcoesSincronizacaoCaixa('{"tipo":"fechamento","caixa_id":10}', contexto), null);
  assert.equal(opcoesSincronizacaoCaixa(null, contexto), null);
  assert.equal(opcoesSincronizacaoCaixa("inválido", contexto), null);
  assert.deepEqual(
    opcoesSincronizacaoCaixa(
      '{"tipo":"fechamento","tenant_id":"tenant-atual","caixa_id":9}',
      contexto,
    ),
    { invalidar: true },
  );
});

test("abrir sangria enquanto consulta está pendente mantém a necessidade do mesmo resumo", () => {
  const antes = precisaConsultarResumoCaixa({ menuAberto: true, modalAtivo: null });
  const depois = precisaConsultarResumoCaixa({ menuAberto: false, modalAtivo: "sangria" });
  assert.equal(antes, true);
  assert.equal(depois, antes); // A dependência do efeito não muda nem aborta a consulta.
  assert.equal(precisaConsultarResumoCaixa({ menuAberto: false, modalAtivo: null }), false);
});
