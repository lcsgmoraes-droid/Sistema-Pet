import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const source = readFileSync(
  new URL("../src/pages/configuracoes/OpenAIIntegracaoCard.jsx", import.meta.url),
  "utf8",
);

assert.match(
  source,
  /Boolean\(data\.has_openai_api_key\)/,
  "a tela deve usar apenas o indicador seguro de chave configurada",
);
assert.doesNotMatch(
  source,
  /Boolean\(data\.openai_api_key\)/,
  "a tela nao deve depender do valor real da chave retornado pela API",
);

console.log("OpenAI config security contract OK");
