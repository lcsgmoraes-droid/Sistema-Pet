import { expect, test } from "@playwright/test";
import { readFile } from "node:fs/promises";
import process from "node:process";
import { URL } from "node:url";

// Regressão em navegador real com dados sintéticos: nenhuma chamada chega ao backend.
const local = ["localhost", "127.0.0.1", "[::1]"].includes(
  new URL(process.env.E2E_BASE_URL || "http://localhost:5173").hostname,
);
const movimentosPath = "/api/produtos/relatorio/movimentacoes";
const vendasPath = "/api/produtos/relatorio/produto-vendas";
const produto = {
  id: 42002,
  nome: "Ração granel sintética QA",
  codigo: "QA-GRANEL",
  sku: "QA-42002",
  unidade: "KG",
  estoque_atual: 60.005,
  estoque_minimo: 5,
};
const quantidades = Array.from({ length: 84 }, (_, indice) => [0.25, 0.5, 1, 2][indice % 4]);

test.use({ channel: "chrome" });
test.skip(
  !local || !process.env.E2E_BASE_URL,
  "requer E2E_BASE_URL explícita de um frontend local; não requer credenciais",
);

async function prepararApi(page) {
  const tenant = { id: "tenant-sintetico-qa", name: "Loja Sintética QA", login_name: "qa" };
  const user = { id: 42001, name: "Usuário QA", role: { name: "admin" }, tenant };
  const consultas = [];
  await page.addInitScript(
    ({ user, tenant }) => {
      globalThis.localStorage.setItem("access_token", "token-sintetico-sem-validade");
      globalThis.localStorage.setItem("user", JSON.stringify(user));
      globalThis.localStorage.setItem("selectedTenant", JSON.stringify(tenant));
    },
    { user, tenant },
  );
  await page.route(
    (url) => url.pathname.startsWith("/api/"),
    async (route) => {
      const url = new URL(route.request().url());
      const path = url.pathname;
      if (path === movimentosPath || path === vendasPath) {
        const params = Object.fromEntries(url.searchParams);
        consultas.push({ path, ...params });
        const operador = params.quantidade_operador;
        const limite = Number(params.quantidade_valor);
        const filtradas = quantidades.filter((qtd) => {
          if (operador === "acima_de") return qtd > limite;
          if (operador === "abaixo_de") return qtd < limite;
          if (operador === "igual_a") return qtd === limite;
          return true;
        });
        const pagina = Number(params.page || 1);
        const tamanho = Number(params.page_size || 20);
        const recorte = params.export_all === "true"
          ? filtradas
          : filtradas.slice((pagina - 1) * tamanho, pagina * tamanho);
        const quantidade = filtradas.reduce((soma, qtd) => soma + qtd, 0);
        if (path === movimentosPath) {
          return route.fulfill({
            json: {
              movimentacoes: recorte.map((qtd, indice) => ({
                id: indice + 1,
                produto_id: produto.id,
                produto_nome: produto.nome,
                codigo: produto.codigo,
                sku: produto.sku,
                data: "24/10/2026",
                data_completa: "2026-10-24T12:00:00",
                saida: qtd,
                estoque: produto.estoque_atual,
                tipo: "Saida",
                motivo_label: "Venda",
                usuario: user.name,
                valor_total: qtd * 10,
              })),
              total_registros: filtradas.length,
              page: pagina,
              page_size: tamanho,
              pages: Math.ceil(filtradas.length / tamanho),
              totais: { total_entradas: 0, total_saidas: quantidade, valor_total: quantidade * 10 },
            },
          });
        }
        return route.fulfill({
          json: {
            produto,
            resumo: { quantidade_vendida_30: quantidade, media_diaria_30: quantidade / 30 },
            janelas: [7, 15, 30, 60, 90].map((dias) => ({
              dias,
              quantidade_vendida: quantidade,
              numero_vendas: filtradas.length,
              media_diaria: quantidade / dias,
              valor_vendido: quantidade * 10,
            })),
            curva_30_dias: [],
            historico_vendas: recorte.map((qtd, indice) => ({
              id: indice + 1,
              venda_id: indice + 100,
              numero_venda: indice + 100,
              data_venda: "2026-10-24T12:00:00",
              cliente_nome: "Cliente sintético QA",
              quantidade: qtd,
              preco_unitario: 10,
              subtotal: qtd * 10,
              status: "finalizada",
            })),
            historico_total: filtradas.length,
            historico_page: pagina,
            historico_page_size: tamanho,
            historico_pages: Math.ceil(filtradas.length / tamanho),
          },
        });
      }
      if (path === "/api/produtos/" || path === "/api/produtos") {
        return route.fulfill({ json: { items: [produto], total: 1 } });
      }
      const respostas = {
        "/api/auth/me-multitenant": user,
        "/api/auth/my-tenants": { tenants: [tenant] },
        "/api/modulos/status": { modulos_ativos: [], plano: "basico" },
        "/api/usuarios/me/menu-favoritos": { items: [] },
        "/api/lembretes/pendentes": { total: 0, lembretes: [] },
      };
      return route.fulfill({ json: respostas[path] || {} });
    },
  );
  return consultas;
}

async function abrirProduto(page) {
  await page.goto("/produtos/relatorio");
  await page.locator("#relatorio-busca-produto").fill("granel");
  await page.getByRole("button", { name: new RegExp(produto.nome) }).click();
  await expect(page.getByRole("heading", { name: /Ração granel sintética QA/ })).toBeVisible();
  await expect(page.getByText("Carregando historico comercial do produto...")).toHaveCount(0);
}

async function escolherComparacao(page, label) {
  await page.locator("#relatorio-quantidade-operador").click();
  await page.getByRole("option", { name: label, exact: true }).click();
}

async function aplicar(page, operador, valor) {
  const resposta = (path) => page.waitForResponse((r) => {
    const url = new URL(r.url());
    return url.pathname === path && url.searchParams.get("quantidade_operador") === operador
      && url.searchParams.get("quantidade_valor") === valor;
  });
  const pendentes = [resposta(movimentosPath), resposta(vendasPath)];
  await page.getByRole("button", { name: "Atualizar painel", exact: true }).click();
  await Promise.all(pendentes);
}

function painel(page, titulo) {
  return page.getByRole("heading", { name: titulo, exact: true }).locator("../../..");
}

test.describe("Giro do produto — filtro por quantidade", () => {
  test("aplica acima, abaixo e igual por item, com unidade kg e vírgula decimal", async ({ page }) => {
    const consultas = await prepararApi(page);
    await abrirProduto(page);
    await expect(page.getByRole("textbox", { name: /Quantidade \(kg\)/ })).toBeVisible();
    for (const [label, operador, valor, apiValor, total] of [
      ["Acima de", "acima_de", "1", "1", 21],
      ["Abaixo de", "abaixo_de", "1", "1", 42],
      ["Igual a", "igual_a", "0,5", "0.5", 21],
    ]) {
      await escolherComparacao(page, label);
      await page.locator("#relatorio-quantidade-valor").fill(valor);
      await aplicar(page, operador, apiValor);
      await expect(painel(page, "Movimentacoes filtradas")).toContainText(`de ${total}`);
      await expect(painel(page, "Historico recente de vendas do produto")).toContainText(`${total} registro(s)`);
      for (const path of [movimentosPath, vendasPath]) {
        expect(consultas.filter((c) => c.path === path).at(-1)).toMatchObject({
          quantidade_operador: operador, quantidade_valor: apiValor, page: "1",
        });
      }
    }
  });

  test("preserva o filtro no período, nas duas paginações e na exportação", async ({ page }) => {
    const consultas = await prepararApi(page);
    await abrirProduto(page);
    await escolherComparacao(page, "Abaixo de");
    await page.locator("#relatorio-quantidade-valor").fill("1");
    await aplicar(page, "abaixo_de", "1");
    await page.screenshot({ path: test.info().outputPath("quantidade-desktop.png"), fullPage: true });
    const periodoRespostas = [movimentosPath, vendasPath].map((path) =>
      page.waitForResponse((r) => new URL(r.url()).pathname === path),
    );
    await page.getByRole("button", { name: "15 dias", exact: true }).click();
    await Promise.all(periodoRespostas);
    for (const [titulo, path] of [
      ["Movimentacoes filtradas", movimentosPath],
      ["Historico recente de vendas do produto", vendasPath],
    ]) {
      await painel(page, titulo).getByRole("button", { name: "Proxima", exact: true }).click();
      await expect.poll(() => consultas.filter((c) => c.path === path).at(-1)?.page).toBe("2");
      expect(consultas.filter((c) => c.path === path).at(-1)).toMatchObject({
        quantidade_operador: "abaixo_de", quantidade_valor: "1",
      });
    }
    const downloadPendente = page.waitForEvent("download");
    await page.getByRole("button", { name: "Exportar CSV", exact: true }).click();
    const download = await downloadPendente;
    expect(download.suggestedFilename()).toMatch(/^movimentacoes_produtos_.*\.csv$/);
    const linhasCsv = (await readFile(await download.path(), "utf8")).trim().split("\n").slice(1);
    expect(linhasCsv).toHaveLength(42);
    expect(linhasCsv.every((linha) => Number(linha.split(";")[8]) < 1)).toBe(true);
    expect(consultas.filter((c) => c.path === movimentosPath).at(-1)).toMatchObject({
      quantidade_operador: "abaixo_de", quantidade_valor: "1", export_all: "true", page: "1",
    });
    await page.setViewportSize({ width: 390, height: 844 });
    await expect(page.locator("#relatorio-quantidade-operador")).toBeVisible();
    expect(await page.evaluate(() => globalThis.document.documentElement.scrollWidth <= globalThis.innerWidth)).toBe(true);
    await page.screenshot({ path: test.info().outputPath("quantidade-mobile.png"), fullPage: true });
    await page.getByRole("button", { name: "Limpar filtros", exact: true }).click();
    await expect(page.locator("#relatorio-busca-produto")).toBeVisible();
    await expect.poll(() => consultas.filter((c) => c.path === movimentosPath).at(-1)?.quantidade_operador).toBeUndefined();
    await expect(page.locator("#relatorio-quantidade-operador")).toHaveValue("Todas as quantidades");
  });

  test("valor inválido ou vazio não consulta o relatório nem troca o filtro aplicado", async ({ page }) => {
    const consultas = await prepararApi(page);
    await abrirProduto(page);
    await escolherComparacao(page, "Acima de");
    await page.locator("#relatorio-quantidade-valor").fill("1");
    await aplicar(page, "acima_de", "1");
    const total = consultas.length;
    for (const valor of ["", "0", "-1", "abc", "0,0001"]) {
      await page.locator("#relatorio-quantidade-valor").fill(valor);
      await page.getByRole("button", { name: "Atualizar painel", exact: true }).click();
      await expect(page.locator("#relatorio-quantidade-valor")).toHaveAttribute("aria-invalid", "true");
      expect(consultas).toHaveLength(total);
    }
    await escolherComparacao(page, "Todas as quantidades");
    const atualizadas = page.waitForResponse((r) => new URL(r.url()).pathname === movimentosPath
      && !new URL(r.url()).searchParams.has("quantidade_operador"));
    await page.getByRole("button", { name: "Atualizar painel", exact: true }).click();
    await atualizadas;
    expect(consultas.filter((c) => c.path === movimentosPath).at(-1)?.quantidade_valor).toBeUndefined();
  });
});
