import assert from "node:assert/strict";
import { test } from "node:test";

import { calcularTotalBase, nomeArquivoPdf, sortearEmpresas } from "./orcamentosGrupoUtils.js";

test("calcula o total do orçamento principal", () => {
  assert.equal(
    calcularTotalBase([
      { quantidade: 2, preco_unitario_base: 10 },
      { quantidade: 1.5, preco_unitario_base: 20 },
    ]),
    50,
  );
});

test("sorteio preserva empresas fixadas e não repete seleção", () => {
  const resultado = sortearEmpresas({
    empresas: [{ id: 1 }, { id: 2 }, { id: 3 }],
    selecoes: [
      { empresa_id: 2, fixada: true },
      { empresa_id: 1, fixada: false },
    ],
    quantidade: 2,
    random: () => 0,
  });

  assert.equal(resultado[0].empresa_id, 2);
  assert.equal(resultado[0].fixada, true);
  assert.equal(new Set(resultado.map((item) => item.empresa_id)).size, 2);
});

test("nomeia PDF individual e conjunto", () => {
  assert.equal(nomeArquivoPdf({ numero: "ORC-1" }, 5), "ORC-1-cotacao-5.pdf");
  assert.equal(nomeArquivoPdf({ numero: "ORC-1" }), "ORC-1-todos.pdf");
});
