import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const configSource = readFileSync(
  new URL("./ConfiguracaoGeralNegocio.jsx", import.meta.url),
  "utf8",
);
const menuSource = readFileSync(new URL("../../components/MenuCaixa.jsx", import.meta.url), "utf8");

test("configuracao permite habilitar o caixa compartilhado pela empresa", () => {
  assert.match(configSource, /caixa_compartilhado: false/);
  assert.match(configSource, /Compartilhar entre usuarios/);
  assert.match(configSource, /caixa_compartilhado: Boolean\(form\.caixa_compartilhado\)/);
});

test("configuracao separa o nome de acesso do nome fantasia", () => {
  assert.match(configSource, /nome_acesso: ""/);
  assert.match(configSource, /Nome de acesso da loja/);
  assert.match(configSource, /independente do nome fantasia/);
  assert.match(configSource, /nome_acesso: nomeAcesso/);
  assert.match(configSource, /nome anterior continua funcionando como alias/);
});

test("menu identifica quando o usuario esta operando um caixa compartilhado", () => {
  assert.match(menuSource, /caixaAberto\.compartilhado/);
  assert.match(menuSource, /Compartilhado/);
  assert.match(menuSource, /Aberto por/);
});
