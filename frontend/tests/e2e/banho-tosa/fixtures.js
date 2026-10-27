/* global localStorage */
import { randomUUID } from "node:crypto";
import { URL } from "node:url";
import { expect } from "@playwright/test";

export function dataBrasilia(deslocamento = 0) {
  const partes = Object.fromEntries(
    new Intl.DateTimeFormat("en", {
      timeZone: "America/Sao_Paulo",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    })
      .formatToParts()
      .map((item) => [item.type, item.value]),
  );
  const data = new Date(`${partes.year}-${partes.month}-${partes.day}T12:00:00Z`);
  data.setUTCDate(data.getUTCDate() + deslocamento);
  return data.toISOString().slice(0, 10);
}

export async function criarContextoBanhoTosa(request, ambiente) {
  const prefixo = `QA BT ${randomUUID().slice(0, 8)}`;
  const evidencias = [];
  let sessao;
  async function api(metodo, caminho, data) {
    if (!caminho.startsWith("/") || caminho.startsWith("//"))
      throw new Error("Caminho de API invalido.");
    let destino = new URL(caminho, ambiente.apiURL);
    for (let tentativa = 0; tentativa < 3; tentativa += 1) {
      if (destino.origin !== ambiente.apiURL) throw new Error("Redirecionamento remoto proibido.");
      let resposta;
      try {
        resposta = await request[metodo](destino.href, {
          headers: sessao ? { Authorization: `Bearer ${sessao.access_token}` } : {},
          data,
          maxRedirects: 0,
        });
      } catch {
        throw new Error(
          `API DEV indisponivel: ${metodo.toUpperCase()} ${caminho}. Detalhes de rede redigidos.`,
        );
      }
      if ([307, 308].includes(resposta.status())) {
        destino = new URL(resposta.headers().location, destino);
        continue;
      }
      // Nunca inclui payload de autenticacao ou tokens em erros/relatorios.
      expect(
        resposta.ok(),
        `${metodo.toUpperCase()} ${caminho}: HTTP ${resposta.status()}`,
      ).toBeTruthy();
      return resposta.status() === 204 ? null : resposta.json();
    }
    throw new Error("A API local excedeu o limite de redirecionamentos.");
  }
  // A rota detalhada e bloqueada em producao/staging. Recusa ate tunel local protegido.
  const health = await request.get(`${ambiente.apiURL}/health/detailed`, { maxRedirects: 0 });
  expect(health.status(), "Backend deve permitir health DEV sem credenciais operacionais.").toBe(
    200,
  );
  expect((await health.json()).checks?.database?.status).toBe("healthy");
  const acesso = `${prefixo.toLowerCase().replaceAll(" ", "-")}`;
  const cadastro = await api("post", "/auth/register", {
    email: `${acesso}@example.com`,
    password: `Qa!${randomUUID()}9`,
    nome: `${prefixo} Operador`,
    nome_loja: `${prefixo} DEV exclusivo`,
    nome_acesso: acesso,
    plan: "grooming-gestao",
    organization_type: "grooming",
    accepted_terms: true,
    accepted_privacy: true,
  });
  expect(
    cadastro.access_token,
    "DEV deve permitir criar identidade sintetica sem envio de email.",
  ).toBeTruthy();
  const tenant = cadastro.tenants.find((item) => item.name === `${prefixo} DEV exclusivo`);
  expect(
    tenant,
    "Selecionar somente a empresa criada por esta execucao, nunca a primeira disponivel.",
  ).toBeTruthy();
  sessao = cadastro;
  sessao = await api("post", "/auth/select-tenant", { tenant_id: tenant.id });
  const user = await api("get", "/auth/me-multitenant");
  expect(String(user.tenant.id)).toBe(String(tenant.id));
  const tutor = await api("post", "/clientes/", {
    nome: `${prefixo} Tutor`,
    tipo_pessoa: "PF",
    is_cliente: true,
    celular: "11955550001",
    ativo: true,
  });
  const pets = [];
  for (const nome of ["Amora", "Pipoca"])
    pets.push(
      await api("post", "/pets", {
        nome: `${prefixo} ${nome}`,
        especie: "Canina",
        porte: "pequeno",
        cliente_id: tutor.id,
      }),
    );
  const banho = await api("post", "/banho-tosa/servicos", {
    nome: `${prefixo} Banho`,
    preco_base: "50",
    duracao_padrao_minutos: 30,
    permite_pacote: true,
  });
  const tosa = await api("post", "/banho-tosa/servicos", {
    nome: `${prefixo} Tosa`,
    categoria: "tosa",
    preco_base: "80",
    duracao_padrao_minutos: 30,
    requer_tosa: true,
  });
  const recurso = await api("post", "/banho-tosa/recursos", {
    nome: `${prefixo} Box`,
    tipo: "box",
    capacidade_simultanea: 2,
  });
  await api("patch", "/banho-tosa/configuracao", {
    horario_inicio: "08:00",
    horario_fim: "18:00",
    dias_funcionamento: ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"],
    lembretes_agendamento_ativos: false,
  });
  const caixa = await api("post", "/caixas/abrir", {
    valor_abertura: 0,
    observacoes_abertura: `${prefixo} caixa sintetico`,
  });
  const forma = await api("post", "/financeiro/formas-pagamento", {
    nome: `${prefixo} Dinheiro`,
    tipo: "dinheiro",
    gera_contas_receber: true,
  });
  async function saldo(creditoId) {
    const lista = await api("get", `/banho-tosa/pacotes/creditos?pet_id=${pets[0].id}&limit=500`);
    const credito = lista.find((item) => item.id === creditoId);
    expect(credito).toBeTruthy();
    return credito;
  }
  async function conferirSaldo(creditoId, esperado) {
    let observado;
    await expect
      .poll(async () => {
        const credito = await saldo(creditoId);
        observado = {
          disponivel: Number(credito.saldo_creditos),
          reservado: Number(credito.creditos_reservados),
          usado: Number(credito.creditos_usados),
          pagamento: credito.status_pagamento,
        };
        return observado;
      })
      .toEqual(esperado);
    evidencias.push({
      credito_id: creditoId,
      esperado,
      observado,
      conferido_em: new Date().toISOString(),
    });
  }
  return {
    ambiente,
    prefixo,
    api,
    sessao,
    user,
    tenant,
    tutor,
    pets,
    banho,
    tosa,
    recurso,
    caixa,
    forma,
    saldo,
    conferirSaldo,
    evidencias,
  };
}

export async function prepararNavegador(context, fixture) {
  const { ambiente, sessao, user } = fixture;
  const origens = new Set([ambiente.baseURL, ambiente.apiURL]);
  await context.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (["http:", "https:"].includes(url.protocol) && !origens.has(url.origin))
      return route.abort();
    return route.continue();
  });
  // Pass-through real para o backend DEV explicito; ignora qualquer proxy Vite mal configurado.
  await context.route(`${ambiente.baseURL}/api/**`, async (route) => {
    const origem = new URL(route.request().url());
    const destino = new URL(origem.pathname.replace(/^\/api/, "") + origem.search, ambiente.apiURL);
    try {
      const resposta = await route.fetch({ url: destino.href, maxRedirects: 0 });
      const location = resposta.headers().location;
      if (location && new URL(location, destino).origin !== ambiente.apiURL)
        throw new Error("Redirecionamento remoto proibido.");
      await route.fulfill({ response: resposta });
    } catch {
      throw new Error(
        `Falha no encaminhamento DEV ${destino.pathname}. Detalhes de rede redigidos.`,
      );
    }
  });
  await context.addInitScript(
    ({ sessao, user }) => {
      localStorage.setItem("access_token", sessao.access_token);
      localStorage.setItem("refresh_token", sessao.refresh_token);
      localStorage.setItem("user", JSON.stringify(user));
      localStorage.setItem("selectedTenant", JSON.stringify(user.tenant));
      for (const tela of ["pdv", "pessoas", "produtos", "pets", "banho_tosa"])
        localStorage.setItem(`tour_visto_${tela}`, "1");
    },
    { sessao, user },
  );
}

export async function selecionarOpcao(page, campo, texto) {
  await campo.fill(texto);
  const opcao = page.getByRole("option").filter({ hasText: texto });
  await expect(opcao).toHaveCount(1);
  await opcao.click();
}

export async function preencherMoeda(campo, valor) {
  await campo.click();
  await campo.press("Control+A");
  await campo.press("Backspace");
  await campo.pressSequentially(String(Math.round(valor * 100)));
}

export async function escrita(page, caminho, metodo, executar) {
  const resposta = page.waitForResponse(
    (res) =>
      new URL(res.url()).pathname.replace(/^\/api/, "") === caminho &&
      res.request().method() === metodo,
  );
  await executar();
  const res = await resposta;
  expect(res.ok(), `${metodo} ${caminho}: HTTP ${res.status()}`).toBeTruthy();
  return res.json();
}
