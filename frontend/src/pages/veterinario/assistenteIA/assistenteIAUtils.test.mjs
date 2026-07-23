import assert from "node:assert/strict";
import test from "node:test";

import { getMemoriaAssistenteIABadge } from "./assistenteIAUtils.js";

test("memoria badge mostra aprendizados isolados do usuario", () => {
  const badge = getMemoriaAssistenteIABadge({
    ok: true,
    memorias_consideradas: 4,
  });

  assert.match(badge.label, /4 aprendizado/);
  assert.match(badge.className, /emerald/);
});
