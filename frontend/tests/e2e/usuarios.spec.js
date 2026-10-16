import { expect, test } from "@playwright/test";
import { URL } from "node:url";
import { credenciaisDoAmbiente, login } from "./helpers.js";

const env = credenciaisDoAmbiente();
const ambienteLocal =
  env && ["localhost", "127.0.0.1", "[::1]"].includes(new URL(env.baseURL).hostname);

test.use({ channel: "chrome" });

test.describe("Usuários: vínculo e edição no modal", () => {
  test.skip(!ambienteLocal, "requer credenciais de uma stack local de teste");

  test("preserva edição após vínculo e limpa o vínculo ao reabrir", async ({ page }, testInfo) => {
    await login(page, env);
    await page.goto("/admin/usuarios");
    await expect(page.getByRole("heading", { name: "Usuarios", exact: true })).toBeVisible();

    await page.route("**/api/clientes/verificar-duplicata/campo?**", async (route) => {
      await route.fulfill({
        json: { duplicado: true, cliente: { id: 99999999, nome: "Pessoa vinculada QA" } },
      });
    });

    const nome = page.locator("#novo-usuario-nome");
    const email = page.locator("#novo-usuario-email");
    const vincular = page.getByRole("button", { name: "Vincular a esta pessoa", exact: true });
    await page.getByRole("button", { name: "Novo usuario", exact: true }).click();
    await email.fill("qa.usuario.modal@example.com");
    await nome.click();
    await vincular.click();
    await expect(nome).toHaveValue("Pessoa vinculada QA");
    await expect(page.getByText("Vinculado a: Pessoa vinculada QA", { exact: true })).toBeVisible();

    await nome.fill("Pessoa editada QA");
    await expect(nome).toHaveValue("Pessoa editada QA");
    await expect(page.getByText("Vinculado a: Pessoa vinculada QA", { exact: true })).toHaveCount(
      0,
    );
    await expect(page.getByRole("radio", { name: "Pessoa Física", exact: true })).toBeVisible();

    await email.fill("qa.usuario.modal.outro@example.com");
    await nome.click();
    await vincular.click();
    await page.getByRole("button", { name: "Cancelar", exact: true }).click();
    await page.getByRole("button", { name: "Novo usuario", exact: true }).click();
    await expect(nome).toHaveValue("");
    await expect(email).toHaveValue("");
    await expect(page.getByText("Vinculado a: Pessoa vinculada QA", { exact: true })).toHaveCount(
      0,
    );
    await expect(page.getByRole("radio", { name: "Pessoa Física", exact: true })).toBeVisible();
    await expect(page.getByText("Informe o nome da pessoa.", { exact: true })).toHaveCount(0);
    await page.screenshot({ path: testInfo.outputPath("usuario-modal-reaberto.png") });
    await page.getByRole("button", { name: "Cancelar", exact: true }).click();
  });
});
