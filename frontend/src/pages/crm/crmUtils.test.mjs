import assert from "node:assert/strict";
import { test } from "node:test";
import {
  exigenciasDaMovimentacao,
  situacaoDoPasso,
  unificarQuadros,
  validarColunas,
} from "./crmUtils.js";

const coluna = (id, nome, tipo, ordem, cards = []) => ({
  id,
  nome,
  tipo,
  ordem,
  total: cards.length,
  valor_total: cards.reduce((soma, card) => soma + (card.valor || 0), 0),
  cards,
});

test("unificarQuadros junta colunas de mesmo nome e marca a loja de cada card", () => {
  const lojas = [
    {
      loja_id: "A",
      loja_nome: "Loja A",
      colunas: [coluna(1, "Novo", "entrada", 1, [{ id: 10 }]), coluna(2, "Feito", "concluido", 2)],
    },
    {
      loja_id: "B",
      loja_nome: "Loja B",
      colunas: [coluna(7, "novo", "entrada", 1, [{ id: 20 }])],
    },
  ];

  const colunas = unificarQuadros(lojas);

  assert.equal(colunas.length, 2);
  assert.equal(colunas[0].total, 2);
  assert.deepEqual(colunas[0].idPorLoja, { A: 1, B: 7 });
  assert.deepEqual(
    colunas[0].cards.map((card) => [card.id, card.loja_nome]),
    [
      [10, "Loja A"],
      [20, "Loja B"],
    ],
  );
  assert.deepEqual(colunas[1].idPorLoja, { A: 2 });
});

test("situacaoDoPasso: sem passo e hoje pedem atenção, atrasado é vermelho, futuro é neutro", () => {
  const agora = new Date(2026, 9, 22, 15, 0, 0);

  assert.equal(situacaoDoPasso(null, agora).codigo, "sem_passo");
  assert.equal(
    situacaoDoPasso({ agendado_para: new Date(2026, 9, 22, 8).toISOString() }, agora).codigo,
    "hoje",
  );
  assert.equal(
    situacaoDoPasso({ agendado_para: new Date(2026, 9, 21, 20).toISOString() }, agora).codigo,
    "atrasado",
  );
  assert.equal(
    situacaoDoPasso({ agendado_para: new Date(2026, 9, 25, 9).toISOString() }, agora).codigo,
    "futuro",
  );
  assert.match(
    situacaoDoPasso({ agendado_para: new Date(2026, 9, 21).toISOString() }, agora).texto,
    /Atrasado/,
  );
});

test("exigenciasDaMovimentacao pede resultado só ao concluir com oportunidades abertas", () => {
  const card = { oportunidades: [{ id: 1, tipo: "vacina" }] };
  const andamento = { tipo: "andamento" };
  const concluido = { tipo: "concluido" };
  const encerrado = { tipo: "encerrado" };

  assert.equal(exigenciasDaMovimentacao(card, andamento, andamento).exigeModal, false);
  assert.equal(exigenciasDaMovimentacao(card, concluido, andamento).exigeModal, true);
  assert.equal(
    exigenciasDaMovimentacao({ oportunidades: [] }, concluido, andamento).exigeModal,
    false,
  );
  assert.equal(
    exigenciasDaMovimentacao({ oportunidades: [] }, encerrado, andamento).exigeMotivoDaPerda,
    true,
  );
  // De coluna final para outra final não repete a pergunta.
  assert.equal(exigenciasDaMovimentacao(card, encerrado, concluido).exigeModal, false);
});

test("validarColunas segue as regras do servidor", () => {
  const c = (nome, tipo) => ({ nome, tipo });

  assert.equal(validarColunas([c("Novo", "entrada"), c("Feito", "concluido")]), "");
  assert.match(validarColunas([c("Novo", "entrada")]), /pelo menos duas/);
  assert.match(validarColunas([c("Novo", "andamento"), c("Feito", "concluido")]), /entrada/);
  assert.match(validarColunas([c("Novo", "entrada"), c("Feito", "andamento")]), /concluído/);
  assert.match(validarColunas([c("Novo", "entrada"), c("novo", "concluido")]), /Já existe/);
  assert.match(validarColunas([c("", "entrada"), c("Feito", "concluido")]), /nome/);
  const nove = Array.from({ length: 9 }, (_, i) => c(`C${i}`, "andamento"));
  assert.match(validarColunas(nove), /no máximo 8/);
});
