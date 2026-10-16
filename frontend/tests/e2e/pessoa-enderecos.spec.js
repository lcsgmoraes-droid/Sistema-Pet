import { expect, test } from "@playwright/test";
import { URL } from "node:url";
import { credenciaisDoAmbiente, fecharTour, login } from "./helpers.js";

const env = credenciaisDoAmbiente();
const ambienteLocal = env && ["localhost", "127.0.0.1"].includes(new URL(env.baseURL).hostname);

test.use({ channel: "chrome" });

test.describe("Pessoa — persistência dos endereços adicionais", () => {
  test.skip(!ambienteLocal, "requer credenciais E2E de uma cópia local do banco");

  test("salva endereço extra no cadastro e permite remover o último na edição", async ({
    page,
  }) => {
    await login(page, env);
    await page.goto("/clientes", { waitUntil: "networkidle" });
    await fecharTour(page);
    await page.getByRole("button", { name: /^novo cadastro$/i }).click();

    const nome = `QA-CAD-20261016 Endereco ${Date.now()}`;
    const apelido = "QA Entrega de cadastro novo";
    // Consulta de CEP determinística: nenhum serviço externo participa deste teste.
    await page.route("https://viacep.com.br/ws/01001000/json/", (route) =>
      route.fulfill({
        json: {
          logradouro: "Rua Sintética QA",
          bairro: "Bairro QA",
          localidade: "Cidade QA",
          uf: "SP",
          ibge: "3550308",
        },
      }),
    );
    await page.locator("#pessoa-nome").fill(nome);
    await page.locator('label[for="pessoa-tipos-cadastro-fornecedor"]').click();
    await page.getByRole("tab", { name: "Endereço", exact: true }).click();
    await page.getByRole("button", { name: "Adicionar endereço", exact: true }).click();
    await page.locator("#endereco-apelido").fill(apelido);
    await page.locator("#endereco-cep").fill("01001000");
    await page.locator("#endereco-logradouro").fill("Rua Sintética QA");
    await page.locator("#endereco-numero").fill("42");
    await page.locator("#endereco-bairro").fill("Bairro QA");
    await page.locator("#endereco-cidade").fill("Cidade QA");
    await page.locator("#endereco-estado").fill("SP");
    await page.getByRole("button", { name: "Salvar endereço", exact: true }).click();
    await expect(page.getByText(apelido, { exact: true })).toBeVisible();

    const criacaoPromise = page.waitForResponse(
      (response) =>
        new URL(response.url()).pathname === "/api/clientes/" &&
        response.request().method() === "POST",
    );
    await page.getByRole("button", { name: "Criar cadastro", exact: true }).click();
    const criacao = await criacaoPromise;
    expect(criacao.status()).toBe(201);
    const pessoa = await criacao.json();
    test
      .info()
      .annotations.push({ type: "pessoa_sintetica_local", description: String(pessoa.id) });
    expect(pessoa.enderecos_adicionais).toEqual([
      expect.objectContaining({ apelido, endereco: "Rua Sintética QA", numero: "42" }),
    ]);

    // Recarregar força um novo GET: não basta o card continuar no estado do formulário.
    await expect(page).toHaveURL(new RegExp(`/clientes/${pessoa.id}/editar$`));
    await page.reload({ waitUntil: "networkidle" });
    await page.getByRole("tab", { name: "Endereço", exact: true }).click();
    const card = page
      .locator("div.rounded-lg.border")
      .filter({ has: page.getByText(apelido, { exact: true }) })
      .last();
    await expect(page.getByText(apelido, { exact: true })).toBeVisible();
    await card.getByRole("button", { name: /excluir/i }).click();
    await page.getByRole("button", { name: "Confirmar", exact: true }).click();
    // O fluxo atual também pede a confirmação específica da remoção do endereço.
    const confirmacaoEndereco = page.getByRole("button", { name: "Confirmar", exact: true });
    if (await confirmacaoEndereco.isVisible()) await confirmacaoEndereco.click();

    const edicaoPromise = page.waitForResponse(
      (response) =>
        new URL(response.url()).pathname === `/api/clientes/${pessoa.id}` &&
        response.request().method() === "PUT",
    );
    await page.getByRole("button", { name: "Salvar", exact: true }).click();
    expect((await edicaoPromise).status()).toBe(200);
    await page.reload({ waitUntil: "networkidle" });
    await page.getByRole("tab", { name: "Endereço", exact: true }).click();
    await expect(page.getByText(apelido, { exact: true })).toHaveCount(0);
  });
});
