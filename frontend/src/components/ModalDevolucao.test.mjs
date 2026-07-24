import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const modalSource = readFileSync(new URL("./ModalDevolucao.jsx", import.meta.url), "utf8");
const sectionsSource = readFileSync(
  new URL("./devolucao/ModalDevolucaoSections.jsx", import.meta.url),
  "utf8",
);

test("devolução a crédito exige cliente antes de enviar a requisição", () => {
  assert.match(modalSource, /Não é possível gerar crédito para uma venda sem cliente cadastrado/);
  assert.match(sectionsSource, /gerarCredito &&/);
  assert.match(sectionsSource, /!vendaSelecionada\?\.cliente_id/);
});
