import { defineConfig } from "@playwright/test";

// Suite de regressao de ponta a ponta (navegador real) para os fluxos
// criticos do CorePet: login, Pessoas, Produtos e PDV.
//
// Nao roda contra um banco fixo nem credenciais fixas: aponta pra qualquer
// stack (dev, ensaio, etc.) via variaveis de ambiente. Sem E2E_BASE_URL,
// E2E_USER_EMAIL e E2E_USER_PASSWORD definidas, os testes sao pulados (nao
// falham) - ver tests/e2e/README.md.
export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 45_000,
  expect: { timeout: 8_000 },
  fullyParallel: false,
  // Os specs compartilham a mesma conta de teste (mesmo login); rodar em
  // paralelo derruba a sessao de uns com o login dos outros.
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: process.env.E2E_BASE_URL || "http://localhost:5173",
    headless: process.env.E2E_HEADED !== "1",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    viewport: { width: 1440, height: 900 },
  },
});
