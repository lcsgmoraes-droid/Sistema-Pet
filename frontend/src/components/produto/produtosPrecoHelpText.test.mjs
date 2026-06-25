import assert from "node:assert/strict";
import test from "node:test";

import { MARGEM_HELP_TEXT, MARKUP_HELP_TEXT } from "./produtosPrecoHelpText.js";

test("explica markup como percentual sobre o custo", () => {
  assert.match(MARKUP_HELP_TEXT, /Markup/);
  assert.match(MARKUP_HELP_TEXT, /custo/i);
  assert.match(MARKUP_HELP_TEXT, /\(PV - custo\) \/ custo x 100/);
});

test("explica margem como percentual sobre o preco de venda", () => {
  assert.match(MARGEM_HELP_TEXT, /Margem/);
  assert.match(MARGEM_HELP_TEXT, /preco de venda/i);
  assert.match(MARGEM_HELP_TEXT, /\(PV - custo\) \/ PV x 100/);
});

test("diferencia markup e margem com o mesmo exemplo", () => {
  assert.match(MARKUP_HELP_TEXT, /custo 10 e venda 15/i);
  assert.match(MARKUP_HELP_TEXT, /markup 50%/i);
  assert.match(MARGEM_HELP_TEXT, /custo 10 e venda 15/i);
  assert.match(MARGEM_HELP_TEXT, /margem 33,33%/i);
});
