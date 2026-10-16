import { expect, test } from "@playwright/test";
import {
  abrirCaixaSeNecessario,
  ajustarEstoque,
  buscarEAdicionarProdutoPDV,
  credenciaisDoAmbiente,
  criarPessoaTeste,
  criarProdutoTeste,
  fecharTour,
  login,
  vincularClientePDV,
} from "./helpers.js";

const env = credenciaisDoAmbiente();

test.describe("PDV", () => {
  test.skip(!env, "requer E2E_BASE_URL, E2E_USER_EMAIL e E2E_USER_PASSWORD - ver tests/e2e/README.md");
  test.setTimeout(90_000);

  test("fluxo completo: produto com estoque + cliente + venda salva", async ({ page }) => {
    await login(page, env);

    const { nome: nomeCliente } = await criarPessoaTeste(page);
    const { sku } = await criarProdutoTeste(page);
    await ajustarEstoque(page, sku);

    await page.goto("/pdv", { waitUntil: "networkidle" });
    await fecharTour(page);

    await abrirCaixaSeNecessario(page);
    await buscarEAdicionarProdutoPDV(page, sku);
    await vincularClientePDV(page, nomeCliente);

    await page.getByRole("button", { name: /^salvar venda$/i }).first().click();

    await expect(page.getByText(/venda salva/i)).toBeVisible({ timeout: 10_000 });
  });
});
