import { test } from "node:test";
import assert from "node:assert/strict";
import {
  telefoneWhatsApp,
  linkWhatsAppNota,
  rotaCompartilhamentoNota,
} from "./compartilharNota.js";

test("formata telefone e preserva o link da nota na mensagem", () => {
  assert.equal(telefoneWhatsApp("(18) 99775-4060"), "5518997754060");
  assert.equal(telefoneWhatsApp("+55 18 99775-4060"), "5518997754060");
  assert.equal(telefoneWhatsApp("123"), "");
  const dados = { numero: 43, link: "https://www.bling.com.br/doc?x=1&accessKey=abc" };
  const link = new URL(linkWhatsAppNota(dados, "18997754060"));
  assert.equal(link.pathname, "/5518997754060");
  assert.ok(link.searchParams.get("text").includes(dados.link));
  assert.equal(linkWhatsAppNota(dados, ""), "");
});

test("usa a rota da venda para nota emitida pela IntNFe", () => {
  assert.equal(
    rotaCompartilhamentoNota({ id: "local-50", venda_id: 1476, provedor: "intnfe" }),
    "/nfe/vendas/1476/compartilhar",
  );
  assert.equal(
    rotaCompartilhamentoNota({ id: 123, venda_id: 1476, provedor: "bling" }),
    "/nfe/123/compartilhar",
  );
});
