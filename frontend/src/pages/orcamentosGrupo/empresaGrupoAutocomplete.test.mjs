import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const source = readFileSync(new URL("./EmpresaGrupoConfigPanel.jsx", import.meta.url), "utf8");

test("busca empresas automaticamente com o seletor padrão de pessoas", () => {
  assert.match(source, /<PessoaSelector/);
  assert.match(source, /window\.setTimeout\(async \(\) => \{/);
  assert.match(source, /\}, 300\);/);
  assert.match(source, /onSelect=\{adicionar\}/);
  assert.doesNotMatch(source, /onSubmit=\{buscarPessoas\}/);
});

test("oferece cadastro rápido e adiciona a pessoa criada ao grupo", () => {
  assert.match(source, /<ModalCadastroCliente/);
  assert.match(source, /onClienteCriado=\{adicionarPessoaCriada\}/);
  assert.match(source, /setMostrarCadastroPessoa\(true\)/);
  assert.match(source, />\s*Novo\s*<\/ActionButton>/);
});
