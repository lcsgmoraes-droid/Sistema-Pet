import { expect, test } from "@playwright/test";
import { credenciaisDoAmbiente, fecharTour, login } from "./helpers.js";

const env = credenciaisDoAmbiente();
const local = env && ["localhost", "127.0.0.1"].includes(new URL(env.baseURL).hostname);
let pessoa;
let produto;

test.describe("Melhorias operacionais em DEV", () => {
  test.skip(!local, "Requer identidade E2E e servidor DEV local; produção não é permitida.");
  test.setTimeout(90_000);
  test.beforeAll(async ({ request }) => {
    const loginRes = await request.post(`${env.baseURL}/api/auth/login-multitenant`, {
      data: { email: env.email, password: env.password },
    });
    expect(loginRes.ok()).toBeTruthy();
    const sessao = await loginRes.json();
    const tenantId = process.env.E2E_TENANT_ID || sessao.tenants[0].id;
    const tenantRes = await request.post(`${env.baseURL}/api/auth/select-tenant`, {
      headers: { Authorization: `Bearer ${sessao.access_token}` },
      data: { tenant_id: tenantId },
    });
    if (!tenantRes.ok())
      throw new Error(`Seleção do tenant DEV: ${tenantRes.status()} ${await tenantRes.text()}`);
    const headers = { Authorization: `Bearer ${(await tenantRes.json()).access_token}` };
    const sufixo = Date.now().toString().slice(-7);
    const pessoaRes = await request.post(`${env.baseURL}/api/clientes/`, {
      headers,
      data: {
        nome: `Pessoa QA Operacional ${sufixo}`,
        tipo_pessoa: "PF",
        is_cliente: true,
        celular: `1197${sufixo}`,
        ativo: true,
      },
    });
    expect(pessoaRes.ok()).toBeTruthy();
    pessoa = await pessoaRes.json();
    const produtoRes = await request.post(`${env.baseURL}/api/produtos/`, {
      headers,
      data: {
        codigo: `QA-OPER-${sufixo}`,
        nome: `Produto QA Operacional ${sufixo}`,
        preco_venda: 12,
        preco_custo: 4,
        tipo_produto: "SIMPLES",
        ativo: true,
        controlar_estoque: false,
      },
    });
    expect(produtoRes.ok()).toBeTruthy();
    produto = await produtoRes.json();
  });

  test("editar pessoa no PDV mantém produto, valor e cliente selecionado", async ({
    page,
  }, testInfo) => {
    await page.addInitScript(() => localStorage.setItem("tour_visto_pdv", "1"));
    await login(page, env);
    await page.goto("/pdv");
    await fecharTour(page);
    await page
      .getByPlaceholder("Digite nome, CPF ou telefone do cliente...", { exact: true })
      .fill(pessoa.codigo);
    await page.getByRole("option").filter({ hasText: pessoa.nome }).click();
    await page
      .getByPlaceholder("Digite o nome do produto, codigo de barras ou servico...", { exact: true })
      .fill(produto.nome);
    await page.getByRole("option").filter({ hasText: produto.nome }).getByRole("button").click();
    await expect(page.getByText(produto.nome, { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Editar cliente selecionado", exact: true }).click();
    const modal = page.getByRole("dialog", { name: "Editar pessoa", exact: true });
    await expect(modal).toBeVisible();
    const novoNome = `${pessoa.nome} Editada`;
    await modal.getByLabel("Nome completo", { exact: false }).fill(novoNome);
    await modal.getByRole("button", { name: "Salvar", exact: true }).click();
    await expect(modal).not.toBeVisible();
    await expect(page.getByText(novoNome, { exact: true })).toBeVisible();
    await expect(page.getByText(produto.nome, { exact: true })).toBeVisible();
    await expect(page.getByText("R$ 12,00", { exact: true }).first()).toBeVisible();
    await page.screenshot({
      path: testInfo.outputPath("melhorias-pdv-edicao.png"),
      fullPage: true,
    });
  });

  test("gestor de campanhas usa busca compartilhada e seleciona código público", async ({
    page,
  }) => {
    await login(page, env);
    await page.goto("/campanhas");
    await fecharTour(page);
    await page.getByRole("tab", { name: "Gestor", exact: true }).click();
    await page
      .getByPlaceholder("Codigo, nome, CPF ou telefone...", { exact: true })
      .fill(pessoa.codigo);
    const opcoes = page.getByRole("option");
    await expect(opcoes.first()).toContainText(pessoa.codigo);
    await opcoes.first().click();
    await expect(page.getByText(/^Pessoa QA Operacional \d+( Editada)?$/).first()).toBeVisible();
  });
});
