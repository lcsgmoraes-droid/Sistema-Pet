import { expect, test } from "@playwright/test";
import { ajustarEstoque, credenciaisDoAmbiente, criarProdutoTeste, login } from "./helpers.js";

const env = credenciaisDoAmbiente();

test.describe("Produtos", () => {
  test.skip(!env, "requer E2E_BASE_URL, E2E_USER_EMAIL e E2E_USER_PASSWORD - ver tests/e2e/README.md");

  test("cria um produto e registra entrada de estoque", async ({ page }) => {
    await login(page, env);
    const { sku, nome } = await criarProdutoTeste(page);

    await page.goto("/produtos");
    await page.waitForLoadState("networkidle");
    const campoBusca = page.locator("input[placeholder*='uscar' i]").first();
    await campoBusca.fill(sku);
    await page.waitForLoadState("networkidle").catch(() => {});
    await page.waitForTimeout(800);
    // getByText(nome) tambem casa com um <h3> de card mobile que fica
    // escondido (CSS) neste viewport desktop; escopar pra linha da tabela
    // visivel evita o falso negativo de "hidden".
    const linhaProduto = page.locator("table tr").filter({ hasText: nome }).first();
    await expect(linhaProduto).toBeVisible({ timeout: 15_000 });

    await ajustarEstoque(page, sku);

    const modalAberto = page.getByText("Nova Entrada de Estoque");
    await expect(modalAberto).not.toBeVisible();
  });
});
