import assert from "node:assert/strict";
import test from "node:test";

import {
  montarLinksDivulgacao,
  nomeArquivoDivulgacao,
  normalizarTelefoneWhatsApp,
  telefoneWhatsAppValido,
} from "./divulgacaoLojaUtils.js";

test("monta links separados para acesso principal, ecommerce, app e WhatsApp", () => {
  assert.deepEqual(
    montarLinksDivulgacao({
      origin: "https://corepet.com.br/",
      slug: "Minha Loja!",
      telefone: "(18) 99999-0000",
      mensagem: "Olá, vim pelo QR Code",
    }),
    {
      smart: "https://corepet.com.br/app?loja=minhaloja",
      ecommerce: "https://corepet.com.br/minhaloja",
      app: "corepet://app?loja=minhaloja",
      whatsapp: "https://wa.me/5518999990000?text=Ol%C3%A1%2C%20vim%20pelo%20QR%20Code",
    },
  );
});

test("normaliza telefone nacional e preserva telefone com DDI", () => {
  assert.equal(normalizarTelefoneWhatsApp("18 99999-0000"), "5518999990000");
  assert.equal(normalizarTelefoneWhatsApp("+55 18 99999-0000"), "5518999990000");
  assert.equal(normalizarTelefoneWhatsApp(""), "");
});

test("valida o WhatsApp antes de salvar nos dados da empresa", () => {
  assert.equal(telefoneWhatsAppValido("18 99643-5503"), true);
  assert.equal(telefoneWhatsAppValido("+55 18 99643-5503"), true);
  assert.equal(telefoneWhatsAppValido("1899"), false);
  assert.equal(telefoneWhatsAppValido(""), false);
});

test("gera nome de arquivo seguro", () => {
  assert.equal(
    nomeArquivoDivulgacao("Pet & Cia Prudente", "a4", "pdf"),
    "divulgacao-pet-cia-prudente-a4.pdf",
  );
});
