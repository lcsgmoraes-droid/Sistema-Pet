import { expect, test } from "@playwright/test";
import { credenciaisDoAmbiente, login } from "./helpers.js";

const env = credenciaisDoAmbiente();

test.describe("Login", () => {
  test.skip(!env, "requer E2E_BASE_URL, E2E_USER_EMAIL e E2E_USER_PASSWORD - ver tests/e2e/README.md");

  test("entra com usuario valido e chega numa tela autenticada", async ({ page }) => {
    await login(page, env);
    await expect(page).not.toHaveURL(/\/login$/);
  });
});
