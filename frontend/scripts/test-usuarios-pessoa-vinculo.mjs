import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const raiz = resolve(import.meta.dirname, "..");

function ler(path) {
  return readFileSync(resolve(raiz, path), "utf8");
}

const hook = ler("src/hooks/useUsuariosPage.js");
const pagina = ler("src/pages/UsuariosPage.jsx");
const tabela = ler("src/components/usuarios/UsuariosTable.jsx");

assert.match(hook, /function isClienteRole/);
assert.match(hook, /rolesUsuariosDiretos = roles\.filter\(\(role\) => !isClienteRole\(role\)\)/);
assert.match(pagina, /roles=\{rolesUsuariosDiretos\}/);

assert.match(tabela, /header: "Pessoa vinculada"/);
assert.match(tabela, /usuario\.pessoa_id/);
assert.match(tabela, /usuario\.pessoa_nome/);
assert.match(tabela, /Sem pessoa/);

console.log("Contrato da listagem de usuarios com pessoa vinculada validado.");
