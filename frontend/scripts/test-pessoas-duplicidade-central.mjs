import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const raiz = resolve(import.meta.dirname, "..");
const ler = (arquivo) => readFileSync(resolve(raiz, arquivo), "utf8");

const pagina = ler("src/pages/ClientesNovo.jsx");
const banner = ler("src/components/pessoas/PessoasDuplicidadeBanner.jsx");
const central = ler("src/components/pessoas/PessoasDuplicidadeCentralModal.jsx");
const fusao = ler("src/components/pessoas/PessoasFusaoModal.jsx");
const apiClientes = ler("src/api/clientes.js");

assert.match(pagina, /PessoasDuplicidadeCentralModal/);
assert.match(pagina, /skip:\s*proximoSkip/);
assert.match(pagina, /revisarSugestoesSelecionadas/);
assert.match(pagina, /filaRevisaoFusao/);
assert.match(pagina, /executarFusoesAssistidasNome/);
assert.match(pagina, /confirmar:\s*false/);
assert.match(pagina, /confirmar:\s*true/);
assert.match(banner, /Revisar duplicidades/);
assert.match(banner, /onAbrirCentral/);
assert.doesNotMatch(banner, /onRevisarSugestao/);
assert.match(central, /Central de revisão de duplicidades/);
assert.match(central, /Selecionar página/);
assert.match(central, /Revisar selecionados/);
assert.match(central, /onMudarPagina/);
assert.match(central, /Fundir com evidência segura/);
assert.match(apiClientes, /fundir-assistidas-nome/);
assert.match(fusao, /await onSuccess/);
assert.match(fusao, /deveFechar/);

console.log("Contrato da central de duplicidades validado.");
