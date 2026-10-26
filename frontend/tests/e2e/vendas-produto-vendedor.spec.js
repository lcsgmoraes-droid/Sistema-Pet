import { readFile, stat } from "node:fs/promises";
import { expect, test } from "@playwright/test";

const baseUrl = process.env.E2E_BASE_URL;
const local = ["localhost", "127.0.0.1", "[::1]"].includes(
  new URL(baseUrl || "http://localhost:5173").hostname,
);

test.use({ channel: "chrome" });
test.skip(
  !baseUrl || !local,
  "requer E2E_BASE_URL explícita de um frontend local; usa somente API sintética",
);

const racao = (quantidade, vendaBruta) => ({
  produto_id: 101,
  produto_nome: "Ração QA",
  produto_codigo: "RACAO-QA",
  quantidade,
  preco_unitario: vendaBruta / quantidade,
  venda_bruta: vendaBruta,
});
const areia = (valor) => ({
  produto_id: 102,
  produto_nome: "Areia QA",
  produto_codigo: "AREIA-QA",
  quantidade: 1,
  preco_unitario: valor,
  venda_bruta: valor,
});
const venda = (id, vendedorId, vendedorNome, total, itens, status = "finalizada") => ({
  id,
  vendedor_funcionario_id: vendedorId,
  vendedor_nome: vendedorNome,
  numero_venda: `QA-${id}`,
  data_venda: "2026-10-20T12:00:00",
  cliente_nome: "Cliente sintético QA",
  total_venda: total,
  venda_bruta: itens.reduce((soma, item) => soma + item.venda_bruta, 0),
  itens: itens.map((item, indice) => ({ ...item, venda_item_id: id * 10 + indice })),
  status,
});
const vendas = [
  venda(1, 10, "Ana QA", 90, [racao(2, 60), areia(40)]),
  venda(2, 11, "Bruno QA", 140, [racao(0.125, 10), racao(1, 30), areia(100)]),
  venda(3, null, null, 30, [racao(1, 30)]),
  venda(4, 10, "Ana QA", 200, [areia(200)]),
  venda(5, 10, "Ana QA", 2970, [racao(99, 2970)], "cancelada"),
];

async function prepararApi(page) {
  const tenant = { id: "tenant-relatorio-qa", name: "Loja Sintética QA", login_name: "qa" };
  const user = {
    id: 42001,
    name: "Usuário QA",
    is_admin: true,
    role: { name: "admin" },
    permissions: ["relatorios.financeiro"],
    tenant,
  };
  await page.addInitScript(
    ({ user, tenant }) => {
      localStorage.setItem("access_token", "token-sintetico-sem-validade");
      localStorage.setItem("user", JSON.stringify(user));
      localStorage.setItem("selectedTenant", JSON.stringify(tenant));
    },
    { user, tenant },
  );
  // Intercepta inclusive chamadas desconhecidas: nenhum dado ou login real é usado.
  await page.route(
    (url) => url.pathname.startsWith("/api/"),
    async (route) => {
      const path = new URL(route.request().url()).pathname;
      const respostas = {
        "/api/auth/me-multitenant": user,
        "/api/auth/my-tenants": { tenants: [tenant] },
        "/api/modulos/status": { modulos_ativos: [], plano: "basico" },
        "/api/usuarios/me/menu-favoritos": { items: [] },
        "/api/lembretes/pendentes": { total: 0, lembretes: [] },
        "/api/empresa/config/visao-comercial": { visao_comercial: "venda" },
        "/api/relatorios/vendas/relatorio": { lista_vendas: vendas },
      };
      return route.fulfill({ json: respostas[path] || {} });
    },
  );
}

async function abrirRelatorio(page) {
  await prepararApi(page);
  await page.goto("/financeiro/vendas");
  await page.getByRole("tab", { name: "Por vendedor", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Vendas por vendedor", exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("combobox", { name: /^Produtos/ })).toBeVisible();
}

async function selecionarProduto(page) {
  await page.getByRole("combobox", { name: /^Produtos/ }).fill("Ração QA");
  await page.getByRole("option").filter({ hasText: "Ração QA" }).click();
}

test("produto por vendedor conta só seus itens e mantém os filtros independentes", async ({
  page,
}) => {
  await abrirRelatorio(page);
  await expect(page.getByText(/4 venda\(s\) · Total vendido: R\$\s*460,00/)).toBeVisible();
  await selecionarProduto(page);

  const resumo = page.getByRole("table", { name: "Resumo por vendedor · Ração QA (RACAO-QA)" });
  await expect(resumo).toBeVisible();
  await expect(resumo.getByRole("row")).toHaveCount(4);
  await expect(resumo.getByRole("row").filter({ hasText: "Ana QA" }).getByRole("cell")).toHaveText([
    "1",
    "2",
    "R$ 60,00",
  ]);
  await expect(
    resumo.getByRole("row").filter({ hasText: "Bruno QA" }).getByRole("cell"),
  ).toHaveText(["1", "1,125", "R$ 40,00"]);
  await expect(
    resumo.getByRole("row").filter({ hasText: "Sem vendedor" }).getByRole("cell"),
  ).toHaveText(["1", "1", "R$ 30,00"]);
  await expect(
    page.getByText(/Quantidade do produto: 4,125.*Valor bruto do produto: R\$\s*130,00/),
  ).toBeVisible();
  await expect(page.getByText("Areia QA · 1", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("cell", { name: "QA-5", exact: true })).toHaveCount(0);

  await page.getByRole("combobox", { name: "Vendedor", exact: true }).fill("Ana QA");
  await page.getByRole("option", { name: "Ana QA", exact: true }).click();
  await expect(resumo.getByRole("row")).toHaveCount(2);
  await expect(
    page.getByText(/Quantidade do produto: 2.*Valor bruto do produto: R\$\s*60,00/),
  ).toBeVisible();

  await page.getByRole("button", { name: "Remover Ração QA (RACAO-QA)", exact: true }).click();
  await expect(resumo).toHaveCount(0);
  await expect(page.getByText(/2 venda\(s\) · Total vendido: R\$\s*290,00/)).toBeVisible();
  await expect(page.getByRole("combobox", { name: "Vendedor", exact: true })).toHaveValue("Ana QA");

  const campoVendedor = page.locator("#relatorio-vendedor").locator("..");
  await campoVendedor.getByRole("button", { name: "Limpar seleção", exact: true }).click();
  await expect(page.getByText(/4 venda\(s\) · Total vendido: R\$\s*460,00/)).toBeVisible();
});

test("exporta o recorte de produto para um arquivo Excel", async ({ page }) => {
  await abrirRelatorio(page);
  await selecionarProduto(page);
  const baixar = page.waitForEvent("download");
  await page.getByRole("button", { name: "Exportar Excel", exact: true }).click();
  const arquivo = await baixar;
  expect(arquivo.suggestedFilename()).toMatch(/^vendas_por_vendedor_produtos_.*\.xlsx$/);
  expect(await arquivo.failure()).toBeNull();
  const dados = await stat(await arquivo.path());
  expect(dados.size).toBeGreaterThan(100);
  await expect(page.getByText("Relatório por vendedor exportado.", { exact: true })).toBeVisible();
});

async function baixarPdf(page) {
  const baixar = page.waitForEvent("download");
  await page.getByRole("button", { name: "Exportar PDF", exact: true }).click();
  const arquivo = await baixar;
  expect(await arquivo.failure()).toBeNull();
  const dados = await readFile(await arquivo.path());
  expect(dados.subarray(0, 5).toString("ascii")).toBe("%PDF-");
  expect(dados.length).toBeGreaterThan(1000);
  return { arquivo, texto: dados.toString("latin1") };
}

test("exporta PDF somente do produto e vendedor selecionados", async ({ page }) => {
  await abrirRelatorio(page);
  await selecionarProduto(page);
  await page.getByRole("combobox", { name: "Vendedor", exact: true }).fill("Ana QA");
  await page.getByRole("option", { name: "Ana QA", exact: true }).click();
  await expect(
    page.getByText(/Quantidade do produto: 2.*Valor bruto do produto: R\$\s*60,00/),
  ).toBeVisible();

  const { arquivo, texto } = await baixarPdf(page);
  expect(arquivo.suggestedFilename()).toMatch(
    /^vendas_por_vendedor_produtos_\d{4}-\d{2}-\d{2}_\d{4}-\d{2}-\d{2}\.pdf$/,
  );
  expect(texto).toContain("Ana QA");
  expect(texto).toContain("60,00");
  expect(texto).not.toContain("Bruno QA");
  expect(texto).not.toContain("Areia QA");
  expect(texto).not.toContain("QA-5");
});

test("exporta PDF de todos os produtos com o total original das vendas", async ({ page }) => {
  await abrirRelatorio(page);
  await expect(page.getByText(/4 venda\(s\) · Total vendido: R\$\s*460,00/)).toBeVisible();

  const { arquivo, texto } = await baixarPdf(page);
  expect(arquivo.suggestedFilename()).toMatch(
    /^vendas_por_vendedor_\d{4}-\d{2}-\d{2}_\d{4}-\d{2}-\d{2}\.pdf$/,
  );
  expect(texto).toContain("Ana QA");
  expect(texto).toContain("Bruno QA");
  expect(texto).toContain("460,00");
  expect(texto).not.toContain("QA-5");
});
