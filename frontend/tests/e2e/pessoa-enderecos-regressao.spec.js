import { expect, test } from "@playwright/test";
import { URL } from "node:url";

// Navegador real com API em memória: não requer login nem modifica nenhum banco.
// O servidor precisa servir o frontend atual em uma URL local (Vite ou homolog).
const local = ["localhost", "127.0.0.1", "[::1]"].includes(
  new URL(process.env.E2E_BASE_URL || "http://localhost:5173").hostname,
);
const pessoaId = 42001;
const apiPessoa = `/api/clientes/${pessoaId}`;
const camposEndereco = [
  "cep",
  "endereco",
  "numero",
  "complemento",
  "bairro",
  "cidade",
  "estado",
  "codigo_municipio",
];
const principal = {
  cep: "01001-000",
  endereco: "Rua Principal QA",
  numero: "42",
  complemento: "Sala QA",
  bairro: "Centro QA",
  cidade: "São Paulo",
  estado: "SP",
  codigo_municipio: "3550308",
};
const adicional = {
  tipo: "entrega",
  apelido: "Entrega QA",
  ...principal,
  endereco: "Rua Entrega QA",
  numero: "84",
};

test.use({ channel: "chrome" });
test.skip(
  !local || !process.env.E2E_BASE_URL,
  "requer E2E_BASE_URL explícita de um frontend local; não requer credenciais",
);

async function prepararApi(page, dados = {}) {
  const tenant = { id: "tenant-sintetico-qa", name: "Loja Sintética QA", login_name: "qa" };
  const user = { id: 42001, name: "Usuário QA", role: { name: "admin" }, tenant };
  const estado = {
    pessoa: {
      id: pessoaId,
      codigo: "QA-ENDERECO",
      nome: "Pessoa Sintética QA",
      tipo_pessoa: "PF",
      is_cliente: false,
      is_fornecedor: true,
      is_veterinario: false,
      is_funcionario: false,
      origem_cliente: "manual",
      origem_tenant_id: tenant.id,
      celular: "11999999999",
      celular_whatsapp: true,
      email: "qa@example.invalid",
      observacoes: "Observação persistida QA",
      contatos_adicionais: [],
      alertas_pdv: [],
      enderecos_adicionais: [],
      app_access_profiles: [],
      created_at: "2026-10-19T12:00:00Z",
      criado_por_nome: user.name,
      ...Object.fromEntries(camposEndereco.map((campo) => [campo, null])),
      ...dados,
    },
    envios: [],
    criacoes: [],
    falharProximo: false,
    // Permite segurar uma resposta e verificar o modal enquanto a API está pendente.
    aguardarResposta: null,
  };
  await page.addInitScript(
    ({ user, tenant }) => {
      localStorage.setItem("access_token", "token-sintetico-sem-validade");
      localStorage.setItem("user", JSON.stringify(user));
      localStorage.setItem("selectedTenant", JSON.stringify(tenant));
    },
    { user, tenant },
  );
  await page.route(
    (url) => url.pathname.startsWith("/api/"),
    async (route) => {
      const request = route.request();
      const path = new URL(request.url()).pathname;
      if (path === apiPessoa && request.method() === "PUT") {
        const payload = request.postDataJSON();
        estado.envios.push(payload);
        if (estado.aguardarResposta) await estado.aguardarResposta;
        if (estado.falharProximo) {
          estado.falharProximo = false;
          return route.fulfill({
            status: 503,
            json: { detail: "Falha simulada ao salvar endereço." },
          });
        }
        // Simula a resposta completa do backend, inclusive campos não alterados.
        estado.pessoa = { ...estado.pessoa, ...payload };
        return route.fulfill({ json: estado.pessoa });
      }
      if (path === apiPessoa) return route.fulfill({ json: estado.pessoa });
      if (path === "/api/clientes/" && request.method() === "POST") {
        estado.criacoes.push(request.postDataJSON());
        estado.pessoa = { ...estado.pessoa, ...request.postDataJSON() };
        return route.fulfill({ status: 201, json: estado.pessoa });
      }
      const respostas = {
        "/api/auth/me-multitenant": user,
        "/api/auth/my-tenants": { tenants: [tenant] },
        "/api/modulos/status": { modulos_ativos: [], plano: "basico" },
        "/api/usuarios/me/menu-favoritos": { items: [] },
        "/api/lembretes/pendentes": { total: 0, lembretes: [] },
        "/api/clientes/": { items: [], total: 0 },
        [`${apiPessoa}/historico-alteracoes`]: { items: [] },
        [`/api/financeiro/cliente/${pessoaId}/resumo`]: { resumo: {} },
      };
      // Nenhuma requisição /api atravessa para um backend ou usa credenciais reais.
      return route.fulfill({ json: respostas[path] || {} });
    },
  );
  await page.route("https://viacep.com.br/ws/01001000/json/", (route) =>
    route.fulfill({
      json: {
        logradouro: principal.endereco,
        bairro: principal.bairro,
        localidade: principal.cidade,
        uf: principal.estado,
        ibge: principal.codigo_municipio,
      },
    }),
  );
  return estado;
}

async function abrirEndereco(page) {
  await page.goto(`/clientes/${pessoaId}/editar?aba=endereco`);
  await expect(page.getByRole("button", { name: "Adicionar endereço", exact: true })).toBeVisible();
}

async function preencherEndereco(page, endereco) {
  if (endereco.apelido) await page.locator("#endereco-apelido").fill(endereco.apelido);
  await page.locator("#endereco-cep").fill(endereco.cep);
  await page.locator("#endereco-numero").focus();
  // Aguarda o preenchimento por CEP antes de sobrescrever com o endereço do teste.
  await expect(page.locator("#endereco-cidade")).toHaveValue(principal.cidade);
  for (const [campo, id] of Object.entries({
    endereco: "logradouro",
    numero: "numero",
    complemento: "complemento",
    bairro: "bairro",
    cidade: "cidade",
    estado: "estado",
  })) {
    await page.locator(`#endereco-${id}`).fill(endereco[campo] || "");
  }
}

async function salvarEndereco(page) {
  const resposta = page.waitForResponse(
    (r) => new URL(r.url()).pathname === apiPessoa && r.request().method() === "PUT",
  );
  await page.getByRole("button", { name: "Salvar endereço", exact: true }).click();
  return resposta;
}

function card(page, texto) {
  return page
    .locator("div.rounded-lg.border.p-3")
    .filter({ has: page.getByText(texto, { exact: true }) });
}

test.describe("Pessoa — salvar endereço sem segundo salvar", () => {
  test("persiste o principal com um clique, mantém outro rascunho e aparece após recarregar", async ({
    page,
  }) => {
    const estado = await prepararApi(page);
    await abrirEndereco(page);
    await page.getByRole("tab", { name: "Dados gerais", exact: true }).click();
    await page.locator("#pessoa-nome").fill("Rascunho que não deve ser enviado");
    await page.getByRole("tab", { name: "Endereço", exact: true }).click();
    await card(page, "Principal").getByRole("button", { name: "Editar", exact: true }).click();
    await preencherEndereco(page, principal);
    expect((await salvarEndereco(page)).status()).toBe(200);
    await expect(page.locator("#endereco-logradouro")).toHaveCount(0);
    await expect(card(page, "Principal")).toContainText("Rua Principal QA, 42 - Sala QA");
    await expect(page.getByText("Nenhum endereço cadastrado", { exact: true })).toHaveCount(0);
    expect(estado.envios).toHaveLength(1);
    expect(Object.keys(estado.envios[0]).sort()).toEqual(
      [...camposEndereco, "enderecos_adicionais"].sort(),
    );
    expect(estado.envios[0]).toMatchObject(principal);
    expect(estado.pessoa.nome).toBe("Pessoa Sintética QA");
    await page.getByRole("tab", { name: "Dados gerais", exact: true }).click();
    await expect(page.locator("#pessoa-nome")).toHaveValue("Rascunho que não deve ser enviado");
    await page.reload();
    await expect(card(page, "Principal")).toContainText("Rua Principal QA, 42 - Sala QA");
    await page.getByRole("tab", { name: "Dados gerais", exact: true }).click();
    await expect(page.locator("#pessoa-nome")).toHaveValue("Pessoa Sintética QA");
  });

  test("persiste adicional e dois salvamentos gerais mantêm todos os cards preenchidos", async ({
    page,
  }) => {
    const estado = await prepararApi(page, principal);
    await abrirEndereco(page);
    await page.getByRole("button", { name: "Adicionar endereço", exact: true }).click();
    await preencherEndereco(page, adicional);
    expect((await salvarEndereco(page)).status()).toBe(200);
    await expect(card(page, adicional.apelido)).toContainText("Rua Entrega QA, 84");
    expect(estado.envios).toHaveLength(1);
    expect(estado.pessoa.enderecos_adicionais).toEqual([expect.objectContaining(adicional)]);
    await page.reload();
    await expect(card(page, adicional.apelido)).toContainText("Rua Entrega QA, 84");
    for (let tentativa = 0; tentativa < 2; tentativa += 1) {
      const resposta = page.waitForResponse(
        (r) => new URL(r.url()).pathname === apiPessoa && r.request().method() === "PUT",
      );
      await page.getByRole("button", { name: "Salvar", exact: true }).click();
      expect((await resposta).status()).toBe(200);
      await expect(card(page, "Principal")).toContainText("Rua Principal QA, 42 - Sala QA");
      await expect(card(page, adicional.apelido)).toContainText("Rua Entrega QA, 84");
      await expect(page.getByText("Nenhum endereço cadastrado", { exact: true })).toHaveCount(0);
    }
    expect(estado.envios).toHaveLength(3);
    expect(estado.pessoa.codigo_municipio).toBe(principal.codigo_municipio);
    expect(estado.pessoa.enderecos_adicionais[0].codigo_municipio).toBe(principal.codigo_municipio);
  });

  test("aguarda a API, conserva o modal em erro e permite tentar novamente", async ({ page }) => {
    const estado = await prepararApi(page, principal);
    await abrirEndereco(page);
    await card(page, "Principal").getByRole("button", { name: "Editar", exact: true }).click();
    await preencherEndereco(page, { ...principal, numero: "999" });
    estado.falharProximo = true;
    let liberarResposta;
    estado.aguardarResposta = new Promise((resolve) => {
      liberarResposta = resolve;
    });
    const resposta = salvarEndereco(page);
    try {
      await expect.poll(() => estado.envios.length).toBe(1);
      await expect(page.locator("#endereco-numero")).toHaveValue("999");
      await expect(
        page.getByRole("button", { name: "Salvar endereço", exact: true }),
      ).toBeDisabled();
    } finally {
      liberarResposta();
    }
    expect((await resposta).status()).toBe(503);
    await expect(
      page.getByText("Falha simulada ao salvar endereço.", { exact: true }),
    ).toBeVisible();
    await expect(page.locator("#endereco-numero")).toHaveValue("999");
    expect(estado.pessoa.numero).toBe("42");
    estado.aguardarResposta = null;
    expect((await salvarEndereco(page)).status()).toBe(200);
    await expect(page.locator("#endereco-numero")).toHaveCount(0);
    await expect(card(page, "Principal")).toContainText("Rua Principal QA, 999");
    await page.reload();
    await expect(card(page, "Principal")).toContainText("Rua Principal QA, 999");
  });

  test("troca o principal e remove o adicional sem pedir o salvar geral", async ({ page }) => {
    const estado = await prepararApi(page, { ...principal, enderecos_adicionais: [adicional] });
    await abrirEndereco(page);
    await card(page, adicional.apelido)
      .getByRole("button", { name: "Editar", exact: true })
      .click();
    await page.locator("#endereco-tipo").click();
    await page.getByRole("option", { name: "Principal", exact: true }).click();
    await page.getByRole("button", { name: "Salvar endereço", exact: true }).click();
    const promocao = page.waitForResponse(
      (r) => new URL(r.url()).pathname === apiPessoa && r.request().method() === "PUT",
    );
    await page.getByRole("button", { name: "Confirmar substituição", exact: true }).click();
    expect((await promocao).status()).toBe(200);
    await expect(card(page, "Principal")).toContainText("Rua Entrega QA, 84");
    expect(estado.pessoa.enderecos_adicionais).toEqual([
      expect.objectContaining({ ...principal, tipo: "residencial" }),
    ]);
    await page.reload();
    await expect(card(page, "Principal")).toContainText("Rua Entrega QA, 84");
    const remocao = page.waitForResponse(
      (r) => new URL(r.url()).pathname === apiPessoa && r.request().method() === "PUT",
    );
    await card(page, "Residencial").getByRole("button", { name: "Excluir", exact: true }).click();
    await page.getByRole("button", { name: "Confirmar", exact: true }).click();
    expect((await remocao).status()).toBe(200);
    expect(estado.pessoa.enderecos_adicionais).toEqual([]);
    await page.reload();
    await expect(card(page, "Principal")).toContainText("Rua Entrega QA, 84");
    await expect(page.getByText("Rua Principal QA, 42 - Sala QA", { exact: true })).toHaveCount(0);
  });

  test("novo cadastro mantém endereço em rascunho até criar a pessoa", async ({ page }) => {
    const estado = await prepararApi(page);
    await page.goto("/clientes");
    await page.getByRole("button", { name: /^novo cadastro$/i }).click();
    await page.locator("#pessoa-nome").fill("Nova Pessoa Sintética QA");
    await page.locator('label[for="pessoa-tipos-cadastro-fornecedor"]').click();
    await page.getByRole("tab", { name: "Endereço", exact: true }).click();
    await page.getByRole("button", { name: "Adicionar endereço", exact: true }).click();
    await preencherEndereco(page, adicional);
    await page.getByRole("button", { name: "Salvar endereço", exact: true }).click();
    await expect(page.locator("#endereco-logradouro")).toHaveCount(0);
    await expect(card(page, adicional.apelido)).toContainText("Rua Entrega QA, 84");
    expect(estado.envios).toEqual([]);
    expect(estado.criacoes).toEqual([]);
    const criacao = page.waitForResponse(
      (r) => new URL(r.url()).pathname === "/api/clientes/" && r.request().method() === "POST",
    );
    await page.getByRole("button", { name: "Criar cadastro", exact: true }).click();
    expect((await criacao).status()).toBe(201);
    expect(estado.criacoes).toHaveLength(1);
    expect(estado.pessoa.enderecos_adicionais).toEqual([expect.objectContaining(adicional)]);
  });

  test("endereço adicional não reenvia principal legado sem número", async ({ page }) => {
    const estado = await prepararApi(page, { ...principal, numero: null });
    await abrirEndereco(page);
    await page.getByRole("button", { name: "Adicionar endereço", exact: true }).click();
    await preencherEndereco(page, adicional);
    expect((await salvarEndereco(page)).status()).toBe(200);
    expect(estado.envios).toEqual([{ enderecos_adicionais: [expect.objectContaining(adicional)] }]);
    expect(estado.pessoa.numero).toBeNull();
    await expect(card(page, adicional.apelido)).toContainText("Rua Entrega QA, 84");
    await page.reload();
    await expect(card(page, adicional.apelido)).toContainText("Rua Entrega QA, 84");
  });
});
