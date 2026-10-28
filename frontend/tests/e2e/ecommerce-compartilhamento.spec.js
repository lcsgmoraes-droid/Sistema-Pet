/* global process, localStorage, window, navigator, DOMException, history, PopStateEvent */
import { expect, test } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { mkdir } from "node:fs/promises";
import { fileURLToPath, URL } from "node:url";

// Loja e produtos sintéticos; nenhuma chamada de API chega ao backend.
const baseURL = process.env.E2E_BASE_URL || "http://localhost:5173";
const local = ["localhost", "127.0.0.1", "[::1]"].includes(new URL(baseURL).hostname);
const slug = "loja-compartilhamento-qa";
const produtoCatalogo = {
  id: 42001,
  nome: "Ração sintética QA",
  codigo: "QA-CATALOGO",
  categoria_nome: "Rações",
  preco_venda: 49.9,
  estoque_atual: 5,
};
const produtoForaDaPagina = {
  ...produtoCatalogo,
  id: 42099,
  nome: "Brinquedo sintético QA & diversão",
  codigo: "QA-FORA-DA-PAGINA",
  imagem_principal: "/uploads/qa-compartilhamento.svg",
  descricao: "Produto de teste que não aparece na primeira página do catálogo.",
};

test.use({ channel: "chrome" });
test.skip(!local, "requer frontend local; todas as APIs são simuladas");

async function prepararLoja(page, { compartilhar = "sucesso", clipboard = true } = {}) {
  const consultasDetalhe = [];
  await page.addInitScript(
    ({ compartilhar, clipboard }) => {
      localStorage.clear();
      window.__compartilhamentosQA = [];
      window.__copiasQA = [];
      Object.defineProperty(navigator, "share", {
        configurable: true,
        value:
          compartilhar === "indisponivel"
            ? undefined
            : async (dados) => {
                window.__compartilhamentosQA.push(dados);
                if (compartilhar === "cancelar") {
                  throw new DOMException("Cancelado pelo usuário", "AbortError");
                }
              },
      });
      Object.defineProperty(navigator, "clipboard", {
        configurable: true,
        value: clipboard
          ? { writeText: async (texto) => window.__copiasQA.push(texto) }
          : undefined,
      });
    },
    { compartilhar, clipboard },
  );
  await page.route(
    (url) => url.pathname.startsWith("/api/"),
    async (route) => {
      const url = new URL(route.request().url());
      const path = url.pathname;
      if (path === "/api/ecommerce/tenant-context") {
        return route.fulfill({
          json: {
            id: "tenant-sintetico-compartilhamento",
            name: "Loja Compartilhamento QA",
            ecommerce_slug: slug,
            ecommerce_ativo: true,
            logo_url: "/uploads/qa-loja.svg",
          },
        });
      }
      if (path === "/api/ecommerce/produtos") {
        return route.fulfill({
          json: { items: [produtoCatalogo], total: 50, offset: 0, limit: 24 },
        });
      }
      if (path === "/api/ecommerce/produtos/filtros") {
        return route.fulfill({ json: { categorias: [], marcas: [] } });
      }
      if (path === "/api/ecommerce/ofertas-ativas") {
        return route.fulfill({ json: { items: [] } });
      }
      if (path.startsWith("/api/ecommerce/products/")) {
        consultasDetalhe.push(url);
        const produto = [produtoCatalogo, produtoForaDaPagina].find(
          (item) => String(item.id) === path.split("/").at(-1),
        );
        return route.fulfill({
          status: produto ? 200 : 404,
          json: produto || { detail: "Produto não encontrado." },
        });
      }
      if (path === "/api/ecommerce/events") return route.fulfill({ json: { ok: true } });
      return route.fulfill({ status: 404, json: { detail: "API não simulada neste teste." } });
    },
  );
  await page.route("**/uploads/qa-*.svg", (route) => route.fulfill({
    contentType: "image/svg+xml",
    body: '<svg xmlns="http://www.w3.org/2000/svg" width="80" height="80"><rect width="80" height="80" fill="orange"/></svg>',
  }));
  return { consultasDetalhe };
}

async function abrirProduto(page, caminho = `/${slug}?produto=${produtoForaDaPagina.id}`) {
  await page.goto(caminho);
  const modal = page.getByRole("dialog");
  await expect(modal.getByRole("heading", { name: produtoForaDaPagina.nome })).toBeVisible();
  return modal;
}

function conferirLinkProduto(valor, produtoId) {
  const url = new URL(valor);
  expect(url.origin).toBe(new URL(baseURL).origin);
  expect(url.searchParams.get("produto")).toBe(String(produtoId));
  const lojaIdentificada =
    url.pathname === `/${slug}` ||
    (url.pathname === "/ecommerce" && url.searchParams.get("tenant") === slug);
  expect(lojaIdentificada).toBe(true);
  return url;
}

function conferirLinkCompartilhamento(valor, produtoId) {
  const url = new URL(valor);
  expect(url.origin).toBe(new URL(baseURL).origin);
  expect(url.pathname).toBe(`/api/ecommerce/compartilhar/produtos/${produtoId}`);
  expect([...url.searchParams.entries()]).toEqual([["tenant", slug]]);
  expect(url.hash).toBe("");
  return url;
}

test("link direto abre produto fora da página atual e continua correto após atualizar", async ({
  page,
}) => {
  const { consultasDetalhe } = await prepararLoja(page);
  await abrirProduto(page);
  await expect.poll(() => consultasDetalhe.length).toBeGreaterThan(0);
  expect(consultasDetalhe.every((url) => url.searchParams.get("tenant") === slug)).toBe(true);
  expect(consultasDetalhe.every((url) => url.searchParams.get("canal") === "ecommerce")).toBe(true);
  conferirLinkProduto(await page.locator('link[rel="canonical"]').getAttribute("href"), 42099);
  conferirLinkCompartilhamento(await page.locator('meta[property="og:url"]').getAttribute("content"), 42099);

  await page.reload();
  await expect(
    page.getByRole("dialog").getByRole("heading", { name: produtoForaDaPagina.nome }),
  ).toBeVisible();
});

test("trocar o produto ou remover o parâmetro pela navegação sincroniza os detalhes", async ({
  page,
}) => {
  await prepararLoja(page);
  await abrirProduto(page);
  await page.evaluate((caminho) => {
    history.pushState({}, "", caminho);
    window.dispatchEvent(new PopStateEvent("popstate"));
  }, `/${slug}?produto=${produtoCatalogo.id}`);
  await expect(
    page.getByRole("dialog").getByRole("heading", { name: produtoCatalogo.nome }),
  ).toBeVisible();
  await page.evaluate((caminho) => {
    history.pushState({}, "", caminho);
    window.dispatchEvent(new PopStateEvent("popstate"));
  }, `/${slug}`);
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("prévia usa foto do produto, volta à loja e restaura metadados ao sair", async ({ page }) => {
  await prepararLoja(page);
  await page.goto("/login");
  const titleOriginal = await page.title();
  const descriptionOriginal = await page.locator('meta[name="description"]').getAttribute("content");
  const navigate = (caminho) => page.evaluate((destino) => {
    history.pushState({}, "", destino);
    window.dispatchEvent(new PopStateEvent("popstate"));
  }, caminho);
  await navigate(`/${slug}?produto=${produtoForaDaPagina.id}`);
  await expect(page.getByRole("dialog").getByRole("heading", {
    name: produtoForaDaPagina.nome,
  })).toBeVisible();
  const image = page.locator('meta[property="og:image"]');
  const twitterImage = page.locator('meta[name="twitter:image"]');
  await expect(image).toHaveAttribute("content", `${new URL(baseURL).origin}${produtoForaDaPagina.imagem_principal}`);
  await expect(twitterImage).toHaveAttribute("content", `${new URL(baseURL).origin}${produtoForaDaPagina.imagem_principal}`);
  await expect(page.locator('meta[property="og:title"]')).toHaveAttribute("content", new RegExp(produtoForaDaPagina.nome));
  await navigate(`/${slug}?produto=${produtoCatalogo.id}`);
  await expect(page.getByRole("dialog").getByRole("heading", {
    name: produtoCatalogo.nome,
  })).toBeVisible();
  await expect(image).toHaveAttribute("content", `${new URL(baseURL).origin}/uploads/qa-loja.svg`);
  await navigate(`/${slug}`);
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(page.locator('meta[property="og:title"]')).toHaveAttribute("content", "Loja Compartilhamento QA | Loja online");
  await expect(image).toHaveAttribute("content", `${new URL(baseURL).origin}/uploads/qa-loja.svg`);
  await navigate("/login");
  await expect(page).toHaveTitle(titleOriginal);
  await expect(page.locator('meta[name="description"]')).toHaveAttribute("content", descriptionOriginal);
  await expect(image).toHaveCount(0);
  await expect(twitterImage).toHaveCount(0);
  await expect(page.locator('link[rel="canonical"]')).toHaveCount(0);
});

test("abrir, copiar e fechar produto preserva a loja identificada por tenant", async ({ page }) => {
  await prepararLoja(page);
  await page.goto(`/ecommerce?tenant=${slug}`);
  await page.getByRole("button").filter({ hasText: produtoCatalogo.nome }).first().click();
  const modal = page.getByRole("dialog");
  await expect(modal.getByRole("heading", { name: produtoCatalogo.nome })).toBeVisible();
  expect(new URL(page.url()).searchParams.get("tenant")).toBe(slug);
  expect(new URL(page.url()).searchParams.get("produto")).toBe(String(produtoCatalogo.id));

  await modal.getByRole("button", { name: /Copiar link/i }).click();
  await expect.poll(() => page.evaluate(() => window.__copiasQA.length)).toBe(1);
  conferirLinkCompartilhamento(await page.evaluate(() => window.__copiasQA[0]), produtoCatalogo.id);
  await modal.getByRole("button", { name: "Fechar detalhes do produto" }).click();
  await expect(modal).toHaveCount(0);
  expect(new URL(page.url()).searchParams.get("tenant")).toBe(slug);
  expect(new URL(page.url()).searchParams.has("produto")).toBe(false);
});

test("WhatsApp e compartilhamento nativo usam nome e link do produto selecionado", async ({
  page,
}) => {
  await prepararLoja(page);
  const modal = await abrirProduto(page);
  const whatsapp = new URL(
    await modal.getByRole("link", { name: /WhatsApp/i }).getAttribute("href"),
  );
  expect(whatsapp.hostname).toBe("wa.me");
  const mensagem = whatsapp.searchParams.get("text");
  expect(mensagem).toContain(produtoForaDaPagina.nome);
  const linkNaMensagem = mensagem.match(/https?:\/\/\S+/)?.[0];
  conferirLinkCompartilhamento(linkNaMensagem, produtoForaDaPagina.id);

  await modal.getByRole("button", { name: "Compartilhar", exact: true }).click();
  await expect.poll(() => page.evaluate(() => window.__compartilhamentosQA.length)).toBe(1);
  const dados = await page.evaluate(() => window.__compartilhamentosQA[0]);
  expect(`${dados.title || ""} ${dados.text || ""}`).toContain(produtoForaDaPagina.nome);
  conferirLinkCompartilhamento(dados.url, produtoForaDaPagina.id);
  expect(await page.evaluate(() => window.__copiasQA)).toEqual([]);
});

test("link recebido usa HTML do servidor e abre o produto correspondente", async ({ page }) => {
  await prepararLoja(page);
  const modal = await abrirProduto(page);
  await modal.getByRole("button", { name: /Copiar link/i }).click();
  await expect.poll(() => page.evaluate(() => window.__copiasQA.length)).toBe(1);
  const sharedUrl = await page.evaluate(() => window.__copiasQA[0]);
  conferirLinkCompartilhamento(sharedUrl, produtoForaDaPagina.id);
  // Reutiliza o renderizador real do backend com dados sintéticos e sem banco/API.
  const source = execFileSync(process.env.PYTHON || "python", [
    "-c",
    [
      "import json, sys",
      "from types import SimpleNamespace",
      "from app.services.ecommerce_product_share import render_product_share_html",
      "payload = json.loads(sys.argv[1])",
      "print(render_product_share_html(SimpleNamespace(**payload['tenant']), payload['product'], payload['base_url']))",
    ].join("\n"),
    JSON.stringify({
      tenant: { id: "00000000-0000-4000-8000-000000000001", name: "Loja Compartilhamento QA", ecommerce_slug: slug },
      product: produtoForaDaPagina,
      base_url: new URL(baseURL).origin,
    }),
  ], {
    cwd: fileURLToPath(new URL("../../../backend/", import.meta.url)),
    encoding: "utf8",
    env: { ...process.env, PYTHONIOENCODING: "utf-8" },
  });
  await page.route(sharedUrl, (route) => route.fulfill({ contentType: "text/html", body: source }));
  await page.goto(sharedUrl);
  await expect(page.getByRole("dialog").getByRole("heading", {
    name: produtoForaDaPagina.nome,
  })).toBeVisible();
  conferirLinkProduto(page.url(), produtoForaDaPagina.id);
});

test("cancelar o compartilhamento nativo não copia nem mostra erro", async ({ page }) => {
  await prepararLoja(page, { compartilhar: "cancelar" });
  const modal = await abrirProduto(page);
  await modal.getByRole("button", { name: "Compartilhar", exact: true }).click();
  await expect.poll(() => page.evaluate(() => window.__compartilhamentosQA.length)).toBe(1);
  expect(await page.evaluate(() => window.__copiasQA)).toEqual([]);
  await expect(modal.getByText(/não foi possível|erro ao compartilhar/i)).toHaveCount(0);
});

test("sem compartilhamento nem clipboard o link aparece para cópia manual", async ({ page }) => {
  await prepararLoja(page, { compartilhar: "indisponivel", clipboard: false });
  const modal = await abrirProduto(page);
  await modal.getByRole("button", { name: "Compartilhar", exact: true }).click();
  const campoLink = modal.getByRole("textbox");
  await expect(campoLink).toBeVisible();
  await expect(campoLink).toHaveAttribute("readonly", "");
  conferirLinkCompartilhamento(await campoLink.inputValue(), produtoForaDaPagina.id);
  await expect(modal.getByText("Link copiado!", { exact: true })).toHaveCount(0);
});

test("produto removido apresenta mensagem e encerra o carregamento", async ({ page }) => {
  await prepararLoja(page);
  await page.route("**/api/ecommerce/products/42999?**", (route) =>
    route.fulfill({ status: 404, json: { detail: "Produto não encontrado." } }),
  );
  await page.goto(`/${slug}?produto=42999`);
  await expect(page.getByText(produtoCatalogo.nome, { exact: true })).toBeVisible();
  await expect(page.getByText("Este produto não está mais disponível nesta loja.")).toBeVisible();
  await expect(page.getByRole("status").filter({ hasText: "Carregando produto" })).toHaveCount(0);
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("loja inválida apresenta mensagem e não mantém carregamento do produto", async ({ page }) => {
  await prepararLoja(page);
  await page.route(
    (url) =>
      url.pathname.startsWith("/api/ecommerce/") &&
      url.searchParams.get("tenant") === "loja-inexistente-qa",
    (route) => route.fulfill({ status: 404, json: { detail: "Loja inválida para e-commerce" } }),
  );
  await page.goto(`/ecommerce?tenant=loja-inexistente-qa&produto=${produtoForaDaPagina.id}`);
  await expect(page.getByText("Loja inválida para e-commerce", { exact: false })).toBeVisible();
  await expect(page.getByRole("status").filter({ hasText: "Carregando produto" })).toHaveCount(0);
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("ações de compartilhamento ficam acessíveis no celular sem rolagem horizontal", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await prepararLoja(page);
  const modal = await abrirProduto(page);
  const compartilhar = modal.getByRole("button", { name: "Compartilhar", exact: true });
  await compartilhar.scrollIntoViewIfNeeded();
  await expect(compartilhar).toBeInViewport();
  await expect(modal.getByRole("link", { name: /WhatsApp/i })).toBeInViewport();
  await expect(modal.getByRole("button", { name: /Copiar link/i })).toBeInViewport();
  const dimensoes = await modal.evaluate((elemento) => {
    const painel = elemento.firstElementChild;
    return { largura: painel.clientWidth, conteudo: painel.scrollWidth };
  });
  expect(dimensoes.conteudo).toBeLessThanOrEqual(dimensoes.largura);
  const pasta = fileURLToPath(new URL("../../../runtime/", import.meta.url));
  await mkdir(pasta, { recursive: true });
  await page.screenshot({
    path: fileURLToPath(
      new URL("../../../runtime/ecommerce-compartilhamento-mobile.png", import.meta.url),
    ),
  });
});

test("produto aberto pelo link preserva imagem e limite da oferta no carrinho", async ({
  page,
}) => {
  await prepararLoja(page);
  await page.route("**/uploads/qa-compartilhamento.svg", (route) =>
    route.fulfill({
      contentType: "image/svg+xml",
      body: '<svg xmlns="http://www.w3.org/2000/svg" width="80" height="80"><rect width="80" height="80" fill="orange"/></svg>',
    }),
  );
  await page.route(`**/api/ecommerce/products/${produtoForaDaPagina.id}?**`, (route) =>
    route.fulfill({
      json: {
        ...produtoForaDaPagina,
        imagem_principal: "/uploads/qa-compartilhamento.svg",
        promocao_ativa: true,
        preco_promocional: 39.9,
        promocao_origem: "validade",
        promocao_validade: { ativa: true, quantidade_promocional: 1 },
      },
    }),
  );
  const modal = await abrirProduto(page);
  await modal.getByRole("button", { name: "Adicionar ao carrinho", exact: true }).click();
  await modal.getByRole("button", { name: "Ver carrinho", exact: true }).click();
  await expect(modal).toHaveCount(0);
  const imagem = page.getByRole("img", { name: produtoForaDaPagina.nome });
  await expect(imagem).toBeVisible();
  await expect.poll(() => imagem.evaluate((elemento) => elemento.naturalWidth)).toBeGreaterThan(0);
  await page
    .getByRole("button", { name: `Aumentar quantidade de ${produtoForaDaPagina.nome}` })
    .click();
  await expect(
    page.getByText("Oferta de validade disponivel para ate 1 unidade(s) nesse preco.", {
      exact: false,
    }),
  ).toBeVisible();
  await expect
    .poll(() =>
      page.evaluate(
        () => JSON.parse(localStorage.getItem("ecommerce_guest_cart")).itens[0].quantidade,
      ),
    )
    .toBe(1);
});
