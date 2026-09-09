import { test } from "node:test";
import assert from "node:assert/strict";
import { telefoneWhatsApp, linkWhatsAppNota } from "./compartilharNota.js";

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
