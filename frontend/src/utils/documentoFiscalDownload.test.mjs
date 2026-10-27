import assert from "node:assert/strict";
import test from "node:test";

import { mensagemDocumento, metadadosDownloadDanfe } from "./documentoFiscalDownload.mjs";

test("salva o DANFE termico da NFC-e como HTML", () => {
  assert.deepEqual(
    metadadosDownloadDanfe({ headers: { "content-type": "text/html; charset=utf-8" } }, 529),
    { nome: "danfe_529.html", tipo: "text/html;charset=utf-8" },
  );
});

test("mantem o DANFE da NF-e como PDF", () => {
  assert.deepEqual(metadadosDownloadDanfe({ headers: { get: () => "application/pdf" } }, 1630), {
    nome: "danfe_1630.pdf",
    tipo: "application/pdf",
  });
});

test("exibe o motivo estruturado da IntNFe no erro de download XML", async () => {
  const mensagem = "O XML recebido do emissor não passou na verificação de integridade.";
  const error = {
    response: { data: new Blob([JSON.stringify({ detail: { mensagem, erro: "XmlInvalido" } })]) },
  };

  assert.equal(await mensagemDocumento(error, "Erro ao baixar XML"), mensagem);
});

test("preserva o detail textual retornado no download", async () => {
  assert.equal(
    await mensagemDocumento({ response: { data: { detail: "Arquivo indisponível." } } }, "Erro"),
    "Arquivo indisponível.",
  );
});

test("mostra mensagem pública e referência do erro de produção", async () => {
  const mensagem = "Erro interno no servidor. Nossa equipe foi notificada.";
  const referencia = "00dace7e-b170-46b3-9f29-269002419bdf";
  const error = {
    response: { data: new Blob([JSON.stringify({ message: mensagem, request_id: referencia })]) },
  };

  assert.equal(
    await mensagemDocumento(error, "Erro ao baixar XML"),
    `${mensagem}\nReferência para suporte: ${referencia}`,
  );
});

test("mensagem indisponível mantém o fallback sem expor objetos ou conteúdo bruto", async () => {
  for (const data of [
    null,
    { detail: { erro: "codigo_interno" }, message: { segredo: "não mostrar" } },
    { detail: " ", message: 502 },
    new Blob(["<html>Detalhe interno</html>"]),
    new Blob(["null"]),
  ]) {
    assert.equal(
      await mensagemDocumento({ response: { data } }, "Erro ao baixar XML"),
      "Erro ao baixar XML",
    );
  }
  assert.equal(await mensagemDocumento(null, "Erro ao baixar XML"), "Erro ao baixar XML");
});

test("ignora referências inválidas sem interferir na mensagem", async () => {
  for (const request_id of [{ valor: "interno" }, "id\nsegredo", "x".repeat(101)]) {
    assert.equal(
      await mensagemDocumento(
        { response: { data: { detail: "Arquivo indisponível.", request_id } } },
        "Erro",
      ),
      "Arquivo indisponível.",
    );
  }
});
