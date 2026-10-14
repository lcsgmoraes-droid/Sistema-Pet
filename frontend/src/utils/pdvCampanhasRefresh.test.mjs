import assert from "node:assert/strict";
import { test } from "node:test";
import { criarAtualizadorSaldoCampanhas } from "./pdvCampanhasRefresh.js";

function fixture(buscarSaldo, options = {}) {
  const timers = new Map();
  const saldos = [];
  const erros = [];
  let timerId = 0;
  const atualizador = criarAtualizadorSaldoCampanhas({
    buscarSaldo,
    onSaldo: (saldo) => saldos.push(saldo),
    onErro: (erro) => erros.push(erro),
    agendar: (callback) => {
      timers.set(++timerId, callback);
      return timerId;
    },
    cancelarAgendamento: (id) => timers.delete(id),
    ...options,
  });
  const proximo = async () => {
    const [id, callback] = timers.entries().next().value;
    timers.delete(id);
    callback();
    await new Promise(setImmediate);
  };
  return { atualizador, saldos, erros, timers, proximo };
}

test("acompanha processamento e atualiza cashback/cupons sem recarregar pagina", async () => {
  const respostas = [
    { customer_id: 35, saldo_cashback: 0, beneficios_em_processamento: true },
    { customer_id: 35, saldo_cashback: 0, beneficios_em_processamento: true },
    {
      customer_id: 35,
      saldo_cashback: 12,
      total_carimbos: 2,
      cupons_ativos: [{ code: "FIDELIDADE20" }],
      beneficios_em_processamento: false,
    },
  ];
  const f = fixture(async () => respostas.shift());
  await f.atualizador.atualizar(35);
  await f.proximo();
  await f.proximo();
  assert.equal(f.saldos.at(-1).saldo_cashback, 12);
  assert.equal(f.saldos.at(-1).total_carimbos, 2);
  assert.deepEqual(f.saldos.at(-1).cupons_ativos, [{ code: "FIDELIDADE20" }]);
  assert.equal(f.saldos.at(-1).beneficios_em_processamento, false);
  assert.equal(f.timers.size, 0);
});

test("saldo concluido nao inicia polling", async () => {
  const f = fixture(async () => ({ saldo_cashback: 0, beneficios_em_processamento: false }));
  await f.atualizador.atualizar(35);
  assert.equal(f.saldos.at(-1).saldo_cashback, 0);
  assert.equal(f.timers.size, 0);
});

test("trocar cliente aborta requisicao e ignora resposta antiga", async () => {
  let resolverAntigo;
  let signalAntigo;
  const f = fixture((clienteId, { signal }) => {
    if (clienteId === 35) {
      signalAntigo = signal;
      return new Promise((resolve) => {
        resolverAntigo = resolve;
      });
    }
    return Promise.resolve({ customer_id: clienteId, saldo_cashback: 5 });
  });
  const antiga = f.atualizador.atualizar(35);
  await f.atualizador.atualizar(36);
  resolverAntigo({ customer_id: 35, saldo_cashback: 12, beneficios_em_processamento: true });
  await antiga;
  assert.equal(signalAntigo.aborted, true);
  assert.deepEqual(
    f.saldos.map((saldo) => saldo.customer_id),
    [36],
  );
  assert.equal(f.timers.size, 0);
});

test("cancelar ao desmontar ou remover cliente elimina polling", async () => {
  const f = fixture(async () => ({ beneficios_em_processamento: true }));
  await f.atualizador.atualizar(35);
  assert.equal(f.timers.size, 1);
  f.atualizador.cancelar();
  assert.equal(f.timers.size, 0);
  assert.equal(f.saldos.length, 1);
});

test("fila longa encerra consultas com sinal pendente sem fabricar saldo zero", async () => {
  const f = fixture(async () => ({ saldo_cashback: 8, beneficios_em_processamento: true }), {
    maxConsultas: 2,
  });
  await f.atualizador.atualizar(35);
  await f.proximo();
  assert.equal(f.saldos.at(-1).saldo_cashback, 8);
  assert.equal(f.saldos.at(-1).beneficios_consulta_limite, true);
  assert.equal(f.timers.size, 0);
});

test("erro de consulta mantem saldo anterior e permite tentativa limitada", async () => {
  let consulta = 0;
  const f = fixture(async () => {
    consulta += 1;
    if (consulta === 1) return { saldo_cashback: 8, beneficios_em_processamento: true };
    throw new Error("sem conexao");
  });
  await f.atualizador.atualizar(35);
  await f.proximo();
  await f.proximo();
  await f.proximo();
  assert.equal(f.saldos.at(-1).saldo_cashback, 8);
  assert.equal(f.saldos.length, 1);
  assert.equal(f.erros.length, 3);
  assert.equal(f.timers.size, 0);
});
