import { expect, test } from "@playwright/test";
import process from "node:process";
import { URL } from "node:url";

// Exercita o PDV real com API em memória, sem credenciais nem banco de dados.
const local = ["localhost", "127.0.0.1", "[::1]"].includes(
  new URL(process.env.E2E_BASE_URL || "http://localhost:5173").hostname,
);
const vendaId = 42002;
const apiVenda = `/api/vendas/${vendaId}`;
const apiStatus = `/api/nfe/vendas/${vendaId}/status`;

test.use({ channel: "chrome" });
test.skip(
  !local || !process.env.E2E_BASE_URL,
  "requer E2E_BASE_URL explícita de frontend local; todas as APIs são simuladas",
);

async function prepararApi(
  page,
  { statusFiscal = "cancelada", statusVenda = "pago_nf", resultadoFiscal } = {},
) {
  const tenant = { id: "tenant-sintetico-qa", name: "Loja Sintética QA", login_name: "qa" };
  const user = { id: 42002, name: "Usuário QA", is_admin: true, role: { name: "admin" }, tenant };
  const estado = {
    statusFiscal,
    falharConsulta: false,
    consultasFiscais: 0,
    envios: [],
    avisos: [],
    venda: {
      id: vendaId,
      numero_venda: "QA-NOTA-CANCELADA",
      data_venda: "2026-10-20T12:00:00",
      status: statusVenda,
      cliente_id: null,
      itens: [
        {
          id: 42003,
          produto_id: 42004,
          produto_nome: "Produto Sintético QA",
          produto_codigo: "QA-42004",
          tipo: "produto",
          quantidade: 1,
          preco_unitario: 39.9,
          subtotal: 39.9,
        },
      ],
      subtotal: 39.9,
      total: 39.9,
      desconto_valor: 0,
      desconto_percentual: 0,
      observacoes: "Venda sintética sem dados reais",
      tem_entrega: false,
      nfe_tipo: "nfce",
      nfe_modelo: "65",
      nfe_numero: 18574,
      nfe_status: "autorizada",
      nfe_provider: "intnfe",
      nfe_correlation_id: "nota-sintetica-qa",
      nfe_chave: "0".repeat(44),
    },
  };
  await page.addInitScript(
    ({ user, tenant }) => {
      globalThis.localStorage.setItem("access_token", "token-sintetico-sem-validade");
      globalThis.localStorage.setItem("user", JSON.stringify(user));
      globalThis.localStorage.setItem("selectedTenant", JSON.stringify(tenant));
      globalThis.localStorage.setItem("tour_visto_pdv", "1");
      globalThis.localStorage.setItem("tour_visto_dashboard", "1");
    },
    { user, tenant },
  );
  await page.route(
    (url) => url.pathname.startsWith("/api/"),
    async (route) => {
      const request = route.request();
      const path = new URL(request.url()).pathname;
      if (path === apiStatus) {
        estado.consultasFiscais += 1;
        if (estado.falharConsulta) {
          return route.fulfill({
            status: 503,
            json: { detail: "Emissor temporariamente indisponível." },
          });
        }
        estado.venda.nfe_status = estado.statusFiscal;
        if (estado.statusFiscal === "cancelada" && estado.venda.status === "pago_nf") {
          estado.venda.status = "finalizada";
        }
        if (estado.statusFiscal === "cancelada") {
          estado.venda.nfe_cancelamento_status = "confirmado";
          estado.venda.pendencia_fiscal_cancelamento = false;
        }
        return route.fulfill({
          json: { success: true, situacao: estado.statusFiscal, provedor: "intnfe" },
        });
      }
      if (path === apiVenda) return route.fulfill({ json: estado.venda });
      if (path === `${apiVenda}/pagamentos`) {
        return route.fulfill({ json: { pagamentos: [], total_pago: 39.9, saldo_devedor: 0 } });
      }
      if (path === `${apiVenda}/cancelar` && request.method() === "POST") {
        estado.envios.push({ path, payload: request.postDataJSON() });
        estado.venda.status = "cancelada";
        if (estado.venda.nfe_status !== "cancelada") {
          estado.venda.nfe_cancelamento_status ||= "pendente";
          estado.venda.pendencia_fiscal_cancelamento = true;
        }
        return route.fulfill({ json: estado.venda });
      }
      if (path === `/api/nfe/vendas/${vendaId}/cancelar` && request.method() === "POST") {
        const resultado = resultadoFiscal || {
          cancelamento_status: "solicitado",
          cancelamento_solicitado: true,
          success: false,
        };
        estado.venda.nfe_cancelamento_status = resultado.cancelamento_status;
        estado.venda.nfe_cancelamento_codigo = resultado.cancelamento_codigo;
        estado.venda.nfe_cancelamento_motivo = resultado.cancelamento_motivo;
        estado.venda.pendencia_fiscal_cancelamento = true;
        return route.fulfill({ json: { ...resultado, situacao: estado.venda.nfe_status } });
      }
      if (path === "/api/nfe/lista") {
        return route.fulfill({
          json: {
            notas: [
              {
                ...estado.venda,
                venda_id: vendaId,
                venda_status: estado.venda.status,
                provedor: "intnfe",
                status: estado.venda.nfe_status,
                modelo: 65,
                tipo: "nfce",
                numero: 18574,
                serie: 1,
                valor: 39.9,
              },
            ],
            total: 1,
            canais: [],
          },
        });
      }
      if (path === "/api/nfe/atualizar-lista")
        return route.fulfill({ json: { mensagem: "Notas atualizadas" } });
      if (path === `${apiVenda}/reabrir`) {
        estado.envios.push({ path, payload: request.postDataJSON() });
        return route.fulfill({ status: 500, json: { detail: "Não deve reabrir para cancelar." } });
      }
      const respostas = {
        "/api/auth/me-multitenant": user,
        "/api/auth/my-tenants": { tenants: [tenant] },
        "/api/modulos/status": { modulos_ativos: ["fiscal"], plano: "basico" },
        "/api/usuarios/me/menu-favoritos": { items: [] },
        "/api/lembretes/pendentes": { total: 0, lembretes: [] },
        "/api/clientes/": { items: [], total: 0 },
        "/api/funcionarios": [],
        "/api/vendas": { vendas: [estado.venda], total: 1 },
        "/api/caixa/aberto": { id: 42005, status: "aberto", saldo_inicial: 0 },
        "/api/comissoes/configuracoes/funcionarios": { data: [] },
        "/api/empresa/config/pdv": { vendedor_obrigatorio_pdv: false },
      };
      // Nenhuma chamada da aplicação alcança um backend ou serviço fiscal real.
      return route.fulfill({ json: respostas[path] || {} });
    },
  );
  page.on("dialog", (dialog) => {
    estado.avisos.push(dialog.message());
    dialog.accept();
  });
  return estado;
}

test.describe("PDV — cancelamento após nota fiscal cancelada", () => {
  test("atualiza a nota e cancela a venda diretamente com confirmação e justificativa", async ({
    page,
  }) => {
    const estado = await prepararApi(page);
    await page.goto(`/pdv?venda_id=${vendaId}`);
    await expect(page.getByText("NFC-e nº 18574 — Cancelada", { exact: true })).toBeVisible();
    await expect(page.getByText("NFC-e nº 18574 — Autorizada", { exact: true })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Imprimir NFC-e", exact: true })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Cancelar venda", exact: true })).toBeVisible();
    expect(estado.consultasFiscais).toBeGreaterThan(0);

    await page.getByRole("button", { name: "Cancelar venda", exact: true }).click();
    const confirmacao = page.getByRole("dialog", { name: "Cancelar venda?" });
    await expect(confirmacao).toBeVisible();
    await confirmacao.getByRole("button", { name: "Cancelar venda", exact: true }).click();
    const justificativa = page.getByRole("dialog", { name: "Justificativa do cancelamento" });
    await expect(justificativa).toBeVisible();
    await justificativa.getByLabel("Justificativa", { exact: true }).fill("curto");
    await justificativa.getByRole("button", { name: "Continuar", exact: true }).click();
    await expect(
      justificativa.getByText("Digite pelo menos 10 caracteres.", { exact: true }),
    ).toBeVisible();
    expect(estado.envios).toHaveLength(0);
    await justificativa
      .getByLabel("Justificativa", { exact: true })
      .fill("Nota cancelada e venda desfeita pelo cliente.");
    await justificativa.getByRole("button", { name: "Continuar", exact: true }).click();
    await expect
      .poll(() => estado.envios)
      .toEqual([
        {
          path: `${apiVenda}/cancelar`,
          payload: { motivo: "Nota cancelada e venda desfeita pelo cliente." },
        },
      ]);
    await expect(page.getByRole("button", { name: "Cancelar venda", exact: true })).toHaveCount(0);
    expect(estado.venda.status).toBe("cancelada");
  });

  test("cancela a venda com nota autorizada e mantém pendência até confirmação fiscal", async ({
    page,
  }) => {
    const estado = await prepararApi(page, { statusFiscal: "autorizada" });
    await page.goto(`/pdv?venda_id=${vendaId}`);
    await expect(page.getByText("NFC-e nº 18574 — Autorizada", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Cancelar venda", exact: true }).click();
    const confirmacao = page.getByRole("dialog", { name: "Cancelar venda?" });
    await expect(confirmacao.getByText(/a nota fiscal continuará válida/)).toBeVisible();
    await confirmacao.getByRole("button", { name: "Cancelar venda", exact: true }).click();
    const justificativa = page.getByRole("dialog", { name: "Justificativa do cancelamento" });
    await justificativa
      .getByLabel("Justificativa", { exact: true })
      .fill("Venda cancelada sem cancelar a nota ainda.");
    await justificativa.getByRole("button", { name: "Continuar", exact: true }).click();
    await expect(page.getByRole("alert").filter({ hasText: "Nota a cancelar" })).toBeVisible();
    await expect(page.getByText("NFC-e nº 18574 — Autorizada", { exact: true })).toBeVisible();
    expect(estado.venda.status).toBe("cancelada");
    expect(estado.venda.nfe_status).toBe("autorizada");
    estado.statusFiscal = "cancelada";
    const consultasAntes = estado.consultasFiscais;
    await page.evaluate(() => globalThis.dispatchEvent(new globalThis.Event("focus")));
    await expect.poll(() => estado.consultasFiscais).toBeGreaterThan(consultasAntes);
    await expect(page.getByText("NFC-e nº 18574 — Cancelada", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Cancelar venda", exact: true })).toHaveCount(0);
    await expect(page.getByRole("alert").filter({ hasText: "Nota a cancelar" })).toHaveCount(0);
    expect(estado.venda.status).toBe("cancelada");
    expect(estado.envios).toHaveLength(1);
  });

  test("não libera cancelar quando a venda já possui devolução", async ({ page }) => {
    await prepararApi(page, { statusVenda: "finalizada_devolucao_parcial" });
    await page.goto(`/pdv?venda_id=${vendaId}`);
    await expect(page.getByText("NFC-e nº 18574 — Cancelada", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Cancelar venda", exact: true })).toHaveCount(0);
  });

  test("consulta indisponível preserva a última situação e permite tentar novamente", async ({
    page,
  }) => {
    const estado = await prepararApi(page);
    estado.falharConsulta = true;
    await page.goto(`/pdv?venda_id=${vendaId}`);
    await expect(
      page.getByRole("alert").filter({ hasText: "Não foi possível consultar o emissor" }),
    ).toBeVisible();
    await expect(page.getByText("NFC-e nº 18574 — Autorizada", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Cancelar venda", exact: true })).toBeVisible();
    estado.falharConsulta = false;
    await page.getByRole("button", { name: "Atualizar situação", exact: true }).click();
    await expect(page.getByText("NFC-e nº 18574 — Cancelada", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Cancelar venda", exact: true })).toBeVisible();
    await expect(
      page.getByRole("alert").filter({ hasText: "Não foi possível consultar o emissor" }),
    ).toHaveCount(0);
  });

  test("Central NF mostra recusa 501 legível e preserva pendência na venda cancelada", async ({
    page,
  }) => {
    const estado = await prepararApi(page, {
      statusFiscal: "autorizada",
      statusVenda: "cancelada",
      resultadoFiscal: {
        success: false,
        cancelamento_status: "recusado",
        cancelamento_codigo: "501",
        cancelamento_motivo: { mensagem: "Prazo de cancelamento excedido" },
        cancelamento_solicitado: false,
      },
    });
    await page.goto("/notas-fiscais/saida");
    await page.getByTitle("Cancelar NF-e", { exact: true }).click();
    const modal = page.getByRole("dialog", { name: "Cancelar Nota Fiscal" });
    await modal.getByLabel(/Justificativa/).fill("Nota a cancelar após desfazer venda.");
    await modal.getByRole("button", { name: "Confirmar Cancelamento" }).click();
    await expect(modal.getByRole("alert")).toContainText("Código 501");
    await expect(modal.getByRole("alert")).toContainText("Prazo de cancelamento excedido");
    const aviso = page
      .getByRole("status")
      .filter({ hasText: "O cancelamento da nota foi recusado" });
    await expect(aviso).toContainText("Código 501");
    await expect(aviso).not.toContainText(/object Object|com sucesso/);
    expect(estado.venda.nfe_status).toBe("autorizada");
    await modal.getByRole("button", { name: "Voltar", exact: true }).click();
    await page.goto(`/pdv?venda_id=${vendaId}`);
    await expect(page.getByRole("alert").filter({ hasText: "Nota a cancelar" })).toContainText(
      "Código 501",
    );
    await expect(page.getByText("NFC-e nº 18574 — Autorizada", { exact: true })).toBeVisible();
  });

  test("pedido aceito mostra cancelamento em andamento até confirmação fiscal", async ({
    page,
  }) => {
    const estado = await prepararApi(page, {
      statusFiscal: "autorizada",
      statusVenda: "cancelada",
    });
    await page.goto("/notas-fiscais/saida");
    await page.getByTitle("Cancelar NF-e", { exact: true }).click();
    const modal = page.getByRole("dialog", { name: "Cancelar Nota Fiscal" });
    await modal.getByLabel(/Justificativa/).fill("Nota a cancelar após desfazer venda.");
    await modal.getByRole("button", { name: "Confirmar Cancelamento" }).click();
    await expect(modal).toHaveCount(0);
    await expect(
      page.getByText("Cancelamento da nota em andamento", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("status").filter({ hasText: "Cancelamento da nota em andamento" }),
    ).toBeVisible();
    expect(estado.venda.nfe_status).toBe("autorizada");
    estado.statusFiscal = "cancelada";
    await page.getByTitle("Forçar reconciliação desta NF", { exact: true }).click();
    await expect(page.getByText("Cancelamento da nota em andamento", { exact: true })).toHaveCount(
      0,
    );
    expect(estado.venda.nfe_status).toBe("cancelada");
    expect(estado.venda.status).toBe("cancelada");
  });
});
