import { expect, test } from "@playwright/test";
import { credenciaisDoAmbiente, fecharTour } from "./helpers.js";

const env = credenciaisDoAmbiente();
const local = env && ["localhost", "127.0.0.1"].includes(new URL(env.baseURL).hostname);
let sessao;
let user;
let parceiro;
let produtos;
let vendaAnterior;
let vendaAbertaAnterior;
let vendaParcialAnterior;
let vendaSemRegraAnterior;
let caixaId;
const nomeGrupo = `QA Comissao UI ${Date.now()}`;

test.describe("Comissão fixa e grupos em DEV", () => {
  test.skip(!local, "Requer identidade E2E e servidor DEV local; produção não é permitida.");
  test.setTimeout(120_000);
  test.use({ actionTimeout: 12_000 });

  async function api(request, metodo, caminho, data) {
    const resposta = await request[metodo](`${env.baseURL}/api${caminho}`, {
      headers: { Authorization: `Bearer ${sessao.access_token}` },
      data,
    });
    expect(resposta.ok(), `${metodo.toUpperCase()} ${caminho}: ${resposta.status()}`).toBeTruthy();
    return resposta.json();
  }

  async function criarVenda(request) {
    return api(request, "post", "/vendas", {
      funcionario_id: parceiro.id,
      vendedor_funcionario_id: parceiro.id,
      itens: produtos.map((produto) => ({
        tipo: "produto",
        produto_id: produto.id,
        quantidade: 2,
        preco_unitario: 20,
        subtotal: 40,
      })),
      observacoes: nomeGrupo,
      tem_entrega: false,
    });
  }

  async function receber(request, venda, valor) {
    await api(request, "post", `/vendas/${venda.id}/finalizar`, {
      caixa_id: caixaId,
      pagamentos: [{ forma_pagamento: "Dinheiro", valor }],
    });
  }

  async function vender(request) {
    const venda = await criarVenda(request);
    await receber(request, venda, 80);
    return venda;
  }

  test.beforeAll(async ({ request }) => {
    const login = await request.post(`${env.baseURL}/api/auth/login-multitenant`, {
      data: { email: env.email, password: env.password },
    });
    expect(login.ok()).toBeTruthy();
    sessao = await login.json();
    const tenantId = process.env.E2E_TENANT_ID || sessao.tenants[0].id;
    sessao = await api(request, "post", "/auth/select-tenant", { tenant_id: tenantId });
    user = await api(request, "get", "/auth/me-multitenant");
    const caixa = await api(request, "get", "/caixas/aberto");
    expect(caixa?.status, "O tenant QA precisa ter um caixa aberto previamente.").toBe("aberto");
    caixaId = caixa.id;
    parceiro = await api(request, "post", "/clientes/", {
      nome: `${nomeGrupo} parceiro`,
      tipo_pessoa: "PF",
      is_funcionario: true,
      parceiro_ativo: true,
    });
    produtos = [];
    for (let indice = 1; indice <= 2; indice += 1) {
      const produto = await api(request, "post", "/produtos/", {
        nome: `${nomeGrupo} produto ${indice}`,
        codigo: `QA-COM-UI-${Date.now()}-${indice}`,
        preco_venda: 20,
        preco_custo: 5,
        unidade: "UN",
        tipo_produto: "SIMPLES",
        ativo: true,
        anunciar_app: false,
        anunciar_ecommerce: false,
      });
      await api(request, "post", "/estoque/entrada", {
        produto_id: produto.id,
        quantidade: 30,
        custo_unitario: 5,
        motivo: "ajuste",
        observacao: nomeGrupo,
      });
      produtos.push(produto);
    }
    vendaSemRegraAnterior = await criarVenda(request);
    await api(request, "post", "/comissoes/configuracoes/batch", {
      configuracoes: produtos.map((produto) => ({
        funcionario_id: parceiro.id,
        tipo: "produto",
        referencia_id: produto.id,
        tipo_calculo: "fixo",
        percentual: 0,
        valor_fixo: 3,
        comissao_venda_parcial: true,
      })),
    });
    vendaAnterior = await vender(request);
    vendaAbertaAnterior = await criarVenda(request);
    vendaParcialAnterior = await criarVenda(request);
    await receber(request, vendaParcialAnterior, 40);
    const hoje = String(vendaAnterior.data_venda).slice(0, 10);
    const relatorio = await api(
      request,
      "get",
      `/relatorios/vendas/relatorio?data_inicio=${hoje}&data_fim=${hoje}`,
    );
    const vendaNoRelatorio = relatorio.lista_vendas.find((venda) => venda.id === vendaAnterior.id);
    expect(vendaNoRelatorio).toBeDefined();
    expect(vendaNoRelatorio.itens.map((item) => item.produto_codigo).sort()).toEqual(
      produtos.map((produto) => produto.codigo).sort(),
    );
  });

  test("salva vários produtos e aplica R$ 5 por unidade somente às novas vendas", async ({
    page,
    request,
  }, testInfo) => {
    await page.addInitScript(
      ({ sessao, user }) => {
        localStorage.setItem("access_token", sessao.access_token);
        if (sessao.refresh_token) localStorage.setItem("refresh_token", sessao.refresh_token);
        localStorage.setItem("user", JSON.stringify(user));
        localStorage.setItem("selectedTenant", JSON.stringify(user.tenant));
        localStorage.setItem("tour_visto_pdv", "1");
      },
      { sessao, user },
    );
    await page.goto("/financeiro/vendas");
    await fecharTour(page);
    await page.getByRole("tab", { name: "Por vendedor", exact: true }).click();
    const busca = page.getByRole("combobox", { name: /^Produtos/ });
    for (const produto of produtos) {
      await busca.fill(produto.codigo);
      const opcao = page.getByRole("option").filter({ hasText: produto.nome });
      await expect(opcao).toContainText(`Cód.: ${produto.codigo}`);
      await opcao.click();
      await expect(
        page.getByRole("button", { name: `Remover ${produto.nome} (${produto.codigo})` }),
      ).toBeVisible();
    }
    await page.getByLabel("Nome do grupo", { exact: true }).fill(nomeGrupo);
    await page.getByRole("button", { name: "Salvar como novo grupo", exact: true }).click();
    await expect(page.getByText("Grupo de produtos salvo.", { exact: true })).toBeVisible();

    // Recarregar exige buscar o grupo persistido e reidratar os nomes dos produtos.
    await page.reload();
    await page.getByRole("tab", { name: "Por vendedor", exact: true }).click();
    await page
      .getByRole("combobox", { name: "Grupo de produtos salvo", exact: true })
      .fill(nomeGrupo);
    await page.getByRole("option", { name: nomeGrupo, exact: true }).click();
    for (const produto of produtos)
      await expect(
        page.getByRole("button", { name: `Remover ${produto.nome} (${produto.codigo})` }),
      ).toBeVisible();
    await page.screenshot({
      path: testInfo.outputPath("comissoes-grupo-multiplo.png"),
      fullPage: true,
    });

    await page.getByRole("button", { name: "Configurar comissão do grupo", exact: true }).click();
    const modal = page.getByRole("dialog", {
      name: `Comissão do grupo: ${nomeGrupo}`,
      exact: true,
    });
    await modal
      .getByRole("combobox", { name: "Parceiro comissionado", exact: true })
      .fill(parceiro.nome);
    await modal.getByRole("option", { name: parceiro.nome, exact: true }).click();
    await modal.getByText("Valor fixo por unidade", { exact: true }).click();
    const valor = modal.getByLabel(/^Valor por unidade vendida \(R\$\)/);
    await valor.focus();
    await valor.press("Control+A");
    await valor.pressSequentially("500");
    await expect(valor).toHaveValue("5,00");
    await expect(modal.getByText(/Multiplicado pela quantidade vendida/)).toBeVisible();
    await page.screenshot({
      path: testInfo.outputPath("comissoes-valor-fixo-modal.png"),
      fullPage: true,
    });
    await modal.getByRole("button", { name: "Salvar agora", exact: true }).click();
    const confirmacao = page.getByRole("dialog", { name: "Confirmar ação", exact: true });
    await expect(confirmacao).toContainText(
      "Comissões de vendas anteriores permanecem como foram calculadas.",
    );
    await confirmacao.getByRole("button", { name: "Confirmar", exact: true }).click();
    await expect(modal).not.toBeVisible();
    await expect(
      page.getByText("Comissão do grupo configurada para as próximas vendas.", { exact: true }),
    ).toBeVisible();

    const regras = await api(request, "get", `/comissoes/configuracoes/funcionario/${parceiro.id}`);
    expect(regras.data).toHaveLength(2);
    expect(
      regras.data.every((regra) => regra.tipo_calculo === "fixo" && regra.valor_fixo === 5),
    ).toBe(true);
    const anteriores = await api(request, "get", `/comissoes?venda_id=${vendaAnterior.id}`);
    expect(anteriores.lista).toHaveLength(2);
    expect(
      anteriores.lista.every((item) => item.valor_fixo === 3 && item.valor_comissao_gerada === 6),
    ).toBe(true);
    // Recebimentos futuros preservam a regra da inclusão, mesmo sem snapshot anterior.
    await receber(request, vendaAbertaAnterior, 80);
    const abertaAntiga = await api(request, "get", `/comissoes?venda_id=${vendaAbertaAnterior.id}`);
    expect(abertaAntiga.lista).toHaveLength(2);
    expect(
      abertaAntiga.lista.every((item) => item.valor_fixo === 3 && item.valor_comissao_gerada === 6),
    ).toBe(true);
    await receber(request, vendaParcialAnterior, 40);
    const parcelasAntigas = await api(
      request,
      "get",
      `/comissoes?venda_id=${vendaParcialAnterior.id}`,
    );
    expect(parcelasAntigas.lista).toHaveLength(4);
    expect(
      parcelasAntigas.lista.every(
        (item) => item.valor_fixo === 3 && item.valor_comissao_gerada === 3,
      ),
    ).toBe(true);
    await receber(request, vendaSemRegraAnterior, 80);
    expect(
      (await api(request, "get", `/comissoes?venda_id=${vendaSemRegraAnterior.id}`)).lista,
    ).toEqual([]);
    const novaVenda = await vender(request);
    const novas = await api(
      request,
      "get",
      `/comissoes?venda_id=${novaVenda.id}&funcionario_id=${parceiro.id}&status=pendente`,
    );
    expect(novas.lista).toHaveLength(2);
    expect(
      novas.lista.every((item) => item.valor_fixo === 5 && item.valor_comissao_gerada === 10),
    ).toBe(true);
    const provisionar = page.waitForResponse(
      (resposta) =>
        resposta.url().includes("/comissoes/grupos-produtos/") &&
        resposta.url().endsWith("/provisionar") &&
        resposta.request().method() === "POST",
    );
    await page.getByRole("button", { name: "Gerar contas a pagar", exact: true }).click();
    await page.getByRole("dialog").getByRole("button", { name: "Confirmar", exact: true }).click();
    const respostaProvisao = await provisionar;
    expect(respostaProvisao.ok()).toBe(true);
    expect((await respostaProvisao.json()).success).toBe(true);

    // O total de R$ 1,63 em dois recebimentos iguais deve fechar sem perder centavo.
    await api(request, "post", "/comissoes/configuracoes/batch", {
      configuracoes: [
        {
          funcionario_id: parceiro.id,
          tipo: "produto",
          referencia_id: produtos[0].id,
          tipo_calculo: "fixo",
          percentual: 0,
          valor_fixo: 1.63,
          comissao_venda_parcial: true,
        },
      ],
    });
    const parcial = await api(request, "post", "/vendas", {
      funcionario_id: parceiro.id,
      vendedor_funcionario_id: parceiro.id,
      itens: [
        {
          tipo: "produto",
          produto_id: produtos[0].id,
          quantidade: 1,
          preco_unitario: 20,
          subtotal: 20,
        },
      ],
      observacoes: nomeGrupo,
      tem_entrega: false,
    });
    for (let indice = 0; indice < 2; indice += 1)
      await api(request, "post", `/vendas/${parcial.id}/finalizar`, {
        caixa_id: caixaId,
        pagamentos: [{ forma_pagamento: "Dinheiro", valor: 10 }],
      });
    const comissoesParciais = await api(request, "get", `/comissoes?venda_id=${parcial.id}`);
    expect(comissoesParciais.lista.map((item) => item.valor_comissao_gerada).sort()).toEqual([
      0.81, 0.82,
    ]);

    // Inspeção visual da célula de recebimento, sem registrar novo pagamento.
    await page.goto("/pdv");
    await fecharTour(page);
    await page
      .getByPlaceholder("Digite o nome do produto, codigo de barras ou servico...", { exact: true })
      .fill(produtos[0].nome);
    await page
      .getByRole("option")
      .filter({ hasText: produtos[0].nome })
      .getByRole("button")
      .click();
    await page.getByRole("button", { name: "Registrar Recebimento", exact: true }).last().click();
    await expect(
      page.getByRole("heading", { name: "Registrar Recebimento", exact: true }),
    ).toBeVisible();
    await page.getByRole("combobox", { name: /^Caixa do recebimento/ }).click();
    await page
      .getByRole("option")
      .filter({ hasText: /^Caixa 1 ·/ })
      .click();
    await page
      .getByRole("button", { name: /Cart[aã]o.*cr[eé]dito/i })
      .first()
      .click();
    await expect(page.getByRole("combobox", { name: /^Operadora/ })).toBeVisible();
    await expect(page.getByRole("combobox", { name: /^Bandeira/ })).toBeVisible();
    await expect(page.getByLabel(/^NSU \/ número da transação/)).toBeVisible();
    await expect(page.getByRole("combobox", { name: /^Número de parcelas/ })).toBeVisible();
    await page.screenshot({
      path: testInfo.outputPath("pdv-recebimento-caixa-cartao-parcelas.png"),
      fullPage: true,
    });
  });
});
