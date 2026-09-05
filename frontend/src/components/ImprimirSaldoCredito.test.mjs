import assert from "node:assert/strict";
import { test } from "node:test";

import { imprimirSaldoCredito, montarTextoSaldoCredito } from "../utils/saldoCreditoPrint.js";

function prepararImpressao(t) {
  const documentoAnterior = Object.getOwnPropertyDescriptor(globalThis, "document");
  const printAnterior = Object.getOwnPropertyDescriptor(globalThis, "print");
  const texto = { textContent: "" };
  const janela = new EventTarget();
  janela.focus = t.mock.fn();
  janela.print = t.mock.fn();
  const frame = {
    contentDocument: { querySelector: () => texto },
    contentWindow: janela,
    setAttribute: t.mock.fn(),
    style: {},
    remove: t.mock.fn(),
  };
  const anexar = t.mock.fn();
  globalThis.document = {
    createElement: () => frame,
    body: { appendChild: anexar },
  };
  globalThis.print = t.mock.fn();
  t.after(() => {
    if (documentoAnterior) Object.defineProperty(globalThis, "document", documentoAnterior);
    else delete globalThis.document;
    if (printAnterior) Object.defineProperty(globalThis, "print", printAnterior);
    else delete globalThis.print;
  });
  return { anexar, frame, janela, texto };
}

test("montarTextoSaldoCredito identifica cliente, saldo e momento da consulta", () => {
  const texto = montarTextoSaldoCredito(
    { id: 12, codigo: "CLI-12", nome: "João da Silva" },
    17555.25,
    new Date("2026-09-04T12:30:00Z"),
  );

  assert.match(texto, /COMPROVANTE DE CREDITO/);
  assert.match(texto, /Cliente: Joao da Silva/);
  assert.match(texto, /Codigo: CLI-12/);
  assert.match(texto, /R\$ 17\.555,25/);
});

test("saldo imprime somente seu documento e aguarda o carregamento antes de imprimir", (t) => {
  const { anexar, frame, janela, texto } = prepararImpressao(t);

  imprimirSaldoCredito({ nome: "Cliente de teste", codigo: "CLI-12" }, 0.3);

  assert.equal(anexar.mock.callCount(), 1);
  assert.equal(janela.print.mock.callCount(), 0);
  frame.onload();
  assert.equal(janela.print.mock.callCount(), 1);
  assert.equal(globalThis.print.mock.callCount(), 0, "nao imprime a pagina do PDV");
  assert.match(texto.textContent, /SALDO DISPONIVEL/);
  assert.match(texto.textContent, /Cliente: Cliente de teste/);
  assert.match(texto.textContent, /R\$ 0,30/);
  assert.doesNotMatch(texto.textContent, /RECIBO DO PDV/);

  assert.equal(
    frame.remove.mock.callCount(),
    0,
    "mantem o documento enquanto a impressao esta aberta",
  );
  janela.dispatchEvent(new Event("afterprint"));
  assert.equal(frame.remove.mock.callCount(), 1, "remove ao imprimir ou cancelar");
  janela.dispatchEvent(new Event("afterprint"));
  assert.equal(frame.remove.mock.callCount(), 1);
});

test("dados do cliente sao inseridos como texto, sem virar HTML no comprovante", (t) => {
  const { frame, texto } = prepararImpressao(t);
  const nome = "<img src=x onerror=alert(1)>";

  imprimirSaldoCredito({ nome }, 10);
  frame.onload();

  assert.ok(texto.textContent.includes(nome));
  assert.ok(!frame.srcdoc.includes(nome));
});

test("falha ao abrir a impressao remove o documento temporario", (t) => {
  const { frame, janela } = prepararImpressao(t);
  janela.print = () => {
    throw new Error("Impressao indisponivel");
  };

  imprimirSaldoCredito({ nome: "Cliente de teste" }, 10);

  assert.throws(() => frame.onload(), /Impressao indisponivel/);
  assert.equal(frame.remove.mock.callCount(), 1);
  assert.equal(globalThis.print.mock.callCount(), 0);
});
