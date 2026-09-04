import assert from "node:assert/strict";
import { test } from "node:test";

import { filtrarCuponsValidosPdv } from "./pdvCuponsAtivos.js";

test("filtrarCuponsValidosPdv oculta cupom expirado mesmo com status ativo", () => {
  const agora = new Date("2026-09-04T12:00:00Z");
  const resultado = filtrarCuponsValidosPdv(
    [
      { code: "VENCIDO", status: "active", valid_until: "2026-09-04T11:59:59Z" },
      { code: "NO-LIMITE", status: "active", valid_until: "2026-09-04T12:00:00Z" },
      { code: "VALIDO", status: "active", valid_until: "2026-09-04T12:00:01Z" },
      { code: "SEM-PRAZO", status: "active", valid_until: null },
      { code: "USADO", status: "used", valid_until: null },
    ],
    agora,
  );

  assert.deepEqual(
    resultado.map((cupom) => cupom.code),
    ["NO-LIMITE", "VALIDO", "SEM-PRAZO"],
  );
});

test("filtrarCuponsValidosPdv rejeita validade invalida por seguranca", () => {
  assert.deepEqual(
    filtrarCuponsValidosPdv([{ code: "DATA-RUIM", status: "active", valid_until: "invalida" }]),
    [],
  );
});
