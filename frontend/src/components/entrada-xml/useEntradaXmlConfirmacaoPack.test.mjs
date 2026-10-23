import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createControllerHarness } from "../../../scripts/helpers/reactControllerHarness.mjs";

const criarItem = (dados = {}) => ({
  id: 101,
  produto_id: 501,
  quantidade: 18,
  valor_unitario: 2.59,
  valor_total: 46.62,
  custo_aquisicao_total: 46.62,
  pack_multiplicador_detectado: 18,
  ...dados,
});

const criarNota = (itens = [criarItem()], dados = {}) => ({
  id: 11,
  status: "pendente",
  itens,
  ...dados,
});

function preparar(multiplicadoresPack = {}) {
  const erros = [];
  const harness = createControllerHarness(
    fileURLToPath(new URL("./useEntradaXmlConfirmacaoPack.js", import.meta.url)),
    {
      mocks: new Map(),
      props: {
        multiplicadoresPack,
        toast: { error: (mensagem) => erros.push(mensagem) },
      },
    },
  );
  return { harness, erros };
}

async function validar(harness, nota, overrides) {
  let resultado;
  await harness.act(() => {
    resultado = harness.tree.validarConfirmacoesPack(nota, overrides);
  });
  return resultado;
}

test("exige OK de todos os packs e aponta o primeiro item ainda pendente", async () => {
  const primeiro = criarItem();
  const segundo = criarItem({ id: 102, produto_id: 502, pack_multiplicador_detectado: 12 });
  const semPack = criarItem({ id: 103, pack_multiplicador_detectado: 1 });
  const nota = criarNota([semPack, primeiro, segundo]);
  const { harness, erros } = preparar();

  assert.equal(harness.tree.obterConfirmacaoPackItem(nota, primeiro).necessaria, true);
  assert.equal(harness.tree.obterConfirmacaoPackItem(nota, primeiro).confirmada, false);
  assert.equal(await validar(harness, nota), false);
  assert.equal(harness.tree.pendenciaConfirmacaoPack.notaId, nota.id);
  assert.equal(harness.tree.pendenciaConfirmacaoPack.itemId, primeiro.id);
  const primeiraTentativa = harness.tree.pendenciaConfirmacaoPack.tentativa;

  assert.equal(await validar(harness, nota), false);
  assert.notEqual(harness.tree.pendenciaConfirmacaoPack.tentativa, primeiraTentativa);
  assert.ok(erros.length >= 1);

  await harness.act(() => harness.tree.confirmarPackItem(nota, primeiro));
  assert.equal(harness.tree.obterConfirmacaoPackItem(nota, primeiro).confirmada, true);
  assert.equal(harness.tree.pendenciaConfirmacaoPack, null);
  assert.equal(await validar(harness, nota), false);
  assert.equal(harness.tree.pendenciaConfirmacaoPack.itemId, segundo.id);

  await harness.act(() => harness.tree.confirmarPackItem(nota, segundo));
  assert.equal(await validar(harness, nota), true);
});

test("sem sugestão ou nota já processada permite seguir sem confirmação", async () => {
  const { harness, erros } = preparar();
  const semPack = criarItem({ pack_multiplicador_detectado: 1 });
  const notaSemPack = criarNota([semPack]);
  assert.equal(harness.tree.obterConfirmacaoPackItem(notaSemPack, semPack).necessaria, false);
  assert.equal(await validar(harness, notaSemPack), true);

  const processada = criarNota([criarItem()], { status: "processada" });
  assert.equal(
    harness.tree.obterConfirmacaoPackItem(processada, processada.itens[0]).necessaria,
    false,
  );
  assert.equal(await validar(harness, processada), true);
  assert.deepEqual(erros, []);
});

test("pack manual exige OK mesmo sem detecção e trocar sugestão por um não dispensa o OK", async () => {
  const manual = criarItem({ pack_multiplicador_detectado: 1 });
  const { harness } = preparar({ [manual.id]: 6 });
  const notaManual = criarNota([manual]);
  assert.equal(harness.tree.obterConfirmacaoPackItem(notaManual, manual).necessaria, true);
  assert.equal(await validar(harness, notaManual), false);
  await harness.act(() => harness.tree.confirmarPackItem(notaManual, manual));
  assert.equal(await validar(harness, notaManual), true);

  const automatico = criarItem();
  const notaAutomatica = criarNota([automatico]);
  await harness.update({ multiplicadoresPack: { [automatico.id]: 1 } });
  assert.equal(harness.tree.obterConfirmacaoPackItem(notaAutomatica, automatico).necessaria, true);
  assert.equal(await validar(harness, notaAutomatica), false);
  await harness.act(() => harness.tree.confirmarPackItem(notaAutomatica, automatico));
  assert.equal(await validar(harness, notaAutomatica), true);
});

test("editar multiplicador invalida o aceite e exige novo OK para o valor atual", async () => {
  const item = criarItem();
  const nota = criarNota([item]);
  const { harness } = preparar();
  await harness.act(() => harness.tree.confirmarPackItem(nota, item));
  assert.equal(await validar(harness, nota), true);

  await harness.update({ multiplicadoresPack: { [item.id]: 12 } });
  assert.equal(harness.tree.obterConfirmacaoPackItem(nota, item).confirmada, false);
  assert.equal(await validar(harness, nota), false);
  await harness.act(() => harness.tree.confirmarPackItem(nota, item));
  assert.equal(await validar(harness, nota), true);

  await harness.act(() => harness.tree.invalidarConfirmacaoPackItem(nota.id, item.id));
  assert.equal(await validar(harness, nota), false);
});

test("um OK não vale para outra nota e limpar confirmações reinicia a conferência", async () => {
  const item = criarItem();
  const nota = criarNota([item]);
  const outraNota = criarNota([item], { id: 12 });
  const { harness } = preparar();

  await harness.act(() => harness.tree.confirmarPackItem(nota, item));
  assert.equal(await validar(harness, nota), true);
  assert.equal(await validar(harness, outraNota), false);
  assert.equal(harness.tree.pendenciaConfirmacaoPack.notaId, outraNota.id);
  assert.equal(harness.tree.obterConfirmacaoPackItem(nota, item).confirmada, true);

  await harness.act(() => harness.tree.limparConfirmacoesPack());
  assert.equal(harness.tree.obterConfirmacaoPackItem(nota, item).confirmada, false);
  assert.equal(await validar(harness, nota), false);
});

test("mudanças nos dados revisados tornam o aceite anterior insuficiente", async () => {
  const item = criarItem();
  const nota = criarNota([item]);
  const { harness } = preparar();
  await harness.act(() => harness.tree.confirmarPackItem(nota, item));

  for (const alteracao of [
    { produto_id: 999 },
    { quantidade: 19 },
    { valor_unitario: 3.5 },
    { custo_aquisicao_unitario: 3.5 },
    { valor_total: 50 },
    { pack_multiplicador_detectado: 12 },
  ]) {
    const alterado = { ...item, ...alteracao };
    const notaAlterada = { ...nota, itens: [alterado] };
    assert.equal(
      harness.tree.obterConfirmacaoPackItem(notaAlterada, alterado).confirmada,
      false,
      `O aceite deve ser revisto ao alterar ${Object.keys(alteracao)[0]}`,
    );
    assert.equal(await validar(harness, notaAlterada), false);
  }
});

test("validação usa overrides recebidos explicitamente em vez do mapa de outra nota", async () => {
  const item = criarItem({ pack_multiplicador_detectado: 1 });
  const nota = criarNota([item]);
  const { harness } = preparar({ [item.id]: 12 });
  assert.equal(await validar(harness, nota), false);
  assert.equal(await validar(harness, nota, {}), true);
  assert.equal(await validar(harness, nota, { [item.id]: 6 }), false);
});
