import assert from "node:assert/strict";
import { test } from "node:test";
import { readFileSync } from "node:fs";
import {
  classificarResultadoOperacao,
  apresentacaoMovimentacao,
  enviarGeracaoUmaVez,
  fontesHttpsSeguras,
  identidadeCreditos,
  identidadeSessaoCreditos,
  modoCreditos,
  orcamentoExpirou,
  payloadImagemCredito,
  podeConfirmarOrcamento,
  rejeicaoAntesDaExecucao,
  validarOrcamento,
} from "./creditosModel.js";

const now = Date.parse("2026-09-09T13:00:00Z");
const quote = {
  operation_id: "quote-1",
  credits: 150,
  price_cents: 300,
  mode: "shadow",
  expires_at: "2026-09-09T13:05:00Z",
};

test("modos são explícitos; falha de catálogo nunca vira off", () => {
  for (const mode of ["off", "shadow", "enforced"]) assert.equal(modoCreditos({ mode }), mode);
  for (const value of [null, {}, { mode: "free" }]) assert.throws(() => modoCreditos(value));
});

test("orçamento valida valores inteiros e não aceita troca de modo", () => {
  assert.equal(validarOrcamento(quote, "shadow"), quote);
  for (const changed of [
    { credits: -1 },
    { credits: 1.5 },
    { price_cents: null },
    { mode: "enforced" },
    { expires_at: "?" },
    { operation_id: "" },
  ]) {
    assert.throws(() => validarOrcamento({ ...quote, ...changed }, "shadow"));
  }
});

test("shadow permite confirmar sem saldo, enforced exige saldo real", () => {
  assert.equal(podeConfirmarOrcamento(quote, null, now), true);
  const enforced = { ...quote, mode: "enforced" };
  assert.equal(podeConfirmarOrcamento(enforced, null, now), false);
  assert.equal(podeConfirmarOrcamento(enforced, { available_credits: 149 }, now), false);
  assert.equal(podeConfirmarOrcamento(enforced, { available_credits: 150 }, now), true);
  assert.equal(podeConfirmarOrcamento(quote, null, now + 300000), false);
  assert.equal(orcamentoExpirou(quote, now), false);
});

test("timeout, running e desconhecido nunca equivalem a falha segura para reenvio", () => {
  for (const status of ["quoted", "running", "uncertain", "unknown"]) {
    assert.equal(classificarResultadoOperacao({ status }), "pending");
  }
  assert.equal(classificarResultadoOperacao({ status: "completed" }), "pending");
  assert.equal(
    classificarResultadoOperacao({ status: "completed", result: { url: "/imagem.png" } }),
    "completed",
  );
  assert.equal(classificarResultadoOperacao({ status: "failed" }), "failed");
});

test("simulação de timeout recupera conclusão sem uma segunda geração paga", async () => {
  let sent = 0;
  let checked = 0;
  const response = await enviarGeracaoUmaVez(
    async (id) => {
      assert.equal(id, "quote-1");
      sent += 1;
      throw new Error("timeout");
    },
    "quote-1",
    async () => {
      checked += 1;
      return { url: "/resultado-ja-gerado.png" };
    },
  );
  assert.equal(sent, 1);
  assert.equal(checked, 1);
  assert.equal(response.recovered, true);
  assert.equal(response.result.url, "/resultado-ja-gerado.png");
});

test("resultado ainda incerto também não reenvia a geração", async () => {
  let sent = 0;
  await assert.rejects(
    enviarGeracaoUmaVez(
      async () => {
        sent += 1;
        throw new Error("conexao perdida");
      },
      "quote-1",
      async () => {
        throw new Error("pendente");
      },
    ),
    /pendente/,
  );
  assert.equal(sent, 1);
});

test("identificação do histórico local separa empresa e usuário", () => {
  assert.notEqual(
    identidadeCreditos({ id: "a" }, { id: 1 }),
    identidadeCreditos({ id: "b" }, { id: 1 }),
  );
  assert.notEqual(
    identidadeCreditos({ id: "a" }, { id: 1 }),
    identidadeCreditos({ id: "a" }, { id: 2 }),
  );
  assert.throws(() => identidadeCreditos(null, { id: 1 }));
});

test("sessão restaurada usa tenant de me-multitenant mesmo sem selectedTenant", () => {
  const user = { id: 1, tenant: { id: "a", name: "Loja A" } };
  assert.equal(identidadeCreditos(null, user), "a:1");
  assert.equal(identidadeSessaoCreditos(null, user, user), "a:1");
  assert.equal(identidadeCreditos(null, { id: 1, tenant_id: "a" }), "a:1");
  assert.throws(() => identidadeCreditos({ id: "b" }, user), /empresa mudou/);
});

test("troca entre abas não associa formulário antigo ao novo usuário ou empresa", () => {
  const original = { id: 1, tenant: { id: "a" } };
  const otherTenant = { id: 1, tenant: { id: "b" } };
  const otherUser = { id: 2, tenant: { id: "a" } };
  assert.throws(() => identidadeSessaoCreditos({ id: "b" }, otherTenant, original));
  assert.throws(() => identidadeSessaoCreditos(null, otherTenant, original), /outra aba/);
  assert.throws(() => identidadeSessaoCreditos({ id: "a" }, otherUser, original), /outra aba/);
  assert.throws(() => identidadeSessaoCreditos({ id: "a" }, original, null));
});

test("extrato não apresenta reserva e consumo como duas cobranças", () => {
  assert.equal(apresentacaoMovimentacao({ kind: "reserve" }).label, "Reserva");
  assert.match(apresentacaoMovimentacao({ kind: "capture" }).note, /não é uma segunda cobrança/);
  assert.equal(apresentacaoMovimentacao({ kind: "release" }).label, "Devolução da reserva");
  assert.match(
    apresentacaoMovimentacao({ mode: "shadow", kind: "capture" }).note,
    /saldo não alterado/,
  );
});

test("só rejeição definitiva antes da execução libera nova confirmação", () => {
  const rejected = { response: { status: 422, data: { detail: "imagem inválida" } } };
  assert.equal(rejeicaoAntesDaExecucao(rejected, { status: "quoted" }), true);
  assert.equal(rejeicaoAntesDaExecucao(rejected, { status: "running" }), false);
  assert.equal(rejeicaoAntesDaExecucao(rejected, { status: "uncertain" }), false);
  assert.equal(rejeicaoAntesDaExecucao({}, { status: "quoted" }), false);
  for (const status of [408, 429, 500, 502, 504])
    assert.equal(rejeicaoAntesDaExecucao({ response: { status } }, { status: "quoted" }), false);
  assert.equal(
    rejeicaoAntesDaExecucao(
      { response: { status: 409, data: { detail: { code: "credit_operation_pending" } } } },
      { status: "quoted" },
    ),
    false,
  );
});

test("fontes externas só aceitam HTTPS sem credenciais e removem duplicação", () => {
  assert.deepEqual(
    fontesHttpsSeguras([
      "https://fabricante.com/produto",
      "javascript:alert(1)",
      "http://inseguro.com",
      "https://user:secret@site.com",
      "https://fabricante.com/produto",
      "texto",
      null,
    ]),
    ["https://fabricante.com/produto"],
  );
});

test("imagem orçada reproduz tipos e defaults enviados na geração", () => {
  assert.deepEqual(payloadImagemCredito({ produto_id: "12", imagem_url: "/produto.png" }, {}), {
    produto_id: 12,
    estilo: "profissional",
    orientacao: "vertical",
    prompt_usuario: "",
    imagem_url: "/produto.png",
    file_sha256: null,
  });
  const image = payloadImagemCredito(
    {
      produto_id: 2,
      imagem_url: "/original.png",
      imagem_url_arte: "/escolhida.png",
      prompt_criacao: "  fundo branco  ",
    },
    { tema: "natural", formato: "quadrado" },
  );
  assert.equal(image.imagem_url, "/escolhida.png");
  assert.equal(image.prompt_usuario, "fundo branco");
  assert.equal(image.orientacao, "quadrada");
});

test("integrações não alteram cobrança dos downloads existentes", () => {
  const source = readFileSync(
    new URL("../../pages/ofertas/EstudioOfertas.jsx", import.meta.url),
    "utf8",
  );
  const downloads = source.slice(
    source.indexOf("async function baixarPng()"),
    source.indexOf("async function publicarLink()"),
  );
  assert.doesNotMatch(downloads, /creditosIA|credit_operation_id|orcarCreditos/);
  assert.match(source, /serviceCode: "oferta\.imagem"/);
});
