import { expect, test } from "@playwright/test";
import { URL } from "node:url";
import { credenciaisDoAmbiente, fecharTour, login } from "./helpers.js";

const env = credenciaisDoAmbiente();
const ambienteLocal = env && ["localhost", "127.0.0.1"].includes(new URL(env.baseURL).hostname);

test.use({ channel: "chrome" });

test.describe("Pessoa — persistência dos endereços adicionais", () => {
  test.skip(!ambienteLocal, "requer credenciais E2E de uma cópia local do banco");

  test("salva endereço com um clique e mantém os cards após salvar o cadastro", async ({
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
    const principalCard = page
      .locator("div.rounded-lg.border.p-3")
      .filter({ has: page.getByText("Principal", { exact: true }) });
    await principalCard.getByRole("button", { name: "Editar", exact: true }).click();
    await page.locator("#endereco-cep").fill("01001000");
    await page.locator("#endereco-numero").focus();
    await expect(page.locator("#endereco-cidade")).toHaveValue("Cidade QA");
    await page.locator("#endereco-numero").fill("73");
    const respostaPut = (response) =>
      new URL(response.url()).pathname === `/api/clientes/${pessoa.id}` &&
      response.request().method() === "PUT";
    const enderecoPromise = page.waitForResponse(respostaPut);
    await page.getByRole("button", { name: "Salvar endereço", exact: true }).click();
    const respostaEndereco = await enderecoPromise;
    expect(respostaEndereco.status()).toBe(200);
    const salvo = await respostaEndereco.json();
    expect(salvo).toMatchObject({
      id: pessoa.id,
      nome,
      is_fornecedor: true,
      endereco: "Rua Sintética QA",
      numero: "73",
      cidade: "Cidade QA",
      estado: "SP",
      codigo_municipio: "3550308",
      enderecos_adicionais: [expect.objectContaining({ apelido, numero: "42" })],
    });
    await expect(principalCard).toContainText("Rua Sintética QA, 73");
    await expect(page.getByText("Nenhum endereço cadastrado", { exact: true })).toHaveCount(0);

    // Confere persistência com GET independente, sem depender do estado do React.
    const confirmado = await page.request.get(`/api/clientes/${pessoa.id}`, {
      headers: { authorization: respostaEndereco.request().headers().authorization },
    });
    expect(confirmado.status()).toBe(200);
    expect(await confirmado.json()).toMatchObject({
      endereco: "Rua Sintética QA",
      numero: "73",
      codigo_municipio: "3550308",
    });
    for (let tentativa = 0; tentativa < 2; tentativa += 1) {
      const geralPromise = page.waitForResponse(respostaPut);
      await page.getByRole("button", { name: "Salvar", exact: true }).click();
      const geral = await geralPromise;
      expect(geral.status()).toBe(200);
      expect(await geral.json()).toMatchObject({
        endereco: "Rua Sintética QA",
        numero: "73",
        codigo_municipio: "3550308",
      });
      await expect(principalCard).toContainText("Rua Sintética QA, 73");
      await expect(card).toContainText("Rua Sintética QA, 42");
      await expect(page.getByText("Nenhum endereço cadastrado", { exact: true })).toHaveCount(0);
    }

    const edicaoPromise = page.waitForResponse(respostaPut);
    await card.getByRole("button", { name: /excluir/i }).click();
    await page.getByRole("button", { name: "Confirmar", exact: true }).click();
    const edicao = await edicaoPromise;
    expect(edicao.status()).toBe(200);
    expect((await edicao.json()).enderecos_adicionais).toEqual([]);
    // O clique da confirmação já persiste: não há um segundo Salvar geral.
    await page.reload({ waitUntil: "networkidle" });
    await page.getByRole("tab", { name: "Endereço", exact: true }).click();
    await expect(page.getByText(apelido, { exact: true })).toHaveCount(0);
    await expect(principalCard).toContainText("Rua Sintética QA, 73");
  });
});
