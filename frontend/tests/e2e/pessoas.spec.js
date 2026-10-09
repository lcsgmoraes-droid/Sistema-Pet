import { expect, test } from "@playwright/test";
import { credenciaisDoAmbiente, criarPessoaTeste, login } from "./helpers.js";

const env = credenciaisDoAmbiente();

test.describe("Pessoas", () => {
  test.skip(!env, "requer E2E_BASE_URL, E2E_USER_EMAIL e E2E_USER_PASSWORD - ver tests/e2e/README.md");

  test("cria uma pessoa com nome e celular", async ({ page }) => {
    await login(page, env);
    await criarPessoaTeste(page);

    await expect(page).toHaveURL(/\/clientes\/\d+\/editar/);
    const erroValidacao = page.getByText("Informe telefone ou celular");
    await expect(erroValidacao).not.toBeVisible();
  });
});
