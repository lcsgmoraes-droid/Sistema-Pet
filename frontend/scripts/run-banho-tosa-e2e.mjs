import { spawnSync } from "node:child_process";
import { ambienteBanhoTosa } from "../tests/e2e/banho-tosa/ambiente.mjs";

const ambiente = ambienteBanhoTosa();
if (!ambiente)
  throw new Error(
    "Defina E2E_CREATE_TEST_IDENTITY=1 para criar dados sinteticos exclusivos no DEV local.",
  );
const resultado = spawnSync(
  process.execPath,
  [
    "node_modules/@playwright/test/cli.js",
    "test",
    "tests/e2e/banho-tosa-pacotes.spec.js",
    ...process.argv.slice(2),
  ],
  {
    stdio: "inherit",
    env: { ...process.env, E2E_BASE_URL: ambiente.baseURL, E2E_BT_API_URL: ambiente.apiURL },
  },
);
process.exit(resultado.status ?? 1);
