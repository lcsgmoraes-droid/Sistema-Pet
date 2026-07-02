import assert from "node:assert/strict";

import { shouldShowDevModuleControls } from "../src/contexts/modulosDevControls.js";

assert.equal(
  shouldShowDevModuleControls({ DEV: true }),
  true,
  "vite dev deve mostrar controles DEV por padrao",
);

assert.equal(
  shouldShowDevModuleControls({ DEV: false }),
  false,
  "build/preview nao deve mostrar controles DEV",
);

assert.equal(
  shouldShowDevModuleControls({ DEV: true, VITE_HIDE_DEV_CONTROLS: "true" }),
  false,
  "VITE_HIDE_DEV_CONTROLS=true deve esconder controles mesmo no vite dev",
);

assert.equal(
  shouldShowDevModuleControls({ DEV: true, VITE_HIDE_DEV_CONTROLS: "1" }),
  false,
  "VITE_HIDE_DEV_CONTROLS=1 deve esconder controles mesmo no vite dev",
);

console.log("Dev controls visibility contract OK");
