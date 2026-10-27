/* global window, document */
import { expect, test } from "@playwright/test";
import { URL } from "node:url";
import { writeFile } from "node:fs/promises";
import { ambienteBanhoTosa } from "./banho-tosa/ambiente.mjs";
import {
  criarContextoBanhoTosa,
  dataBrasilia,
  escrita,
  preencherMoeda,
  prepararNavegador,
  selecionarOpcao,
} from "./banho-tosa/fixtures.js";

const ambiente = ambienteBanhoTosa();
test.use({ channel: "chrome", trace: "off", actionTimeout: 15_000 });
let f;
let pacote;
let credito;
let apiContext;

function esperado(disponivel, reservado, usado, pagamento = "pendente") {
  return { disponivel, reservado, usado, pagamento };
}

async function anexarJson(info, nome, dados) {
  const path = info.outputPath(`${nome}.json`);
  await writeFile(path, JSON.stringify(dados, null, 2), "utf8");
  await info.attach(nome, { path, contentType: "application/json" });
}

async function abrirPacotes(page) {
  await page.goto(`${ambiente.baseURL}/banho-tosa/pacotes`);
  await expect(page.getByRole("button", { name: "Novo pacote", exact: true })).toBeVisible();
}

function linhaCredito(page) {
  return page
    .getByRole("button", { name: `Ações de ${pacote.nome} para ${f.pets[0].nome}`, exact: true })
    .locator("..");
}

async function criarAgendamentoUI(page, hora) {
  await page.goto(`${ambiente.baseURL}/banho-tosa/agenda`);
  await page.getByRole("button", { name: "Agendar", exact: true }).click();
  const modal = page.getByRole("dialog", { name: "Novo agendamento", exact: true });
  await selecionarOpcao(page, modal.locator("#bt-agenda-tutor"), f.tutor.codigo);
  await modal.getByRole("button").filter({ hasText: f.pets[0].nome }).click();
  await selecionarOpcao(page, modal.locator("#bt-agenda-servico"), f.banho.nome);
  await modal.locator("#bt-agenda-data").fill(dataBrasilia(1).split("-").reverse().join("/"));
  await modal.locator("#bt-agenda-hora").fill(hora);
  await selecionarOpcao(page, modal.locator("#bt-agenda-recurso"), f.recurso.nome);
  await expect(modal.locator("output")).toContainText("crédito(s) para este serviço");
  const agendamento = await escrita(page, "/banho-tosa/agendamentos", "POST", () =>
    modal.getByRole("button", { name: "Confirmar", exact: true }).click(),
  );
  await expect(modal).not.toBeVisible();
  return agendamento;
}

async function receberNoPDV(page, valor) {
  await page.getByRole("button", { name: "Registrar Recebimento", exact: true }).first().click();
  await expect(page.getByText("Selecione a forma de pagamento", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: f.forma.nome, exact: true }).click();
  await preencherMoeda(page.locator("#modal-pagamento-valor"), valor);
  await page.getByTestId("modal-pagamento-footer-adicionar").click();
  return escrita(page, `/vendas/${credito.venda_id}/finalizar`, "POST", () =>
    page.getByRole("button", { name: "Registrar Recebimento", exact: true }).last().click(),
  );
}

async function agendarAPI(pet, servico, deslocamento = 1, hora = "14:00") {
  return f.api("post", "/banho-tosa/agendamentos", {
    cliente_id: f.tutor.id,
    pet_id: pet.id,
    data_hora_inicio: `${dataBrasilia(deslocamento)}T${hora}:00`,
    recurso_id: f.recurso.id,
    observacoes: `${f.prefixo} automacao`,
    servicos: [
      {
        servico_id: servico.id,
        quantidade: "1",
        valor_unitario: String(servico.preco_base),
        desconto: "0",
      },
    ],
  });
}

test.describe("Banho e tosa — pacote de quatro banhos em DEV real", () => {
  test.skip(
    !ambiente,
    "Requer E2E_CREATE_TEST_IDENTITY=1; cria somente identidade exclusiva em DEV local.",
  );
  test.describe.configure({ mode: "serial" });
  test.setTimeout(120_000);

  test.beforeAll(async ({ playwright }) => {
    apiContext = await playwright.request.newContext();
    f = await criarContextoBanhoTosa(apiContext, ambiente);
  });
  test.afterAll(async () => {
    await apiContext?.dispose();
  });
  test.beforeEach(async ({ context }) => {
    await prepararNavegador(context, f);
  });
  test.afterEach(async ({ page, context }, info) => {
    if (!f) return;
    await anexarJson(info, "identificadores-sinteticos", {
      prefixo: f.prefixo,
      tenant_id: f.tenant.id,
      tutor_id: f.tutor.id,
      pet_id: f.pets[0].id,
      pacote_id: pacote?.id,
      credito_id: credito?.id,
      venda_id: credito?.venda_id,
      saldos_conferidos: f.evidencias,
    });
    if (!page.isClosed())
      await page.screenshot({ path: info.outputPath("resultado.png"), fullPage: true });
    await context.unrouteAll({ behavior: "ignoreErrors" });
  });

  test("cadastro e vinculo pela interface criam quatro banhos e uma cobranca pendente", async ({
    page,
  }) => {
    await abrirPacotes(page);
    await page.getByRole("button", { name: "Novo pacote", exact: true }).click();
    await page.locator("#bt-pacote-nome").fill(`${f.prefixo} Quatro banhos`);
    await selecionarOpcao(
      page,
      page.getByRole("combobox", { name: "Serviço incluído" }),
      f.banho.nome,
    );
    await page.getByLabel("Quantidade", { exact: false }).fill("4");
    await preencherMoeda(page.locator("#bt-pacote-preco"), 200);
    pacote = await escrita(page, "/banho-tosa/pacotes", "POST", () =>
      page.getByRole("button", { name: "Cadastrar pacote", exact: true }).click(),
    );
    expect(Number(pacote.servicos[0].quantidade_creditos)).toBe(4);
    await page.getByRole("button", { name: "Vincular pacote ao pet", exact: true }).click();
    await selecionarOpcao(page, page.locator("#bt-credito-pacote"), pacote.nome);
    await selecionarOpcao(page, page.locator("#bt-pacote-tutor"), f.tutor.codigo);
    await selecionarOpcao(page, page.locator("#bt-credito-pet"), f.pets[0].nome);
    credito = await escrita(page, "/banho-tosa/pacotes/creditos", "POST", () =>
      page
        .locator("form")
        .filter({ has: page.locator("#bt-credito-pet") })
        .getByRole("button", { name: "Vincular pacote ao pet", exact: true })
        .click(),
    );
    await expect(linhaCredito(page)).toContainText("Pagamento em aberto");
    credito = await f.saldo(credito.id);
    expect(credito.venda_id).toBeTruthy();
    await f.conferirSaldo(credito.id, esperado(4, 0, 0));
  });

  test("agendar reserva 4→3, cancelar devolve4, checkin confirma e cancelar atendimento estorna", async ({
    page,
  }) => {
    const primeiro = await criarAgendamentoUI(page, "09:00");
    expect(Number(primeiro.servicos[0].pacote_quantidade)).toBe(1);
    await f.conferirSaldo(credito.id, esperado(3, 1, 0));
    await page.getByRole("button", { name: "Cancelar", exact: true }).click();
    await escrita(page, `/banho-tosa/agendamentos/${primeiro.id}/status`, "PATCH", () =>
      page.getByRole("dialog").getByRole("button", { name: "Confirmar", exact: true }).click(),
    );
    await f.conferirSaldo(credito.id, esperado(4, 0, 0));
    const segundo = await criarAgendamentoUI(page, "10:00");
    const atendimento = await escrita(
      page,
      `/banho-tosa/agendamentos/${segundo.id}/check-in`,
      "POST",
      () => page.getByRole("button", { name: "Fazer check-in", exact: true }).click(),
    );
    await f.conferirSaldo(credito.id, esperado(3, 0, 1));
    await page.goto(`${ambiente.baseURL}/banho-tosa/fila`);
    await page
      .locator("article")
      .filter({ hasText: f.pets[0].nome })
      .getByRole("button", { name: "Abrir ficha", exact: true })
      .click();
    const ficha = page.getByRole("dialog", {
      name: "Ficha operacional do atendimento",
      exact: true,
    });
    await ficha.getByRole("button", { name: "Fechamento", exact: true }).click();
    await ficha
      .getByRole("button", { name: "Cancelar atendimento e retirar da fila", exact: true })
      .click();
    const confirmacao = page.locator('[data-modal-panel="corepet-dialog"]');
    await confirmacao.locator("#corepet-dialog-input").fill(`${f.prefixo} cancelamento de teste`);
    await escrita(
      page,
      `/banho-tosa/atendimentos/${atendimento.id}/cancelar-processo`,
      "POST",
      () => confirmacao.getByRole("button", { name: "Cancelar atendimento", exact: true }).click(),
    );
    await f.conferirSaldo(credito.id, esperado(4, 0, 0));
    expect((await f.saldo(credito.id)).venda_id).toBe(credito.venda_id);
  });

  test("outro pet e servico fora do pacote nao consomem os quatro banhos", async ({ page }) => {
    for (const [pet, servico, hora] of [
      [f.pets[1], f.banho, "13:00"],
      [f.pets[0], f.tosa, "14:00"],
    ]) {
      const agendamento = await agendarAPI(pet, servico, 1, hora);
      expect(Number(agendamento.servicos[0].pacote_quantidade)).toBe(0);
      await f.api("patch", `/banho-tosa/agendamentos/${agendamento.id}/status`, {
        status: "cancelado",
      });
    }
    await f.conferirSaldo(credito.id, esperado(4, 0, 0));
    await abrirPacotes(page);
    await expect(linhaCredito(page)).toContainText("4 disponíveis");
  });

  test("quatro reservas esgotam a disponibilidade e a quinta fica avulsa", async ({ page }) => {
    const agendamentos = [];
    for (let dia = 1; dia <= 5; dia += 1)
      agendamentos.push(await agendarAPI(f.pets[0], f.banho, dia));
    expect(agendamentos.map((item) => Number(item.servicos[0].pacote_quantidade))).toEqual([
      1, 1, 1, 1, 0,
    ]);
    await f.conferirSaldo(credito.id, esperado(0, 4, 0));
    await abrirPacotes(page);
    await expect(linhaCredito(page)).toContainText("0 disponíveis · 4 reservados");
    for (const item of agendamentos)
      await f.api("patch", `/banho-tosa/agendamentos/${item.id}/status`, { status: "cancelado" });
    await f.conferirSaldo(credito.id, esperado(4, 0, 0));
  });
  test("PDV recebe parcial e integral sem alterar quatro creditos", async ({
    page,
    context,
  }, info) => {
    await abrirPacotes(page);
    // Desliga a emulação de foco padrão do Playwright; a troca real de abas
    // passa a produzir eventos nativos. Não dispara eventos falsos.
    const sessaoPrincipal = await context.newCDPSession(page);
    await sessaoPrincipal.send("Emulation.setFocusEmulationEnabled", { enabled: false });
    await page.bringToFront();
    const consultasAoRetornar = [];
    page.on("response", async (response) => {
      if (new URL(response.url()).pathname.endsWith("/banho-tosa/pacotes/creditos")) {
        try {
          const lista = await response.json();
          const item = lista.find((registro) => registro.id === credito.id);
          consultasAoRetornar.push({
            status: response.status(),
            pagamento: item?.status_pagamento,
            recebido: item?.valor_pago,
          });
        } catch {
          consultasAoRetornar.push({ status: response.status(), leitura: "indisponivel" });
        }
      }
    });
    await page.evaluate(() => {
      window.__qaFocoPacotes = [];
      const registrar = (tipo) =>
        window.__qaFocoPacotes.push({
          tipo,
          visibilidade: document.visibilityState,
          foco: document.hasFocus(),
        });
      registrar("inicial");
      window.addEventListener("focus", () => registrar("focus"));
      window.addEventListener("blur", () => registrar("blur"));
      document.addEventListener("visibilitychange", () => registrar("visibilitychange"));
    });
    await linhaCredito(page)
      .getByRole("button", { name: /^Ações de/ })
      .click();
    const popup = context.waitForEvent("page");
    await page.getByRole("menuitem", { name: "Abrir venda no PDV", exact: true }).click();
    const pdv = await popup;
    await pdv.waitForLoadState("domcontentloaded");
    const sessaoPdv = await context.newCDPSession(pdv);
    await sessaoPdv.send("Emulation.setFocusEmulationEnabled", { enabled: false });
    await pdv.bringToFront();
    await expect(pdv).toHaveURL(new RegExp(`venda_id=${credito.venda_id}`));
    const alteracoesDaVenda = [];
    pdv.on("request", (request) => {
      if (
        request.method() === "PUT" &&
        new URL(request.url()).pathname.replace(/^\/api/, "") === `/vendas/${credito.venda_id}`
      )
        alteracoesDaVenda.push(request.method());
    });
    await receberNoPDV(pdv, 80);
    await f.conferirSaldo(credito.id, esperado(4, 0, 0, "parcial"));
    const parcial = await f.saldo(credito.id);
    expect(Number(parcial.valor_pago)).toBe(80);
    expect(Number(parcial.valor_restante)).toBe(120);
    alteracoesDaVenda.length = 0;
    await pdv.goto(`${ambiente.baseURL}/pdv?venda_id=${credito.venda_id}`);
    await receberNoPDV(pdv, 120);
    await f.conferirSaldo(credito.id, esperado(4, 0, 0, "pago"));
    const pago = await f.saldo(credito.id);
    expect(Number(pago.valor_pago)).toBe(200);
    expect(Number(pago.valor_restante)).toBe(0);
    expect(
      alteracoesDaVenda,
      "Novo recebimento deve preservar o snapshot da venda parcial sem PUT.",
    ).toEqual([]);
    await pdv.close();
    await page.bringToFront();
    try {
      await expect(linhaCredito(page)).toContainText("Recebido: R$ 200,00");
    } finally {
      const foco = await page.evaluate(() => ({
        eventos: window.__qaFocoPacotes,
        atual: { visibilidade: document.visibilityState, foco: document.hasFocus() },
      }));
      await anexarJson(info, "diagnostico-retorno-pdv", { foco, consultas: consultasAoRetornar });
    }
  });
});
