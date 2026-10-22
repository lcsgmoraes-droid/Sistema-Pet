import { expect, test } from "@playwright/test";

const baseUrl = process.env.E2E_BASE_URL;
const local = ["localhost", "127.0.0.1", "[::1]"].includes(
  new URL(baseUrl || "http://localhost:5173").hostname,
);
const produtoId = 98246;
const apiProduto = `/api/produtos/${produtoId}`;
const loteEntrada = {
  id: 65001,
  produto_id: produtoId,
  nome_lote: "NF111160-14",
  quantidade_inicial: 5,
  quantidade_disponivel: 5,
  quantidade_reservada: 0,
  data_validade: null,
  data_fabricacao: null,
  apenas_identificacao: false,
  custo_unitario: 23.64,
  status: "ativo",
};

test.use({ channel: "chrome" });
test.skip(
  !baseUrl || !local,
  "requer E2E_BASE_URL explícita de um frontend local; usa somente API sintética",
);

async function prepararApi(page, { estoque = 5, lotes = [loteEntrada] } = {}) {
  const tenant = { id: "tenant-lotes-qa", name: "Loja Sintética QA", login_name: "qa" };
  const user = { id: 42001, name: "Usuário QA", role: { name: "admin" }, tenant };
  const estado = {
    produto: {
      id: produtoId,
      nome: "Keldog Biscoito Original 900g QA",
      codigo: "QA-2766",
      tipo_produto: "SIMPLES",
      unidade: "UN",
      estoque_atual: estoque,
      estoque_reservado: 0,
      preco_custo: 23.64,
      preco_venda: 30,
      controlar_estoque: true,
    },
    lotes: structuredClone(lotes),
    envios: [],
    falharProximo: false,
    aguardarCarga: null,
  };
  await page.addInitScript(
    ({ user, tenant }) => {
      localStorage.setItem("access_token", "token-sintetico-sem-validade");
      localStorage.setItem("user", JSON.stringify(user));
      localStorage.setItem("selectedTenant", JSON.stringify(tenant));
    },
    { user, tenant },
  );
  // Todas as chamadas /api são interceptadas, inclusive após salvar/recarregar.
  // Nenhuma requisição usa backend, banco ou credenciais reais.
  await page.route(
    (url) => url.pathname.startsWith("/api/"),
    async (route) => {
      const request = route.request();
      const path = new URL(request.url()).pathname;
      if (path === `${apiProduto}/lotes-validade` && request.method() === "PUT") {
        const payload = request.postDataJSON();
        estado.envios.push(payload);
        if (estado.falharProximo) {
          estado.falharProximo = false;
          return route.fulfill({
            status: 503,
            json: { detail: "Falha simulada ao salvar lote." },
          });
        }
        const existente = estado.lotes.find((lote) => lote.id === payload.lote_id);
        const salvo = {
          ...(existente || {
            id: 65002,
            produto_id: produtoId,
            status: "ativo",
            quantidade_reservada: 0,
            apenas_identificacao: true,
          }),
          nome_lote: payload.nome_lote,
          quantidade_disponivel: payload.quantidade,
          data_validade: payload.data_validade,
          data_fabricacao: payload.data_fabricacao,
        };
        estado.lotes = existente
          ? estado.lotes.map((lote) => (lote.id === existente.id ? salvo : lote))
          : [...estado.lotes, salvo];
        return route.fulfill({ json: salvo });
      }
      if (path === `${apiProduto}/lotes`) {
        if (estado.aguardarCarga) await estado.aguardarCarga;
        return route.fulfill({ json: estado.lotes });
      }
      if (path === apiProduto) return route.fulfill({ json: estado.produto });
      const respostas = {
        "/api/auth/me-multitenant": user,
        "/api/auth/my-tenants": { tenants: [tenant] },
        "/api/modulos/status": { modulos_ativos: [], plano: "basico" },
        "/api/usuarios/me/menu-favoritos": { items: [] },
        "/api/lembretes/pendentes": { total: 0, lembretes: [] },
        [`/api/estoque/movimentacoes/produto/${produtoId}`]: [],
        [`/api/estoque/movimentacoes/produto/${produtoId}/vendas-por-canal`]: {
          vendas_por_canal: [],
        },
      };
      return route.fulfill({ json: respostas[path] || {} });
    },
  );
  return estado;
}

async function abrirLotes(page) {
  await page.goto(`/produtos/${produtoId}/movimentacoes?aba=lotes`);
  await expect(page.getByRole("heading", { name: "Lotes e validade", exact: true })).toBeVisible();
  await expect(page.getByText("Carregando lotes...", { exact: true })).toHaveCount(0);
}

const linhaLote = (page, numero = loteEntrada.nome_lote) =>
  page.getByRole("row").filter({ hasText: numero });

async function preencher(page, { numero = "525", quantidade = "5", validade = "26082027" } = {}) {
  await page.locator("#lote-numero").fill(numero);
  await page.locator("#lote-quantidade").fill(quantidade);
  await page.locator("#lote-validade").fill(validade);
  await page.locator("#lote-numero").click(); // Fecha o calendário do InputData.
}

async function enviar(page, rotulo) {
  const resposta = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname === `${apiProduto}/lotes-validade` &&
      response.request().method() === "PUT",
  );
  await page.getByRole("button", { name: rotulo, exact: true }).click();
  return resposta;
}

async function verificarBloqueio(page, estado, rotulo) {
  const botao = page.getByRole("button", { name: rotulo, exact: true });
  // A barreira pode desabilitar o botão ou validar no envio; em ambos os casos
  // o formulário não pode enviar uma operação incorreta para a API.
  if (await botao.isEnabled()) await botao.click();
  expect(estado.envios).toHaveLength(0);
  await expect(page.locator("#lote-numero")).toBeVisible();
}

test.describe("Lotes e validade — distinguir correção de novo cadastro", () => {
  test("aguarda os lotes antes de oferecer cadastro ou correção", async ({ page }) => {
    const estado = await prepararApi(page);
    let liberarCarga;
    estado.aguardarCarga = new Promise((resolve) => {
      liberarCarga = resolve;
    });
    await page.goto(`/produtos/${produtoId}/movimentacoes?aba=lotes`);
    await expect(page.getByText("Carregando lotes...", { exact: true })).toBeVisible();
    await expect(page.locator("#lote-numero")).toHaveCount(0);
    await expect(
      page.getByRole("button", { name: "Cadastrar outro lote", exact: true }),
    ).toHaveCount(0);
    liberarCarga();
    await expect(linhaLote(page)).toBeVisible();
    await expect(page.getByText("Carregando lotes...", { exact: true })).toHaveCount(0);
    await expect(page.locator("#lote-numero")).toHaveCount(0);
  });

  test("começa na lista e corrige o lote da nota sem duplicar suas cinco unidades", async ({
    page,
  }) => {
    const estado = await prepararApi(page);
    await abrirLotes(page);
    await expect(page.locator("#lote-numero")).toHaveCount(0);
    await expect(
      page.getByText("Todo o estoque já está identificado em lotes.", { exact: true }),
    ).toBeVisible();
    await linhaLote(page).getByRole("button", { name: "Corrigir lote", exact: true }).click();
    await expect(
      page.getByRole("heading", { name: "Corrigir lote existente", exact: true }),
    ).toBeVisible();
    await expect(page.locator("#lote-numero")).toHaveValue(loteEntrada.nome_lote);
    await preencher(page);
    expect((await enviar(page, "Salvar correção")).status()).toBe(200);
    expect(estado.envios).toEqual([
      {
        lote_id: loteEntrada.id,
        nome_lote: "525",
        quantidade: 5,
        data_validade: "2027-08-26",
        data_fabricacao: null,
      },
    ]);
    await expect(linhaLote(page, "525")).toBeVisible();
    await expect(page.locator("#lote-numero")).toHaveCount(0);
    expect(estado.lotes).toHaveLength(1);
    expect(estado.produto.estoque_atual).toBe(5);
    expect(estado.lotes[0].custo_unitario).toBe(loteEntrada.custo_unitario);
    expect(estado.lotes[0].apenas_identificacao).toBe(false);
  });

  test("novo cadastro não reutiliza as unidades já identificadas", async ({ page }) => {
    const estado = await prepararApi(page);
    await abrirLotes(page);
    await page.getByRole("button", { name: "Cadastrar outro lote", exact: true }).click();
    await expect(
      page.getByRole("heading", { name: "Cadastrar outro lote", exact: true }),
    ).toBeVisible();
    await preencher(page, { numero: "OUTRO" });
    await verificarBloqueio(page, estado, "Cadastrar lote");
    await expect(
      page.getByText(/Todo o estoque já está identificado em lotes/).first(),
    ).toBeVisible();
    await page.getByRole("button", { name: "Cancelar", exact: true }).click();
    await expect(page.locator("#lote-numero")).toHaveCount(0);
    await expect(linhaLote(page)).toBeVisible();
  });

  test("cadastra outro lote somente com o saldo ainda sem lote", async ({ page }) => {
    const estado = await prepararApi(page, { estoque: 10 });
    await abrirLotes(page);
    await page.getByRole("button", { name: "Cadastrar outro lote", exact: true }).click();
    await preencher(page, { numero: "OUTRO", quantidade: "5,0" });
    expect((await enviar(page, "Cadastrar lote")).status()).toBe(200);
    expect(estado.envios[0]).toMatchObject({
      lote_id: null,
      nome_lote: "OUTRO",
      quantidade: 5,
      data_validade: "2027-08-26",
    });
    await expect(linhaLote(page, "OUTRO")).toBeVisible();
    expect(estado.lotes).toHaveLength(2);
    expect(estado.lotes.reduce((total, lote) => total + lote.quantidade_disponivel, 0)).toBe(10);
    expect(estado.produto.estoque_atual).toBe(10);
  });

  test("novo com número existente não vira correção silenciosa", async ({ page }) => {
    const estado = await prepararApi(page, { estoque: 10 });
    await abrirLotes(page);
    await page.getByRole("button", { name: "Cadastrar outro lote", exact: true }).click();
    await preencher(page, { numero: ` ${loteEntrada.nome_lote} `, quantidade: "2" });
    await verificarBloqueio(page, estado, "Cadastrar lote");
    await expect(page.locator("#lote-numero")).toHaveAttribute("aria-invalid", "true");
    expect(estado.lotes[0].quantidade_disponivel).toBe(5);
  });

  test("falha ao salvar mantém a correção preenchida e permite tentar novamente", async ({
    page,
  }) => {
    const estado = await prepararApi(page);
    await abrirLotes(page);
    await linhaLote(page).getByRole("button", { name: "Corrigir lote", exact: true }).click();
    await preencher(page);
    estado.falharProximo = true;
    expect((await enviar(page, "Salvar correção")).status()).toBe(503);
    await expect(page.locator("#lote-numero")).toHaveValue("525");
    await expect(page.locator("#lote-quantidade")).toHaveValue("5");
    await expect(page.locator("#lote-validade")).toHaveValue("26/08/2027");
    expect((await enviar(page, "Salvar correção")).status()).toBe(200);
    expect(estado.envios).toHaveLength(2);
    expect(estado.envios[1]).toEqual(estado.envios[0]);
    await expect(linhaLote(page, "525")).toBeVisible();
  });

  test("permite corrigir nome de divergência antiga sem aumentar a quantidade", async ({
    page,
  }) => {
    const estado = await prepararApi(page, { estoque: 3 });
    await abrirLotes(page);
    await linhaLote(page).getByRole("button", { name: "Corrigir lote", exact: true }).click();
    await preencher(page);
    expect((await enviar(page, "Salvar correção")).status()).toBe(200);
    expect(estado.envios[0]).toMatchObject({ lote_id: loteEntrada.id, quantidade: 5 });
    expect(estado.produto.estoque_atual).toBe(3);
  });

  test("correção aceita zero para retirar a identificação", async ({ page }) => {
    const estado = await prepararApi(page);
    await abrirLotes(page);
    await linhaLote(page).getByRole("button", { name: "Corrigir lote", exact: true }).click();
    await preencher(page, { numero: loteEntrada.nome_lote, quantidade: "0" });
    expect((await enviar(page, "Salvar correção")).status()).toBe(200);
    expect(estado.envios[0]).toMatchObject({ lote_id: loteEntrada.id, quantidade: 0 });
    expect(estado.produto.estoque_atual).toBe(5);
  });

  test("validade inválida e fabricação posterior impedem salvar", async ({ page }) => {
    const estado = await prepararApi(page, { estoque: 10 });
    await abrirLotes(page);
    await page.getByRole("button", { name: "Cadastrar outro lote", exact: true }).click();
    await preencher(page, { numero: "OUTRO", validade: "31022027" });
    await page.getByRole("button", { name: "Cadastrar lote", exact: true }).click();
    await expect(page.locator("#lote-validade")).toHaveAttribute("aria-invalid", "true");
    expect(estado.envios).toHaveLength(0);
    await page.locator("#lote-validade").fill("26082027");
    await page.locator("#lote-fabricacao").fill("27082027");
    await page.locator("#lote-numero").click();
    await page.getByRole("button", { name: "Cadastrar lote", exact: true }).click();
    await expect(page.locator("#lote-fabricacao")).toHaveAttribute("aria-invalid", "true");
    expect(estado.envios).toHaveLength(0);
    await page.locator("#lote-fabricacao").fill("");
    await page.locator("#lote-numero").click();
    expect((await enviar(page, "Cadastrar lote")).status()).toBe(200);
    expect(estado.envios[0].data_fabricacao).toBeNull();
  });

  test("correção preserva as unidades reservadas do lote", async ({ page }) => {
    const estado = await prepararApi(page, {
      lotes: [{ ...loteEntrada, quantidade_reservada: 3 }],
    });
    await abrirLotes(page);
    await linhaLote(page).getByRole("button", { name: "Corrigir lote", exact: true }).click();
    await preencher(page, { quantidade: "2" });
    await verificarBloqueio(page, estado, "Salvar correção");
    await expect(page.locator("#lote-quantidade")).toHaveAttribute("aria-invalid", "true");
    await page.locator("#lote-quantidade").fill("3");
    expect((await enviar(page, "Salvar correção")).status()).toBe(200);
    expect(estado.envios[0]).toMatchObject({ lote_id: loteEntrada.id, quantidade: 3 });
  });

  test("fabricação parcial exige completar ou limpar antes de salvar", async ({ page }) => {
    const estado = await prepararApi(page);
    await abrirLotes(page);
    await linhaLote(page).getByRole("button", { name: "Corrigir lote", exact: true }).click();
    await preencher(page);
    await page.locator("#lote-fabricacao").fill("0102");
    await page.locator("#lote-numero").click();
    await page.getByRole("button", { name: "Salvar correção", exact: true }).click();
    await expect(page.getByRole("alert")).toHaveText(
      "Informe uma data de fabricação completa e válida ou limpe o campo.",
    );
    expect(estado.envios).toHaveLength(0);
    await page.locator("#lote-fabricacao").fill("");
    await page.locator("#lote-numero").click();
    expect((await enviar(page, "Salvar correção")).status()).toBe(200);
    expect(estado.envios[0].data_fabricacao).toBeNull();
  });

  test("trocar de lote ou cancelar não transporta datas parciais para outro formulário", async ({
    page,
  }) => {
    const estado = await prepararApi(page, {
      estoque: 10,
      lotes: [
        loteEntrada,
        { ...loteEntrada, id: 65003, nome_lote: "SEGUNDO", quantidade_disponivel: 2 },
      ],
    });
    await abrirLotes(page);
    await linhaLote(page).getByRole("button", { name: "Corrigir lote", exact: true }).click();
    await expect(page.locator("#lote-numero")).toBeFocused();
    await page.locator("#lote-numero").press("Tab");
    await expect(page.locator("#lote-quantidade")).toBeFocused();
    await page.locator("#lote-validade").fill("0102");
    await page.locator("#lote-fabricacao").fill("0304");
    await linhaLote(page, "SEGUNDO")
      .getByRole("button", { name: "Corrigir lote", exact: true })
      .click();
    await expect(page.locator("#lote-numero")).toHaveValue("SEGUNDO");
    await expect(page.locator("#lote-numero")).toBeFocused();
    await expect(page.locator("#lote-validade")).toHaveValue("");
    await expect(page.locator("#lote-fabricacao")).toHaveValue("");
    await page.locator("#lote-fabricacao").fill("0102");
    await page.locator("#lote-numero").click(); // Dispensa o calendário antes de cancelar.
    await page.getByRole("button", { name: "Cancelar", exact: true }).click();
    await page.getByRole("button", { name: "Cadastrar outro lote", exact: true }).click();
    await expect(page.locator("#lote-numero")).toHaveValue("");
    await expect(page.locator("#lote-validade")).toHaveValue("");
    await expect(page.locator("#lote-fabricacao")).toHaveValue("");
    expect(estado.envios).toHaveLength(0);
  });
});
