import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("./EcommerceDivulgacao.jsx", import.meta.url), "utf8");

test("a tela de divulgação permite persistir o WhatsApp nos dados do tenant", () => {
  assert.match(source, /api\.put\("\/empresa\/dados-cadastrais"/);
  assert.match(source, /telefone:\s*valorInformado/);
  assert.match(source, /WhatsApp da loja salvo/);
  assert.match(source, /Clique em Salvar para manter este número ao voltar à tela/);
});
