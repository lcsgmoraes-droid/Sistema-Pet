import assert from "node:assert/strict";
import test from "node:test";

import {
  formatarDataIsoParaBr,
  mascararDataBr,
  parseDataBrParaIso,
} from "./agendaDateInputUtils.js";

test("formatarDataIsoParaBr exibe data ISO no padrao brasileiro", () => {
  assert.equal(formatarDataIsoParaBr("2026-05-19"), "19/05/2026");
});

test("parseDataBrParaIso converte dd/mm/aaaa para ISO", () => {
  assert.equal(parseDataBrParaIso("19/05/2026"), "2026-05-19");
});

test("parseDataBrParaIso rejeita formato invertido e datas invalidas", () => {
  assert.equal(parseDataBrParaIso("05/19/2026"), "");
  assert.equal(parseDataBrParaIso("31/02/2026"), "");
  assert.equal(parseDataBrParaIso("1/5/2026"), "");
});

test("mascararDataBr aplica barras enquanto o usuario digita", () => {
  assert.equal(mascararDataBr("19052026"), "19/05/2026");
  assert.equal(mascararDataBr("19a05b2026"), "19/05/2026");
  assert.equal(mascararDataBr("1905"), "19/05");
});
