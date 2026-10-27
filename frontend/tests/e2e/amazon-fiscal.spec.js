import { expect, test } from "@playwright/test";
import process from "node:process";
import { URL } from "node:url";

// Pedidos, documentos e autenticação sintéticos. Nenhuma API alcança produção.
const local = ["localhost", "127.0.0.1", "[::1]"].includes(
  new URL(process.env.E2E_BASE_URL || "http://localhost:5173").hostname,
);
const base = "/api/integracoes/ecommerceai/fiscal/manage";
const orderId = "999-1234567-1234567";
const hash = "a".repeat(64);
test.use({ channel: "chrome" });
test.skip(!local || !process.env.E2E_BASE_URL, "requer frontend local e APIs simuladas");

async function setup(page, { pending = false, historical = false, central = false } = {}) {
  const tenant = { id: "qa-amazon-fiscal", name: "Empresa Sintética QA", login_name: "qa" };
  const user = { id: 42001, name: "Operador QA", is_admin: true, role: { name: "admin" }, tenant };
  const state = {
    accounts: [],
    mappings: [],
    mutations: [],
    reads: [],
    detailGets: 0,
    changeRevision: false,
    pending,
    scopes: ["catalog:read"],
    order: {
      id: 42,
      account_id: 7,
      channel: "amazon",
      seller_id: "SELLER-SINTETICO-QA",
      external_order_id: orderId,
      source_revision: 3,
      payload_hash: hash,
      status: historical ? "blocked" : "ready",
      total: "39.90",
      recipient_name: "Cliente Sintético",
      blockers: historical
        ? [
            {
              code: "historical_order_requires_review",
              message: "Pedido anterior à ativação: revise o histórico.",
            },
          ]
        : [],
      xml_available: false,
      danfe_available: false,
      source: {
        recipient: {
          name: "Cliente Sintético",
          document: "52998224725",
          address: {
            street: "Rua de Teste",
            number: "10",
            city: "São Paulo",
            state: "SP",
            postal_code: "01001000",
          },
        },
        items: [
          {
            external_item_id: "ITEM-QA",
            seller_sku: "AMZ-Kit-QA",
            quantity: "1",
            unit_price: "39.90",
            gross_amount: "39.90",
            discount_amount: "0.00",
          },
        ],
        totals: { products: "39.90", discount: "0.00", freight: "0.00", invoice_total: "39.90" },
        buyer_paid_total: "39.90",
        payments: [{ fiscal_method: "17", amount: "39.90" }],
      },
      discount_audit: {
        policy: "source_discounts",
        extra_discount: "0.00",
        effective_discount: "0.00",
      },
    },
  };
  await page.addInitScript(
    ({ user, tenant }) => {
      globalThis.localStorage.setItem("access_token", "token-sintetico-sem-validade");
      globalThis.localStorage.setItem("user", JSON.stringify(user));
      globalThis.localStorage.setItem("selectedTenant", JSON.stringify(tenant));
      globalThis.localStorage.setItem("tour_visto_dashboard", "1");
    },
    { user, tenant },
  );
  await page.route(
    (url) => url.pathname.startsWith("/api/"),
    async (route) => {
      const request = route.request();
      const path = new URL(request.url()).pathname;
      const method = request.method();
      if (method === "GET") state.reads.push(path);
      if (method !== "GET") state.mutations.push({ path, body: request.postDataJSON() });
      if (path === "/api/integracoes/ecommerceai/status")
        return route.fulfill({
          json: {
            connected: !state.pending,
            connection: { account_name: "EcommerceAI QA", scopes: state.scopes },
            request: state.pending
              ? {
                  id: "qa-request",
                  status: "pending",
                  requested_scopes: [
                    "catalog:read",
                    "fiscal:prepare",
                    "fiscal:issue",
                    "fiscal:read",
                  ],
                  expires_at: "2099-01-01T00:00:00Z",
                }
              : null,
          },
        });
      if (path.endsWith("/requests/qa-request/approve")) {
        state.pending = false;
        state.scopes.push("fiscal:prepare", "fiscal:issue", "fiscal:read");
        return route.fulfill({ json: { ok: true } });
      }
      if (path === `${base}/accounts` || path === `${base}/accounts/7`) {
        if (method !== "GET") {
          const account = {
            id: 7,
            ...request.postDataJSON(),
            activated_at: request.postDataJSON().auto_issue_enabled ? "2026-10-27T12:00:00Z" : null,
          };
          state.accounts = [account];
          return route.fulfill({ json: account });
        }
        return route.fulfill({ json: { items: state.accounts } });
      }
      if (path === `${base}/products`)
        return route.fulfill({
          json: {
            items: [{ id: 42005, name: "Kit Sintético QA", sku: "KIT-QA", product_type: "kit" }],
          },
        });
      if (path === `${base}/mappings`) {
        if (method === "POST") {
          const mapping = {
            id: 1,
            ...request.postDataJSON(),
            product_name: "Kit Sintético QA",
            product_sku: "KIT-QA",
          };
          state.mappings.push(mapping);
          return route.fulfill({ json: mapping });
        }
        return route.fulfill({ json: { items: state.mappings } });
      }
      if (path === `${base}/orders`)
        return route.fulfill({ json: { items: [state.order], total: 1, page: 1, page_size: 25 } });
      if (path === `${base}/orders/42`) {
        state.detailGets += 1;
        if (state.changeRevision && state.detailGets > 1) state.order.source_revision += 1;
        return route.fulfill({ json: state.order });
      }
      if (path === `${base}/orders/42/emitir`) {
        Object.assign(state.order, {
          status: "authorized",
          numero: 76543,
          chave: "1".repeat(44),
          protocolo: "PROTOCOLO-QA",
          xml_available: true,
          danfe_available: true,
        });
        return route.fulfill({ json: state.order });
      }
      if (path === `${base}/orders/42/review`) {
        Object.assign(state.order, {
          status: "ready",
          blockers: [],
          historical_reviewed_at: "2026-10-27T12:00:00Z",
        });
        return route.fulfill({ json: state.order });
      }
      if (path === `${base}/orders/42/xml`)
        return route.fulfill({ contentType: "application/xml", body: "<documentoSinteticoQA/>" });
      if (path === "/api/nfe/lista")
        return route.fulfill({
          json: {
            notas: [
              {
                id: "fiscal-externa-42",
                fiscal_order_id: 42,
                numero: 76543,
                serie: 1,
                modelo: 55,
                tipo: "nfe",
                status: "autorizada",
                provedor: "intnfe",
                origem: "fiscal_externa",
                canal: "amazon",
                canal_label: "Amazon",
                numero_pedido_loja: orderId,
                data_emissao: "2026-10-27T12:00:00Z",
                valor: 39.9,
                cliente: { nome: "Cliente Sintético", cpf_cnpj: "52998224725" },
              },
            ],
            total: 1,
            canais: ["amazon"],
          },
        });
      const responses = {
        "/api/auth/me-multitenant": user,
        "/api/auth/my-tenants": { tenants: [tenant] },
        "/api/modulos/status": { modulos_ativos: ["fiscal", "integracoes"], plano: "basico" },
        "/api/usuarios/me/menu-favoritos": { items: [] },
        "/api/lembretes/pendentes": { total: 0, lembretes: [] },
      };
      return route.fulfill({ json: responses[path] || {} });
    },
  );
  if (central) {
    Object.assign(state.order, {
      status: "authorized",
      numero: 76543,
      chave: "1".repeat(44),
      xml_available: true,
      danfe_available: true,
    });
    await page.goto("/notas-fiscais/saida?busca=76543&abrir=1");
    await expect(page.getByRole("dialog", { name: `Pedido Amazon ${orderId}` })).toBeVisible();
    return state;
  }
  await page.goto("/configuracoes/integracoes?ecommerceai_request=qa-request");
  await expect(
    page.getByRole("heading", { name: "NF-e de pedidos Amazon", exact: true }),
  ).toBeVisible();
  return state;
}

async function review(page) {
  await page.getByRole("button", { name: `Ações do pedido ${orderId}` }).click();
  await page.getByRole("menuitem", { name: "Revisar pedido", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: `Pedido Amazon ${orderId}` });
  await expect(dialog.getByText("Cliente Sintético", { exact: true })).toBeVisible();
  return dialog;
}

test("aprovação fiscal, ativação e desconto dependem de escolhas explícitas e SKU exato", async ({
  page,
}) => {
  const state = await setup(page, { pending: true });
  const approve = page.getByRole("button", { name: "Aceitar e conectar", exact: true });
  await expect(approve).toBeDisabled();
  await page
    .getByText("Autorizo as permissões fiscais solicitadas para esta empresa", { exact: true })
    .click();
  await approve.click();
  await expect
    .poll(() => state.mutations[0])
    .toEqual({
      path: "/api/integracoes/ecommerceai/requests/qa-request/approve",
      body: { confirm_fiscal_scopes: true },
    });
  await page.getByRole("button", { name: "Cadastrar conta fiscal Amazon", exact: true }).click();
  let dialog = page.getByRole("dialog", { name: "Cadastrar conta fiscal Amazon" });
  await expect(
    dialog.getByLabel("Autorizo emissão automática de novos pedidos desta loja"),
  ).not.toBeChecked();
  await expect(dialog.getByRole("combobox", { name: "Política de descontos" })).toHaveValue(
    "Somente descontos explícitos do pedido",
  );
  await dialog.getByLabel("Seller ID da conta Amazon").fill("SELLER-SINTETICO-QA");
  await dialog.getByLabel("CNPJ do emitente CorePet").fill("11222333000181");
  await dialog.getByRole("button", { name: "Salvar configuração", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  expect(state.accounts[0].auto_issue_enabled).toBe(false);
  expect(state.accounts[0].discount_policy).toBe("source_discounts");
  expect(state.mutations[1].body).not.toHaveProperty("activated_at");
  await page.getByRole("button", { name: "Configurar", exact: true }).click();
  dialog = page.getByRole("dialog", { name: "Configurar conta Amazon" });
  await dialog.getByRole("combobox", { name: "Política de descontos" }).click();
  await dialog
    .getByRole("option", { name: "Ajustar total ao pagamento documentado", exact: true })
    .click();
  await dialog.getByRole("button", { name: "Salvar configuração", exact: true }).click();
  await expect(dialog.getByRole("alert")).toContainText("Confirme");
  expect(state.mutations.filter((entry) => entry.path.endsWith("/accounts/7"))).toHaveLength(0);
  await dialog
    .getByText("Autorizo ajustar o desconto ao pagamento documentado", { exact: true })
    .click();
  await dialog
    .getByText("Autorizo emissão automática de novos pedidos desta loja", { exact: true })
    .click();
  await dialog.getByRole("button", { name: "Salvar configuração", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  expect(state.accounts[0].activated_at).toBe("2026-10-27T12:00:00Z");
  await page.getByRole("button", { name: "Mapear SKUs", exact: true }).click();
  dialog = page.getByRole("dialog", { name: /Mapear SKUs Amazon/ });
  await dialog.getByLabel("SKU exato na Amazon").fill("AMZ-Kit-QA");
  await dialog.getByLabel("Buscar produto ou kit CorePet").fill("Kit Sintético");
  await dialog.getByRole("button", { name: "Buscar produtos", exact: true }).click();
  await dialog.getByRole("combobox", { name: "Produto ou kit CorePet" }).click();
  await dialog
    .getByRole("option", { name: "KIT-QA — Kit Sintético QA (kit)", exact: true })
    .click();
  await dialog.getByRole("button", { name: "Salvar vínculo", exact: true }).click();
  await expect.poll(() => state.mappings.length).toBe(1);
  expect(state.mappings[0]).toMatchObject({
    account_id: 7,
    seller_sku: "AMZ-Kit-QA",
    product_id: 42005,
  });
});

test("revisão confirma versão antes de emitir e autorização não afirma aceite Amazon", async ({
  page,
}) => {
  const state = await setup(page);
  const dialog = await review(page);
  await expect(dialog.getByText("AMZ-Kit-QA", { exact: true })).toBeVisible();
  await expect(dialog.getByText(/aceite pela Amazon separadamente/)).toBeVisible();
  expect(state.mutations).toHaveLength(0);
  await dialog.getByRole("button", { name: "Confirmar emissão da NF-e", exact: true }).click();
  expect(state.mutations).toHaveLength(0);
  await page
    .getByRole("dialog", { name: "Confirmar ação", exact: true })
    .getByRole("button", { name: "Confirmar", exact: true })
    .click();
  await expect
    .poll(() => state.mutations)
    .toEqual([
      {
        path: `${base}/orders/42/emitir`,
        body: { expected_revision: 3, expected_payload_hash: hash },
      },
    ]);
  await expect(dialog.getByText("Autorizada na SEFAZ", { exact: true })).toBeVisible();
  await expect(
    dialog.getByRole("button", { name: "Confirmar emissão da NF-e", exact: true }),
  ).toBeDisabled();
  const download = page.waitForEvent("download");
  await dialog.getByRole("button", { name: "Baixar XML autorizado", exact: true }).click();
  expect((await download).suggestedFilename()).toContain(".xml");
  expect(state.detailGets).toBe(2);
});

test("Central abre nota externa por link e oferece só detalhes, consulta e documentos", async ({
  page,
}) => {
  const state = await setup(page, { central: true });
  const dialog = page.getByRole("dialog", { name: `Pedido Amazon ${orderId}` });
  await expect(dialog.getByText("Cliente Sintético", { exact: true })).toBeVisible();
  await dialog.getByRole("button", { name: "Voltar", exact: true }).click();
  await page.getByRole("button", { name: "Ações da nota 76543", exact: true }).click();
  await expect(page.getByRole("menuitem")).toHaveText([
    "Ver detalhes",
    "Atualizar situação da NF",
    "Baixar DANFE",
    "Baixar XML",
  ]);
  const download = page.waitForEvent("download");
  await page.getByRole("menuitem", { name: "Baixar XML", exact: true }).click();
  expect((await download).suggestedFilename()).toContain(".xml");
  expect(state.reads).toContain(`${base}/orders/42/xml`);
  expect(
    state.reads.some((path) => path.includes("undefined") || path.includes("/vendas/42")),
  ).toBe(false);
});

test("pedido histórico exige revisão e versão nova interrompe emissão", async ({ page }) => {
  const state = await setup(page, { historical: true });
  const dialog = await review(page);
  const release = dialog.getByRole("button", {
    name: "Registrar revisão do pedido anterior",
    exact: true,
  });
  await expect(release).toBeDisabled();
  await expect(
    dialog.getByRole("button", { name: "Confirmar emissão da NF-e", exact: true }),
  ).toBeDisabled();
  await dialog
    .getByText("Revisei o histórico e confirmo que este pedido pode seguir para emissão", {
      exact: true,
    })
    .click();
  await release.click();
  await expect
    .poll(() => state.mutations)
    .toEqual([{ path: `${base}/orders/42/review`, body: { acknowledge_historical: true } }]);
  state.changeRevision = true;
  await dialog.getByRole("button", { name: "Confirmar emissão da NF-e", exact: true }).click();
  await page
    .getByRole("dialog", { name: "Confirmar ação", exact: true })
    .getByRole("button", { name: "Confirmar", exact: true })
    .click();
  await expect(dialog.getByRole("alert")).toContainText("O pedido foi atualizado");
  expect(state.mutations.filter((entry) => entry.path.endsWith("/emitir"))).toHaveLength(0);
});
