// Helpers compartilhados pela suite e2e do CorePet.
//
// Os seletores aqui foram validados manualmente contra uma copia de producao
// (ensaio) em 2026-10-07: alguns campos do formulario de Produtos nao tem
// `name`/`id` nem `label[for]` (associacao so visual), entao a localizacao
// por texto do label + "proximo input" e proposital, nao um hack.

export function credenciaisDoAmbiente() {
  const baseURL = process.env.E2E_BASE_URL;
  const email = process.env.E2E_USER_EMAIL;
  const password = process.env.E2E_USER_PASSWORD;
  if (!baseURL || !email || !password) return null;
  return { baseURL, email, password };
}

export async function fecharTour(page) {
  const candidatos = [
    page.getByRole("button", { name: /concluir/i }),
    page.getByRole("button", { name: /pular/i }),
    page.locator(".driver-popover-close-btn"),
  ];
  for (const loc of candidatos) {
    const el = loc.first();
    if (await el.isVisible({ timeout: 1200 }).catch(() => false)) {
      await el.click().catch(() => {});
      await page.waitForTimeout(300);
      return true;
    }
  }
  return false;
}

export async function login(page, { email, password }) {
  await page.goto("/login", { waitUntil: "networkidle" });
  await page.fill("#login-identificador", email);
  await page.fill("#login-senha", password);
  await page.click("button:has-text('Entrar')");
  await page.waitForTimeout(1500);

  const escolhaEmpresa = page.getByText(/escolha a empresa/i).first();
  if (await escolhaEmpresa.isVisible({ timeout: 2000 }).catch(() => false)) {
    await page
      .locator("button")
      .filter({ hasText: "Entrar nesta empresa" })
      .first()
      .click();
    await page.waitForTimeout(1500);
  }

  await page.waitForLoadState("networkidle").catch(() => {});
  await fecharTour(page);
}

export function sufixoUnico() {
  return Date.now().toString().slice(-8);
}

export async function criarPessoaTeste(page) {
  await page.goto("/clientes", { waitUntil: "networkidle" });
  await fecharTour(page);

  await page.getByRole("button", { name: /novo/i }).first().click();
  await page.waitForTimeout(600);

  const sufixo = sufixoUnico();
  // Sem digitos fora do sufixo (nada tipo "E2E"): a busca de cliente do PDV
  // tem uma heuristica de "parece telefone" que extrai so os digitos do
  // texto inteiro quando acha varios digitos misturados - um "2" solto no
  // meio do nome (ex. em "E2E") corrompe a busca por numero errado.
  const nome = `Pessoa Automatizada ${sufixo}`;
  const celular = `1899${sufixo.slice(0, 6)}`;

  const campoNome = page
    .locator("#pessoa-criar-nome, input[placeholder='Digite o nome completo']")
    .first();
  await campoNome.waitFor({ state: "visible", timeout: 5000 });
  await campoNome.fill(nome);

  const campoCelular = page.locator("input[placeholder='(00) 00000-0000']").first();
  await campoCelular.fill(celular);

  await page.getByRole("button", { name: /criar cadastro/i }).first().click();
  await page.waitForTimeout(1500);

  return { nome, celular };
}

export async function criarProdutoTeste(page) {
  await page.goto("/produtos", { waitUntil: "networkidle" });
  await fecharTour(page);

  const botaoNovo = page
    .getByRole("link", { name: /novo produto/i })
    .or(page.getByRole("button", { name: /novo produto/i }))
    .first();
  if (await botaoNovo.isVisible().catch(() => false)) {
    await botaoNovo.click();
  } else {
    await page.goto("/produtos/novo");
  }
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.waitForTimeout(800);
  await fecharTour(page);

  const sufixo = sufixoUnico();
  const sku = `E2E-${sufixo}`;
  const nome = `Produto E2E ${sufixo}`;

  await page.locator("input[placeholder='Ex: PROD0001']").first().fill(sku);
  await page
    .locator("input[placeholder='Ex: Racao Golden para Caes Adultos 15kg']")
    .first()
    .fill(nome);

  // Preco de Venda fica na aba Caracteristicas (onde ja estamos), mas o
  // campo nao tem name/id nem label[for] - associacao so visual (ver nota
  // no topo do arquivo). Preenche aqui antes de cadastrar: o backend exige
  // esse campo e o toast de erro so aparece depois do clique (sempre, em
  // toda tentativa validada manualmente), entao evitamos a corrida de
  // clicar-errar-corrigir-clicar preenchendo direto.
  const campoPreco = page
    .locator("label")
    .filter({ hasText: /pre.o de venda/i })
    .locator("+ input")
    .first();
  await campoPreco.waitFor({ state: "visible", timeout: 10000 });
  await campoPreco.fill("49,90");

  const abaEstoque = page.locator("text=Estoque/Lotes").first();
  if (await abaEstoque.isVisible().catch(() => false)) {
    await abaEstoque.click();
    await page.waitForTimeout(400);
  }

  await page.getByRole("button", { name: /^cadastrar$/i }).first().click();
  await page.waitForTimeout(1500);

  return { sku, nome };
}

export async function ajustarEstoque(page, sku, { quantidade = "10", precoCusto = "25.00" } = {}) {
  await page.goto("/produtos", { waitUntil: "networkidle" });
  await fecharTour(page);

  const campoBusca = page.locator("input[placeholder*='uscar' i]").first();
  await campoBusca.fill(sku);
  await page.waitForTimeout(800);
  await fecharTour(page);

  await page.getByRole("button", { name: /^editar$/i }).first().click();
  await page.locator("text=Carregando produto").waitFor({ state: "detached", timeout: 10000 }).catch(() => {});
  await fecharTour(page);

  const abaEstoqueEdit = page
    .getByRole("tab", { name: /estoque\/lotes/i })
    .or(page.locator("text=Estoque/Lotes"))
    .first();
  const botaoNovaEntrada = page
    .getByRole("button", { name: /ajustar estoque|entrada de estoque|novo lote|adicionar lote|nova entrada/i })
    .first();

  // A troca de aba as vezes nao "pega" se clicada logo apos a navegacao
  // (pagina de edicao ainda terminando de montar); confere e tenta de novo.
  for (let tentativa = 0; tentativa < 3; tentativa += 1) {
    if (await abaEstoqueEdit.isVisible().catch(() => false)) {
      await abaEstoqueEdit.click();
    }
    await page.waitForTimeout(700);
    if (await botaoNovaEntrada.isVisible({ timeout: 2000 }).catch(() => false)) break;
  }

  await botaoNovaEntrada.click();
  await page.waitForTimeout(600);

  const campoQuantidade = page
    .locator("label")
    .filter({ hasText: /^Quantidade/ })
    .locator("+ input")
    .first();
  await campoQuantidade.fill(quantidade);

  const campoPrecoCusto = page
    .locator("label")
    .filter({ hasText: /pre.o de custo/i })
    .locator("xpath=following-sibling::*[1]//input | following-sibling::input[1]")
    .first();
  await campoPrecoCusto.fill(precoCusto);

  await page.getByRole("button", { name: /registrar entrada/i }).first().click();
  await page.waitForTimeout(1200);
}

export async function abrirCaixaSeNecessario(page) {
  const botaoAbrirCaixa = page.getByRole("button", { name: /abrir caixa/i }).first();
  if (!(await botaoAbrirCaixa.isVisible().catch(() => false))) return;

  await botaoAbrirCaixa.click();
  await page.waitForTimeout(600);

  const campoValorInicial = page.locator("input[placeholder='0,00']").first();
  await campoValorInicial.click();
  await page.keyboard.press("Control+A").catch(() => {});
  await page.keyboard.press("Backspace").catch(() => {});
  // Mascara de moeda: digita os centavos da direita pra esquerda, "10000" = R$ 100,00.
  await page.keyboard.type("10000", { delay: 40 });

  await page.getByRole("button", { name: /abrir caixa|confirmar/i }).last().click();
  await page.waitForTimeout(1000);
}

export async function buscarEAdicionarProdutoPDV(page, sku) {
  await page.locator("input[placeholder*='nome do produto' i]").first().fill(sku);
  await page.waitForTimeout(1000);
  const resultado = page.locator(`text=${sku}`).first();
  await resultado.waitFor({ state: "visible", timeout: 5000 });
  await resultado.click();
  await page.waitForTimeout(800);
}

export async function vincularClientePDV(page, nomeCliente) {
  const botaoFechar = page.getByRole("button", { name: /^fechar$/i }).first();
  if (await botaoFechar.isVisible().catch(() => false)) {
    await botaoFechar.click();
    await page.waitForTimeout(400);
  }

  const campoCliente = page.locator("input[placeholder*='nome, CPF ou telefone' i]").first();
  const resultado = page.locator(`text=${nomeCliente}`).first();

  // Pessoa acabou de ser criada agora mesmo; a busca do PDV pode levar um
  // instante a mais pra enxergar o cadastro novo. Tenta de novo antes de desistir.
  let encontrado = false;
  for (let tentativa = 0; tentativa < 3 && !encontrado; tentativa += 1) {
    await campoCliente.fill("");
    await campoCliente.fill(nomeCliente);
    encontrado = await resultado.isVisible({ timeout: 3000 }).catch(() => false);
    if (!encontrado) await page.waitForTimeout(1200);
  }

  await resultado.waitFor({ state: "visible", timeout: 5000 });
  await resultado.click();
  await page.waitForTimeout(600);
}
