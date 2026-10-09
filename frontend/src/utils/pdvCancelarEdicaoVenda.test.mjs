import assert from "node:assert/strict";
import { test } from "node:test";
import { cancelarEdicaoVenda } from "./pdvCancelarEdicaoVenda.js";

function preparar({
  vendaId = 34,
  status = "aberta",
  originalId = 34,
  original = "finalizada",
  restaurar,
} = {}) {
  const chamadas = [];
  return {
    chamadas,
    argumentos: {
      vendaAtual: { id: vendaId, status },
      restauracao: { vendaId: originalId, status: original },
      restaurarStatus: async (id, statusOriginal) => {
        chamadas.push(["PATCH", id, statusOriginal]);
        await restaurar?.();
      },
      recarregarContextoCliente: async () => chamadas.push(["CONTEXTO"]),
      limparRestauracao: () => chamadas.push(["RESET"]),
      limparVenda: () => chamadas.push(["LIMPAR"]),
      carregarVendasRecentes: () => chamadas.push(["RECENTES"]),
    },
  };
}

test("cancelar espera restauracao do servidor antes de atualizar beneficios e limpar tela", async () => {
  let liberar;
  const pendente = new Promise((resolve) => {
    liberar = resolve;
  });
  const { chamadas, argumentos } = preparar({ restaurar: () => pendente });
  const cancelamento = cancelarEdicaoVenda(argumentos);
  assert.deepEqual(chamadas, [["PATCH", 34, "finalizada"]]);
  liberar();
  await cancelamento;
  assert.deepEqual(chamadas, [
    ["PATCH", 34, "finalizada"],
    ["CONTEXTO"],
    ["RESET"],
    ["LIMPAR"],
    ["RECENTES"],
  ]);
});

test("falha de restauracao conserva tela e referencia para nova tentativa", async () => {
  const erro = new Error("Caixa indisponivel");
  const { chamadas, argumentos } = preparar({
    restaurar: async () => {
      throw erro;
    },
  });
  await assert.rejects(cancelarEdicaoVenda(argumentos), erro);
  assert.deepEqual(chamadas, [["PATCH", 34, "finalizada"]]);
});

test("status original da venda A nunca restaura a venda B", async () => {
  const { chamadas, argumentos } = preparar({ vendaId: 35 });
  await cancelarEdicaoVenda(argumentos);
  assert.deepEqual(chamadas, [["RESET"], ["LIMPAR"], ["RECENTES"]]);
});

test("venda que ja tem status original descarta edicao sem restaurar novamente", async () => {
  const { chamadas, argumentos } = preparar({ status: "finalizada" });
  await cancelarEdicaoVenda(argumentos);
  assert.deepEqual(chamadas, [["RESET"], ["LIMPAR"], ["RECENTES"]]);
});

test("venda nova nao aplica restauracao pendente de uma venda anterior", async () => {
  const { chamadas, argumentos } = preparar({ vendaId: null });
  await cancelarEdicaoVenda(argumentos);
  assert.deepEqual(chamadas, [["RESET"], ["LIMPAR"], ["RECENTES"]]);
});
