import assert from "node:assert/strict";
import test from "node:test";

import { atualizarObservacaoComContagem, transcreverContagemCedulas } from "./caixaContagem.js";

test("transcreve as cedulas, moedas e total usados na conferencia", () => {
  const texto = transcreverContagemCedulas({ n100: 2, n20: 1, moedas: "3.50" });

  assert.match(texto, /2 x R\$\s?100,00 = R\$\s?200,00/);
  assert.match(texto, /1 x R\$\s?20,00 = R\$\s?20,00/);
  assert.match(texto, /moedas = R\$\s?3,50/);
  assert.match(texto, /total = R\$\s?223,50/);
});

test("substitui uma contagem automatica anterior sem apagar a observacao manual", () => {
  const anterior = atualizarObservacaoComContagem("Troco do dia anterior", { n50: 1 });
  const atual = atualizarObservacaoComContagem(anterior, { n20: 2 });

  assert.match(atual, /Troco do dia anterior/);
  assert.doesNotMatch(atual, /R\$\s?50,00/);
  assert.equal((atual.match(/\[Contagem de cedulas\]/g) || []).length, 1);
});
