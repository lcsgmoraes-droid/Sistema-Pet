/* global process, URL, localStorage */
import { expect, test } from "@playwright/test";
import { randomUUID } from "node:crypto";
import { fecharTour } from "./helpers.js";

const baseURL = process.env.E2E_BASE_URL;
const autorizado =
  process.env.E2E_CREATE_TEST_IDENTITY === "1" &&
  baseURL &&
  ["localhost", "127.0.0.1"].includes(new URL(baseURL).hostname);
const marcador = `QA Busca ${randomUUID().slice(0, 8)}`;
let sessao;
let user;
let tutor;
let outroTutor;
let fornecedor;
let produto;
let kit;

test.describe("Buscas compartilhadas em outros módulos DEV", () => {
  test.skip(!autorizado, "Requer DEV local e autorização E2E_CREATE_TEST_IDENTITY=1.");
  test.setTimeout(90_000);
  test.use({ actionTimeout: 12_000 });

  async function api(request, metodo, caminho, data) {
    const resposta = await request[metodo](`${baseURL}/api${caminho}`, {
      headers: sessao?.access_token ? { Authorization: `Bearer ${sessao.access_token}` } : {},
      data,
    });
    expect(resposta.ok(), `${metodo.toUpperCase()} ${caminho}: ${resposta.status()}`).toBeTruthy();
    return resposta.json();
  }

  test.beforeAll(async ({ request }) => {
    // A identidade é exclusiva desta suíte: não invalida sessões de outros aceites.
    const sufixo = randomUUID().slice(0, 8);
    sessao = await api(request, "post", "/auth/register", {
      email: `qa-buscas-${sufixo}@example.com`,
      password: `Qa!${randomUUID()}9`,
      nome: "Operador QA Buscas",
      nome_loja: `DEV Buscas ${sufixo}`,
      nome_acesso: `qa-buscas-${sufixo}`,
      plan: "pet-venda-ativa",
      accepted_terms: true,
      accepted_privacy: true,
    });
    sessao = await api(request, "post", "/auth/select-tenant", {
      tenant_id: sessao.tenants[0].id,
    });
    user = await api(request, "get", "/auth/me-multitenant");
    tutor = await api(request, "post", "/clientes/", {
      nome: `${marcador} Tutor Acácia`,
      tipo_pessoa: "PF",
      is_cliente: true,
      telefone: "11955550001",
    });
    outroTutor = await api(request, "post", "/clientes/", {
      nome: `${marcador} Tutor Ipê`,
      tipo_pessoa: "PF",
      is_cliente: true,
      telefone: "11955550002",
    });
    fornecedor = await api(request, "post", "/clientes/", {
      nome: `${marcador} Fornecedor Cedro`,
      tipo_pessoa: "PF",
      is_cliente: false,
      is_fornecedor: true,
    });
    produto = await api(request, "post", "/produtos/", {
      nome: `${marcador} Ração Premium`,
      codigo: `QA-BUSCA-${sufixo}`,
      preco_venda: 20,
      preco_custo: 5,
      unidade: "UN",
      tipo_produto: "SIMPLES",
      ativo: true,
      anunciar_app: false,
      anunciar_ecommerce: false,
    });
    kit = await api(request, "post", "/produtos/", {
      nome: `${marcador} Kit`,
      codigo: `QA-KIT-${sufixo}`,
      preco_venda: 20,
      preco_custo: 5,
      unidade: "UN",
      tipo_produto: "KIT",
      tipo_kit: "VIRTUAL",
      e_kit_fisico: false,
      composicao_kit: [{ produto_componente_id: produto.id, quantidade: 1 }],
      ativo: true,
      anunciar_app: false,
      anunciar_ecommerce: false,
    });
  });

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(
      ({ sessao, user }) => {
        localStorage.setItem("access_token", sessao.access_token);
        localStorage.setItem("refresh_token", sessao.refresh_token);
        localStorage.setItem("user", JSON.stringify(user));
        localStorage.setItem("selectedTenant", JSON.stringify(user.tenant));
        for (const tela of ["pdv", "pessoas", "produtos", "pets"])
          localStorage.setItem(`tour_visto_${tela}`, "1");
      },
      { sessao, user },
    );
  });

  test("Pessoas encontra o código público e exibe o cadastro correto", async ({
    page,
  }, testInfo) => {
    await page.goto("/clientes");
    await fecharTour(page);
    const busca = page.getByRole("combobox").first();
    await busca.fill(tutor.codigo);
    const linha = page.getByRole("row").filter({ hasText: tutor.nome });
    await expect(linha).toBeVisible();
    await expect(linha).toContainText(tutor.codigo);
    await expect(page.getByRole("row").filter({ hasText: outroTutor.nome })).toHaveCount(0);
    await page.screenshot({
      path: testInfo.outputPath("pessoas-codigo-publico.png"),
      fullPage: true,
    });
  });

  test("Novo Pet seleciona tutor pelo código e mantém a nova digitação ao trocar", async ({
    page,
  }, testInfo) => {
    await page.goto("/pets/novo");
    await fecharTour(page);
    const busca = page.getByRole("combobox", { name: /Cliente \(Tutor\)/ });
    await busca.fill(tutor.codigo);
    const primeira = page.getByRole("option").first();
    await expect(primeira).toContainText(tutor.nome);
    await expect(primeira).toContainText(`#${tutor.codigo}`);
    await page.screenshot({
      path: testInfo.outputPath("pet-tutor-sugestao-codigo.png"),
      fullPage: true,
    });
    await busca.press("ArrowDown");
    await busca.press("Enter");
    await expect(busca).toHaveValue(tutor.nome);
    await expect(page.getByRole("listbox")).toHaveCount(0);
    await busca.fill(outroTutor.codigo);
    await expect(busca).toHaveValue(outroTutor.codigo);
    const segunda = page.getByRole("option").filter({ hasText: outroTutor.nome });
    await expect(segunda).toBeVisible();
    await segunda.click();
    await expect(busca).toHaveValue(outroTutor.nome);
    await page.screenshot({ path: testInfo.outputPath("pet-tutor-trocado.png"), fullPage: true });
  });

  test("Conta a pagar encontra fornecedor pelo código e permite selecionar", async ({
    page,
  }, testInfo) => {
    await page.goto("/financeiro/contas-pagar");
    await fecharTour(page);
    await page.getByRole("button", { name: "Nova Conta", exact: true }).click();
    const busca = page.getByPlaceholder("Digite o fornecedor...", { exact: true });
    await busca.fill(fornecedor.codigo);
    const opcao = page.getByRole("option").filter({ hasText: fornecedor.nome });
    await expect(opcao).toContainText(`#${fornecedor.codigo}`);
    await page.screenshot({
      path: testInfo.outputPath("conta-pagar-fornecedor-codigo.png"),
      fullPage: true,
    });
    await opcao.click();
    await expect(busca).toHaveValue(fornecedor.nome);
    await expect(page.getByRole("listbox")).toHaveCount(0);
  });

  test("Composição de kit encontra produto pelo código e seleciona sem salvar", async ({
    page,
  }, testInfo) => {
    await page.goto(`/produtos/${kit.id}/editar`);
    await fecharTour(page);
    await page.getByRole("button", { name: /Composição/ }).click();
    const busca = page.getByPlaceholder("Código, nome, SKU ou código de barras do componente");
    await busca.fill(produto.codigo);
    const opcao = page.getByRole("option").filter({ hasText: produto.nome });
    await expect(opcao).toContainText(produto.codigo);
    await busca.scrollIntoViewIfNeeded();
    await page.screenshot({ path: testInfo.outputPath("kit-produto-codigo.png"), fullPage: true });
    await opcao.click();
    await expect(busca).toHaveValue(`[${produto.codigo}] ${produto.nome}`);
    await expect(page.getByRole("listbox")).toHaveCount(0);
  });
});
