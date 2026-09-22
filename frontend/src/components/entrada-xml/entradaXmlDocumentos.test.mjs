import assert from "node:assert/strict";
import test from "node:test";

import { nomeDocumentoDaResposta, nomeDocumentoEntrada } from "./entradaXmlDocumentos.mjs";

test("monta nomes seguros para os documentos da NF-e de entrada", () => {
  const nota = { numero_nota: "901.597", serie: "2" };
  assert.equal(nomeDocumentoEntrada(nota, "pdf"), "danfe_901597_serie_2.pdf");
  assert.equal(nomeDocumentoEntrada(nota, "xml"), "nfe_901597_serie_2.xml");
});

test("prioriza o nome enviado pelo backend", () => {
  const response = {
    headers: { "content-disposition": 'attachment; filename="danfe_901597_serie_2.pdf"' },
  };
  assert.equal(nomeDocumentoDaResposta(response, "danfe_fallback.pdf"), "danfe_901597_serie_2.pdf");
});
