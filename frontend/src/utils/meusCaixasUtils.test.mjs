import assert from "node:assert/strict";
import { test } from "node:test";
import {
  iniciarConsultaCaixas,
  mensagemErroConsultaCaixas,
  parametrosHistoricoCaixas,
  podeReabrirCaixa,
  separarPaginaCaixas,
} from "./meusCaixasUtils.js";

function pendente() {
  let resolve;
  let reject;
  const promise = new Promise((sucesso, falha) => {
    resolve = sucesso;
    reject = falha;
  });
  return { promise, resolve, reject };
}

test("consulta compacta mantém filtros e busca uma sentinela além dos 25 caixas", () => {
  assert.deepEqual(
    parametrosHistoricoCaixas(
      { data_inicio: "2026-10-01", data_fim: "2026-10-09", status: "fechado" },
      2,
    ),
    {
      compact: true,
      limit: 26,
      offset: 50,
      data_inicio: "2026-10-01",
      data_fim: "2026-10-09",
      status_filter: "fechado",
    },
  );
  assert.deepEqual(parametrosHistoricoCaixas(), { compact: true, limit: 26, offset: 0 });
});

test("paginação permite percorrer todo o histórico sem duplicar ou perder a sentinela", () => {
  const historico = Array.from({ length: 51 }, (_, indice) => ({ id: indice + 1 }));
  const paginas = [0, 1, 2].map((pagina) => {
    const params = parametrosHistoricoCaixas({}, pagina);
    return separarPaginaCaixas(historico.slice(params.offset, params.offset + params.limit));
  });
  assert.deepEqual(
    paginas.map((pagina) => pagina.temProximaPagina),
    [true, true, false],
  );
  assert.deepEqual(
    paginas.flatMap((pagina) => pagina.caixas),
    historico,
  );
  assert.equal(separarPaginaCaixas(historico.slice(0, 25)).temProximaPagina, false);
});

test("erro de resposta não se transforma em histórico vazio", async () => {
  let caixas = [{ id: 1 }];
  let erro = "";
  const consulta = iniciarConsultaCaixas({
    consultar: async () => ({ detail: "Inválido" }),
    onSucesso: (resposta) => {
      caixas = separarPaginaCaixas(resposta).caixas;
    },
    onErro: (falha) => {
      erro = falha.message;
    },
  });
  await consulta.finalizado;
  assert.deepEqual(caixas, [{ id: 1 }]);
  assert.match(erro, /Resposta inválida/);
});

test("falha de rede mantém os dados anteriores e permite uma nova consulta bem-sucedida", async () => {
  let caixas = [{ id: 1 }];
  let erro = "";
  let loading = false;
  const callbacks = {
    onIniciar: () => {
      loading = true;
      erro = "";
    },
    onSucesso: (resposta) => {
      caixas = separarPaginaCaixas(resposta).caixas;
    },
    onErro: (falha) => {
      erro = mensagemErroConsultaCaixas(falha, "Falha no histórico");
    },
    onFim: () => {
      loading = false;
    },
  };
  await iniciarConsultaCaixas({
    ...callbacks,
    consultar: async () => {
      throw new Error("timeout");
    },
  }).finalizado;
  assert.equal(erro, "Falha no histórico");
  assert.equal(loading, false);
  assert.deepEqual(caixas, [{ id: 1 }]);
  await iniciarConsultaCaixas({ ...callbacks, consultar: async () => [{ id: 2 }] }).finalizado;
  assert.equal(erro, "");
  assert.deepEqual(caixas, [{ id: 2 }]);
});

test("resposta antiga após mudança de filtro não substitui a página atual", async () => {
  const antiga = pendente();
  let caixas = [];
  let finalizacoes = 0;
  const callbacks = {
    onSucesso: (resposta) => {
      caixas = resposta;
    },
    onErro: () => assert.fail("Consulta cancelada não deve mostrar erro"),
    onFim: () => {
      finalizacoes += 1;
    },
  };
  const consultaAntiga = iniciarConsultaCaixas({ ...callbacks, consultar: () => antiga.promise });
  consultaAntiga.cancelar();
  await iniciarConsultaCaixas({ ...callbacks, consultar: async () => [{ id: 2 }] }).finalizado;
  antiga.resolve([{ id: 1 }]);
  await consultaAntiga.finalizado;
  assert.deepEqual(caixas, [{ id: 2 }]);
  assert.equal(finalizacoes, 1);
});

test("cancelar ao desmontar aborta a requisição sem atualizar estado nem apresentar erro", async () => {
  const requisicao = pendente();
  let signal;
  let alteracoes = 0;
  const consulta = iniciarConsultaCaixas({
    consultar: (sinal) => {
      signal = sinal;
      return requisicao.promise;
    },
    onSucesso: () => {
      alteracoes += 1;
    },
    onErro: () => {
      alteracoes += 1;
    },
    onFim: () => {
      alteracoes += 1;
    },
  });
  consulta.cancelar();
  assert.equal(signal.aborted, true);
  requisicao.reject(new Error("Cancelado"));
  await consulta.finalizado;
  assert.equal(alteracoes, 0);
});

test("histórico aparece enquanto caixa aberto está pendente e sua falha não apaga o histórico", async () => {
  const atual = pendente();
  let caixas = [];
  let statusAberto = "carregando";
  const consultaAberto = iniciarConsultaCaixas({
    consultar: () => atual.promise,
    onSucesso: () => {
      statusAberto = "pronto";
    },
    onErro: () => {
      statusAberto = "erro";
    },
  });
  await iniciarConsultaCaixas({
    consultar: async () => [{ id: 9 }],
    onSucesso: (resposta) => {
      caixas = separarPaginaCaixas(resposta).caixas;
    },
    onErro: () => assert.fail("Histórico deveria ter carregado"),
  }).finalizado;
  assert.deepEqual(caixas, [{ id: 9 }]);
  assert.equal(statusAberto, "carregando");
  assert.equal(podeReabrirCaixa(statusAberto, null), false);
  atual.reject(new Error("Timeout no aberto"));
  await consultaAberto.finalizado;
  assert.equal(statusAberto, "erro");
  assert.equal(podeReabrirCaixa(statusAberto, null), false);
  assert.deepEqual(caixas, [{ id: 9 }]);
});

test("reabertura só libera após confirmar que não há caixa aberto", () => {
  assert.equal(podeReabrirCaixa("carregando", null), false);
  assert.equal(podeReabrirCaixa("erro", null), false);
  assert.equal(podeReabrirCaixa("pronto", { id: 1 }), false);
  assert.equal(podeReabrirCaixa("pronto", null), true);
});

test("mensagem de erro usa detalhe textual sem tentar renderizar objetos de validação", () => {
  assert.equal(
    mensagemErroConsultaCaixas({ response: { data: { detail: "Sem permissão" } } }, "Falha"),
    "Sem permissão",
  );
  assert.equal(
    mensagemErroConsultaCaixas({ response: { data: { detail: [{ msg: "Inválido" }] } } }, "Falha"),
    "Falha",
  );
});
