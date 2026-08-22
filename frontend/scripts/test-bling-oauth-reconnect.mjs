import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const source = readFileSync(
  new URL("../src/pages/configuracoes/BlingIntegracao.jsx", import.meta.url),
  "utf8",
);

assert.match(
  source,
  /api\.get\("\/auth\/bling\/link-autorizacao"\)/,
  "a tela de integracoes deve buscar o link OAuth pelo cliente autenticado",
);
assert.match(
  source,
  /status\.conectado \? "Renovar Token" : "Reconectar Bling"/,
  "a acao offline deve orientar a reconexao completa",
);
assert.match(
  source,
  /const statusAtual = await carregarStatus\(\)/,
  "o teste de conexao deve usar o resultado recem-carregado",
);
assert.doesNotMatch(
  source,
  /window\.location\.assign\("\/api\/auth\/bling\/link-autorizacao/,
  "a navegacao nao deve chamar diretamente uma rota protegida sem cabecalho de autenticacao",
);
assert.doesNotMatch(
  source,
  /Contacte o suporte com esse código|Copie o código gerado/,
  "a tela nao deve orientar um fluxo manual obsoleto",
);

console.log("Bling OAuth reconnect checks passed.");
