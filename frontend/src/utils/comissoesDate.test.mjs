import assert from "node:assert/strict";
import test from "node:test";

import { formatarDataHoraComissao } from "./comissoesDate.js";

test("formatarDataHoraComissao nao desloca data sem hora para o dia anterior", () => {
  assert.equal(formatarDataHoraComissao("2026-05-23"), "23/05/2026");
});

test("formatarDataHoraComissao preserva hora local de timestamp sem timezone", () => {
  assert.equal(formatarDataHoraComissao("2026-05-23T09:05:00"), "23/05/2026, 09:05");
});

test("formatarDataHoraComissao preserva hora local de timestamp vindo do backend", () => {
  assert.equal(formatarDataHoraComissao("2026-05-23 09:05:00"), "23/05/2026, 09:05");
});
