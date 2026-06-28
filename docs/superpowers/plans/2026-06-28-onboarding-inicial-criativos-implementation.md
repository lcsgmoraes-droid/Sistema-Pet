# Onboarding Inicial e Criativos Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Revisar a Introducao Guiada, criar checklist interno de implantacao e preparar a base textual para videos/criativos do Sistema Pet.

**Architecture:** Extrair a configuracao da Introducao Guiada para modulos puros testaveis, manter a tela React como camada de apresentacao e registrar a implantacao interna em documentos versionados. A Central de Ajuda recebe conteudo alinhado aos caminhos reais do menu, e um contrato em Node protege a estrutura minima do onboarding.

**Tech Stack:** React 18, Vite, Node.js `node:test`, scripts `.mjs`, Markdown em `docs/`.

---

## File Structure

- Create: `frontend/scripts/test-onboarding-inicial-contract.mjs`
  - Contrato de baixo custo que valida se o onboarding tem secoes obrigatorias, IDs unicos, caminhos reais e matriz basica de conteudo.
- Modify: `frontend/package.json`
  - Adiciona script `test:onboarding-inicial`.
- Create: `frontend/src/pages/introducaoGuiada/introducaoGuiadaConfig.js`
  - Fonte unica das secoes, itens, badges, ordenacao e helpers puros da Introducao Guiada.
- Create: `frontend/src/pages/introducaoGuiada/introducaoGuiadaChecks.js`
  - Helpers puros para estado inicial de checks, contagem de respostas e execucao defensiva de checks automaticos.
- Create: `frontend/src/pages/introducaoGuiada/introducaoGuiadaChecks.test.mjs`
  - Testes unitarios dos helpers de checks automaticos.
- Modify: `frontend/src/pages/IntroducaoGuiada.jsx`
  - Passa a consumir os modulos extraidos, exibe melhor obrigatorio/opcional/condicional e preserva comportamento atual.
- Modify: `frontend/src/pages/centralAjuda/centralAjudaKnowledge.js`
  - Adiciona artigos de primeiros passos, corrige caminhos obsoletos e alinha compras/entrada XML/Bling.
- Create: `docs/implantacao/GUIA_IMPLANTACAO_INICIAL.md`
  - Checklist interno para Lucas/suporte conduzir implantacao.
- Create: `docs/marketing/MATRIZ_CRIATIVOS_SISTEMA.md`
  - Matriz inicial de videos demonstrativos e criativos comerciais.
- Modify: `docs/INDICE_OPERACIONAL.md`
  - Inclui links para os dois documentos novos.

---

### Task 1: Add Onboarding Contract Test

**Files:**
- Create: `frontend/scripts/test-onboarding-inicial-contract.mjs`
- Modify: `frontend/package.json`

- [ ] **Step 1: Write the failing contract test**

Create `frontend/scripts/test-onboarding-inicial-contract.mjs`:

```js
import assert from "node:assert/strict";
import {
  SECOES_ONBOARDING,
  buildGuiaHref,
  flattenOnboardingItems,
} from "../src/pages/introducaoGuiada/introducaoGuiadaConfig.js";

const REQUIRED_SECTIONS = [
  "empresa-acesso",
  "financeiro-obrigatorio",
  "cadastros-base",
  "operacao-venda",
  "compras-estoque",
  "modulos-operacao",
  "validacao-final",
];

const REQUIRED_ITEM_IDS = [
  "empresa-dados",
  "empresa-fiscal",
  "usuarios-permissoes",
  "contas-bancarias",
  "formas-pagamento",
  "operadoras-cartao",
  "categorias-financeiras",
  "dre-tipos-despesa",
  "produtos",
  "pessoas",
  "abrir-caixa",
  "venda-teste",
  "fechar-caixa",
  "compras-entrada-xml",
  "modulo-veterinario",
  "modulo-banho-tosa",
  "validacao-relatorios",
];

const VALID_BADGES = new Set(["obrigatorio", "recomendado", "condicional"]);

assert.equal(Array.isArray(SECOES_ONBOARDING), true, "SECOES_ONBOARDING deve ser array");

for (const sectionId of REQUIRED_SECTIONS) {
  assert(
    SECOES_ONBOARDING.some((section) => section.id === sectionId),
    `Secao obrigatoria ausente: ${sectionId}`,
  );
}

const items = flattenOnboardingItems(SECOES_ONBOARDING);
const itemIds = items.map((item) => item.id);
assert.equal(new Set(itemIds).size, itemIds.length, "IDs dos itens devem ser unicos");

for (const itemId of REQUIRED_ITEM_IDS) {
  assert(itemIds.includes(itemId), `Item obrigatorio ausente: ${itemId}`);
}

for (const item of items) {
  assert(item.titulo, `Item ${item.id} precisa de titulo`);
  assert(item.resultado, `Item ${item.id} precisa de resultado`);
  assert(item.onde?.startsWith("/"), `Item ${item.id} precisa apontar para rota absoluta`);
  assert(VALID_BADGES.has(item.tipo), `Item ${item.id} tem tipo invalido: ${item.tipo}`);
}

assert.equal(
  buildGuiaHref("/cadastros/financeiro/formas-pagamento", "formas-pagamento"),
  "/cadastros/financeiro/formas-pagamento?guia=formas-pagamento",
);
assert.equal(
  buildGuiaHref("/pdv?origem=ajuda", "venda-teste"),
  "/pdv?origem=ajuda&guia=venda-teste",
);

console.log("Onboarding inicial contract OK");
```

- [ ] **Step 2: Add package script**

In `frontend/package.json`, add this line inside `"scripts"`:

```json
"test:onboarding-inicial": "node scripts/test-onboarding-inicial-contract.mjs"
```

- [ ] **Step 3: Run test to verify it fails**

Run:

```powershell
cd frontend
npm run test:onboarding-inicial
```

Expected: FAIL with `ERR_MODULE_NOT_FOUND` for `introducaoGuiadaConfig.js`.

- [ ] **Step 4: Commit**

Run:

```powershell
git add frontend/package.json frontend/scripts/test-onboarding-inicial-contract.mjs
git commit -m "test: adiciona contrato do onboarding inicial"
```

---

### Task 2: Extract Onboarding Configuration

**Files:**
- Create: `frontend/src/pages/introducaoGuiada/introducaoGuiadaConfig.js`
- Test: `frontend/scripts/test-onboarding-inicial-contract.mjs`

- [ ] **Step 1: Create config module**

Create `frontend/src/pages/introducaoGuiada/introducaoGuiadaConfig.js` with this exported shape:

```js
export const BADGE_LABELS = {
  obrigatorio: "Obrigatorio",
  recomendado: "Recomendado",
  condicional: "Condicional",
};

export function flattenOnboardingItems(secoes = SECOES_ONBOARDING) {
  return secoes.flatMap((secao) =>
    secao.itens.map((item) => ({
      ...item,
      secaoId: secao.id,
      secaoTitulo: secao.titulo,
    })),
  );
}

export function buildGuiaHref(path, guiaId) {
  const sep = path.includes("?") ? "&" : "?";
  return `${path}${sep}guia=${encodeURIComponent(guiaId)}`;
}

export const SECOES_ONBOARDING = [
  {
    id: "empresa-acesso",
    titulo: "1) Empresa, acesso e permissoes",
    resumo: "Identifique a empresa, revise acesso e confirme quais modulos estao liberados.",
    itens: [
      {
        id: "empresa-dados",
        titulo: "Conferir dados cadastrais da empresa",
        tipo: "obrigatorio",
        onde: "/configuracoes",
        resultado: "Recibos, documentos e comunicacoes usam os dados certos.",
        autoCheckKey: "empresaDados",
      },
      {
        id: "empresa-fiscal",
        titulo: "Conferir configuracao fiscal basica",
        tipo: "obrigatorio",
        onde: "/configuracoes/fiscal",
        resultado: "Impostos, margem e documentos fiscais partem de uma base coerente.",
        autoCheckKey: "empresaFiscal",
      },
      {
        id: "usuarios-permissoes",
        titulo: "Criar usuarios e revisar permissoes",
        tipo: "recomendado",
        onde: "/admin/usuarios",
        resultado: "Cada pessoa opera com acesso adequado, sem depender do admin.",
        autoCheckKey: "usuarios",
      },
      {
        id: "plano-modulos",
        titulo: "Conferir plano e modulos ativos",
        tipo: "recomendado",
        onde: "/meu-plano",
        resultado: "O guia mostra apenas o que faz sentido para a operacao contratada.",
      },
    ],
  },
  {
    id: "financeiro-obrigatorio",
    titulo: "2) Financeiro obrigatorio",
    resumo: "Prepare caixa, recebimentos, DRE e conciliacao antes da primeira venda real.",
    itens: [
      {
        id: "contas-bancarias",
        titulo: "Conferir bancos, caixas e carteiras",
        tipo: "obrigatorio",
        onde: "/cadastros/financeiro/bancos",
        resultado: "O sistema sabe onde o dinheiro entra e sai.",
        autoCheckKey: "contasBancarias",
      },
      {
        id: "formas-pagamento",
        titulo: "Conferir formas de pagamento",
        tipo: "obrigatorio",
        onde: "/cadastros/financeiro/formas-pagamento",
        resultado: "O PDV consegue finalizar vendas e gerar recebiveis quando necessario.",
        autoCheckKey: "formasPagamento",
      },
      {
        id: "operadoras-cartao",
        titulo: "Cadastrar operadoras de cartao",
        tipo: "condicional",
        condicao: "Obrigatorio se vender em cartao",
        onde: "/cadastros/financeiro/operadoras",
        resultado: "Taxas, prazos e conciliacao de cartao ficam mais confiaveis.",
        autoCheckKey: "operadoras",
      },
      {
        id: "categorias-financeiras",
        titulo: "Revisar categorias financeiras",
        tipo: "obrigatorio",
        onde: "/cadastros/categorias-financeiras",
        resultado: "Fluxo de caixa e contas usam classificacao consistente.",
        autoCheckKey: "categoriasFinanceiras",
      },
      {
        id: "dre-tipos-despesa",
        titulo: "Revisar DRE e tipos de despesa",
        tipo: "obrigatorio",
        onde: "/financeiro/dre",
        resultado: "Lucro, custos e despesas aparecem com leitura gerencial correta.",
        autoCheckKey: "dreBase",
      },
    ],
  },
  {
    id: "cadastros-base",
    titulo: "3) Cadastros base da operacao",
    resumo: "Organize produtos, pessoas e pets antes de rodar o atendimento real.",
    itens: [
      {
        id: "departamentos-categorias-marcas",
        titulo: "Conferir departamentos, categorias e marcas",
        tipo: "obrigatorio",
        onde: "/cadastros/categorias",
        resultado: "Produtos ficam organizados para venda, relatorios e comissao.",
        autoCheckKey: "categoriasProduto",
      },
      {
        id: "produtos",
        titulo: "Cadastrar ou importar produtos vendaveis",
        tipo: "obrigatorio",
        onde: "/produtos",
        resultado: "PDV, estoque, ecommerce e app passam a ter catalogo operacional.",
        autoCheckKey: "produtos",
      },
      {
        id: "estoque-minimo",
        titulo: "Revisar estoque inicial e estoque minimo",
        tipo: "recomendado",
        onde: "/produtos",
        resultado: "Alertas de ruptura e reposicao ficam mais uteis.",
        autoCheckKey: "estoqueMinimo",
      },
      {
        id: "pessoas",
        titulo: "Cadastrar clientes, fornecedores e equipe",
        tipo: "obrigatorio",
        onde: "/clientes",
        resultado: "Vendas, compras, financeiro e atendimento ficam vinculados a pessoas reais.",
        autoCheckKey: "pessoas",
      },
      {
        id: "pets",
        titulo: "Cadastrar pets dos clientes",
        tipo: "recomendado",
        onde: "/pets",
        resultado: "Historico, recorrencia, veterinario e banho/tosa ganham contexto.",
        autoCheckKey: "pets",
      },
      {
        id: "especies-racas-opcoes-racao",
        titulo: "Revisar especies, racas e opcoes de racao",
        tipo: "recomendado",
        onde: "/cadastros/especies-racas",
        resultado: "Cadastro de pets e analises de racao ficam padronizados.",
        autoCheckKey: "opcoesRacao",
      },
    ],
  },
  {
    id: "operacao-venda",
    titulo: "4) PDV, caixa e primeira venda",
    resumo: "Teste o ciclo minimo antes de operar com cliente real.",
    itens: [
      {
        id: "abrir-caixa",
        titulo: "Abrir caixa com saldo inicial",
        tipo: "obrigatorio",
        onde: "/pdv",
        resultado: "O dia de venda comeca com conferencia de caixa.",
        autoCheckKey: "caixaAberto",
      },
      {
        id: "venda-teste",
        titulo: "Fazer venda teste",
        tipo: "obrigatorio",
        onde: "/pdv",
        resultado: "Venda, pagamento, estoque e financeiro sao validados juntos.",
        autoCheckKey: "temVendas",
      },
      {
        id: "contas-receber-venda",
        titulo: "Conferir contas a receber da venda",
        tipo: "obrigatorio",
        onde: "/financeiro/contas-receber",
        resultado: "Recebiveis aparecem quando a forma de pagamento exige prazo.",
      },
      {
        id: "fechar-caixa",
        titulo: "Fechar caixa e conferir diferenca",
        tipo: "obrigatorio",
        onde: "/meus-caixas",
        resultado: "A rotina diaria fica validada ate a conferencia final.",
      },
    ],
  },
  {
    id: "compras-estoque",
    titulo: "5) Compras, estoque e entrada XML",
    resumo: "Valide reposicao, custo, impostos de entrada e integracoes.",
    itens: [
      {
        id: "fornecedores",
        titulo: "Cadastrar fornecedores principais",
        tipo: "recomendado",
        onde: "/clientes",
        resultado: "Compras e produtos ficam vinculados ao fornecedor certo.",
        autoCheckKey: "fornecedores",
      },
      {
        id: "compras-pedidos",
        titulo: "Registrar pedido de compra",
        tipo: "condicional",
        condicao: "Obrigatorio se usar modulo Compras",
        onde: "/compras/pedidos",
        resultado: "Reposicao passa a ter pedido, recebimento e historico.",
        modulo: "compras",
        autoCheckKey: "pedidoCompra",
      },
      {
        id: "compras-entrada-xml",
        titulo: "Processar entrada XML ou nota de compra",
        tipo: "condicional",
        condicao: "Obrigatorio se usar entrada fiscal de mercadoria",
        onde: "/compras/entrada-xml",
        resultado: "Custos, impostos, divergencias e estoque sao conferidos pela NF.",
        modulo: "compras",
        autoCheckKey: "entradaXml",
      },
      {
        id: "bling-integracao",
        titulo: "Validar integracao Bling",
        tipo: "condicional",
        condicao: "Obrigatorio se usar Bling",
        onde: "/produtos/sinc-bling",
        resultado: "Produtos, pedidos e monitoramento ficam alinhados com o Bling.",
        modulo: "bling",
        autoCheckKey: "blingConfig",
      },
    ],
  },
  {
    id: "modulos-operacao",
    titulo: "6) Modulos por tipo de operacao",
    resumo: "Ative apenas os fluxos que fazem sentido para o cliente.",
    itens: [
      {
        id: "modulo-entregas",
        titulo: "Configurar entregas",
        tipo: "condicional",
        condicao: "Se a loja faz delivery",
        onde: "/configuracoes/entregas",
        resultado: "Rotas, taxas, origem e entregadores ficam prontos.",
        modulo: "entregas",
        autoCheckKey: "configEntrega",
      },
      {
        id: "modulo-comissoes",
        titulo: "Configurar comissoes",
        tipo: "condicional",
        condicao: "Se a equipe recebe comissao",
        onde: "/comissoes",
        resultado: "Vendas geram calculo de comissao conforme regra definida.",
        modulo: "comissoes",
        autoCheckKey: "comissoesConfig",
      },
      {
        id: "modulo-banho-tosa",
        titulo: "Configurar Banho & Tosa",
        tipo: "condicional",
        condicao: "Se a loja agenda banho/tosa",
        onde: "/banho-tosa/servicos",
        resultado: "Servicos, agenda, recursos e fila ficam prontos para atendimento.",
        modulo: "banho_tosa",
        autoCheckKey: "banhoTosaServicos",
      },
      {
        id: "modulo-veterinario",
        titulo: "Configurar modulo veterinario",
        tipo: "condicional",
        condicao: "Se a empresa usa clinica veterinaria",
        onde: "/veterinario/configuracoes",
        resultado: "Agenda, consultorios, parceiros e catalogos clinicos ficam preparados.",
        modulo: "veterinario",
        autoCheckKey: "vetConfig",
      },
      {
        id: "modulo-ecommerce",
        titulo: "Configurar ecommerce",
        tipo: "condicional",
        condicao: "Se vender online",
        onde: "/ecommerce/configuracoes",
        resultado: "Loja, retirada/entrega, pagamento e catalogo online ficam prontos.",
        modulo: "ecommerce",
        autoCheckKey: "ecommerceConfig",
      },
      {
        id: "modulo-campanhas",
        titulo: "Criar primeira campanha",
        tipo: "condicional",
        condicao: "Se usar campanhas",
        onde: "/campanhas",
        resultado: "Cliente ja sai com uma acao comercial configurada.",
        modulo: "campanhas",
        autoCheckKey: "campanhas",
      },
      {
        id: "modulo-whatsapp",
        titulo: "Configurar WhatsApp",
        tipo: "condicional",
        condicao: "Se usar atendimento ou automacao via WhatsApp",
        onde: "/ia/whatsapp",
        resultado: "Atendimento, handoff e automacoes ficam rastreaveis.",
        modulo: "whatsapp",
        autoCheckKey: "whatsappConfig",
      },
    ],
  },
  {
    id: "validacao-final",
    titulo: "7) Validacao final",
    resumo: "Confira o sistema como usuario real antes de encerrar a implantacao.",
    itens: [
      {
        id: "validacao-fluxo-caixa",
        titulo: "Conferir fluxo de caixa",
        tipo: "obrigatorio",
        onde: "/financeiro/fluxo-caixa",
        resultado: "Entradas e saidas aparecem com datas e contas corretas.",
      },
      {
        id: "validacao-dre",
        titulo: "Conferir DRE",
        tipo: "obrigatorio",
        onde: "/financeiro/dre",
        resultado: "Receitas, custos e despesas aparecem em leitura gerencial.",
      },
      {
        id: "validacao-relatorios",
        titulo: "Conferir relatorios de venda e estoque",
        tipo: "obrigatorio",
        onde: "/financeiro/relatorio-vendas",
        resultado: "Gestor consegue tomar decisao com dados confiaveis.",
      },
      {
        id: "validacao-usuario-operacional",
        titulo: "Testar com usuario operacional",
        tipo: "obrigatorio",
        onde: "/admin/usuarios",
        resultado: "A rotina funciona sem usar acesso de administrador.",
      },
    ],
  },
];
```

- [ ] **Step 2: Run the contract**

Run:

```powershell
cd frontend
npm run test:onboarding-inicial
```

Expected: PASS and `Onboarding inicial contract OK`.

- [ ] **Step 3: Commit**

Run:

```powershell
git add frontend/src/pages/introducaoGuiada/introducaoGuiadaConfig.js
git commit -m "feat: extrai configuracao do onboarding inicial"
```

---

### Task 3: Extract Automatic Check Helpers

**Files:**
- Create: `frontend/src/pages/introducaoGuiada/introducaoGuiadaChecks.js`
- Create: `frontend/src/pages/introducaoGuiada/introducaoGuiadaChecks.test.mjs`

- [ ] **Step 1: Write failing helper tests**

Create `frontend/src/pages/introducaoGuiada/introducaoGuiadaChecks.test.mjs`:

```js
import assert from "node:assert/strict";
import { test } from "node:test";
import {
  criarEstadoChecksInicial,
  executarIntroducaoChecks,
  toCount,
} from "./introducaoGuiadaChecks.js";

test("toCount normaliza formatos comuns de resposta", () => {
  assert.equal(toCount([1, 2]), 2);
  assert.equal(toCount({ items: [1] }), 1);
  assert.equal(toCount({ data: [1, 2, 3] }), 3);
  assert.equal(toCount({ total: 4 }), 4);
  assert.equal(toCount({ count: 5 }), 5);
  assert.equal(toCount(null), 0);
});

test("criarEstadoChecksInicial preserva todas as chaves conhecidas como false", () => {
  const checks = criarEstadoChecksInicial();
  assert.equal(checks.empresaFiscal, false);
  assert.equal(checks.formasPagamento, false);
  assert.equal(checks.categoriasFinanceiras, false);
  assert.equal(checks.entradaXml, false);
  assert.equal(checks.whatsappConfig, false);
});

test("executarIntroducaoChecks marca checks com respostas positivas e ignora falhas", async () => {
  const respostas = new Map([
    ["/empresa/fiscal", { regime_tributario: "simples" }],
    ["/empresa/dados-cadastrais", {
      cnpj: "00.000.000/0001-00",
      razao_social: "Pet Teste",
      endereco: "Rua A",
      numero: "1",
      bairro: "Centro",
      cidade: "Presidente Prudente",
      uf: "SP",
    }],
    ["/contas-bancarias?apenas_ativas=true", [{ id: 1 }]],
    ["/financeiro/formas-pagamento?apenas_ativas=true", [{ id: 2 }]],
    ["/financeiro/categorias", { total: 2 }],
    ["/dre/categorias", [{ id: 1 }]],
    ["/dre/subcategorias", [{ id: 10 }]],
    ["/vendas?page=1&per_page=1", { total: 1 }],
  ]);

  const api = {
    async get(url) {
      if (url === "/compras/entrada-xml?limit=1") {
        throw new Error("Modulo sem acesso");
      }
      return { data: respostas.get(url) ?? {} };
    },
  };

  const checks = await executarIntroducaoChecks(api);

  assert.equal(checks.empresaFiscal, true);
  assert.equal(checks.empresaDados, true);
  assert.equal(checks.contasBancarias, true);
  assert.equal(checks.formasPagamento, true);
  assert.equal(checks.categoriasFinanceiras, true);
  assert.equal(checks.dreBase, true);
  assert.equal(checks.temVendas, true);
  assert.equal(checks.entradaXml, false);
});
```

- [ ] **Step 2: Run helper tests to verify failure**

Run:

```powershell
cd frontend
node src/pages/introducaoGuiada/introducaoGuiadaChecks.test.mjs
```

Expected: FAIL with `ERR_MODULE_NOT_FOUND` for `introducaoGuiadaChecks.js`.

- [ ] **Step 3: Create helper module**

Create `frontend/src/pages/introducaoGuiada/introducaoGuiadaChecks.js`:

```js
export const CHECK_KEYS = [
  "empresaFiscal",
  "empresaDados",
  "usuarios",
  "contasBancarias",
  "formasPagamento",
  "operadoras",
  "categoriasFinanceiras",
  "dreBase",
  "categoriasProduto",
  "produtos",
  "estoqueMinimo",
  "pessoas",
  "fornecedores",
  "pets",
  "opcoesRacao",
  "caixaAberto",
  "temVendas",
  "pedidoCompra",
  "entradaXml",
  "blingConfig",
  "configEntrega",
  "entregadores",
  "comissoesConfig",
  "banhoTosaServicos",
  "vetConfig",
  "ecommerceConfig",
  "campanhas",
  "whatsappConfig",
];

export function criarEstadoChecksInicial() {
  return Object.fromEntries(CHECK_KEYS.map((key) => [key, false]));
}

export function toCount(data) {
  if (Array.isArray(data)) return data.length;
  if (!data || typeof data !== "object") return 0;
  if (Array.isArray(data.items)) return data.items.length;
  if (Array.isArray(data.data)) return data.data.length;
  if (typeof data.total === "number") return data.total;
  if (typeof data.count === "number") return data.count;
  return 0;
}

async function safeCheck(fn) {
  try {
    return Boolean(await fn());
  } catch {
    return false;
  }
}

export async function executarIntroducaoChecks(api) {
  const checks = criarEstadoChecksInicial();

  const tarefas = [
    ["empresaFiscal", async () => {
      const { data = {} } = await api.get("/empresa/fiscal");
      return Boolean(data.regime_tributario || data.cnae_principal || data.aliquota_simples_vigente);
    }],
    ["empresaDados", async () => {
      const { data = {} } = await api.get("/empresa/dados-cadastrais");
      return Boolean(data.cnpj && data.razao_social && data.endereco && data.numero && data.bairro && data.cidade && data.uf);
    }],
    ["usuarios", async () => toCount((await api.get("/usuarios?limit=2")).data) > 1],
    ["contasBancarias", async () => toCount((await api.get("/contas-bancarias?apenas_ativas=true")).data) > 0],
    ["formasPagamento", async () => toCount((await api.get("/financeiro/formas-pagamento?apenas_ativas=true")).data) > 0],
    ["operadoras", async () => toCount((await api.get("/operadoras-cartao?apenas_ativas=true")).data) > 0],
    ["categoriasFinanceiras", async () => toCount((await api.get("/financeiro/categorias")).data) > 0],
    ["dreBase", async () => {
      const categorias = toCount((await api.get("/dre/categorias")).data);
      const subcategorias = toCount((await api.get("/dre/subcategorias")).data);
      return categorias > 0 && subcategorias > 0;
    }],
    ["categoriasProduto", async () => toCount((await api.get("/produtos/categorias")).data) > 0],
    ["produtos", async () => {
      const { data = {} } = await api.get("/produtos?per_page=1");
      return Boolean((Array.isArray(data.produtos) && data.produtos.length > 0) || data.total > 0);
    }],
    ["estoqueMinimo", async () => toCount((await api.get("/produtos?per_page=1&estoque_minimo_configurado=true")).data) > 0],
    ["pessoas", async () => toCount((await api.get("/clientes/?limit=1")).data) > 0],
    ["fornecedores", async () => toCount((await api.get("/clientes/?tipo=fornecedor&limit=1")).data) > 0],
    ["pets", async () => toCount((await api.get("/pets?limit=1")).data) > 0],
    ["opcoesRacao", async () => toCount((await api.get("/opcoes-racao/linhas?apenas_ativos=false")).data) > 0],
    ["caixaAberto", async () => Boolean((await api.get("/caixas/aberto")).data?.id)],
    ["temVendas", async () => Number((await api.get("/vendas?page=1&per_page=1")).data?.total || 0) > 0],
    ["pedidoCompra", async () => toCount((await api.get("/compras/pedidos?limit=1")).data) > 0],
    ["entradaXml", async () => toCount((await api.get("/compras/entrada-xml?limit=1")).data) > 0],
    ["blingConfig", async () => toCount((await api.get("/bling/status")).data) > 0],
    ["configEntrega", async () => Object.keys((await api.get("/configuracoes/entregas")).data || {}).length > 0],
    ["entregadores", async () => toCount((await api.get("/clientes/?is_entregador=true&incluir_inativos=false&limit=1")).data) > 0],
    ["comissoesConfig", async () => {
      const lista = (await api.get("/comissoes/configuracoes/funcionarios")).data?.data || [];
      return lista.some((funcionario) => Number(funcionario.total_configuracoes || 0) > 0);
    }],
    ["banhoTosaServicos", async () => toCount((await api.get("/banho-tosa/servicos?limit=1")).data) > 0],
    ["vetConfig", async () => Object.keys((await api.get("/veterinario/configuracoes")).data || {}).length > 0],
    ["ecommerceConfig", async () => Object.keys((await api.get("/ecommerce-config")).data || {}).length > 0],
    ["campanhas", async () => toCount((await api.get("/campanhas?limit=1")).data) > 0],
    ["whatsappConfig", async () => Object.keys((await api.get("/whatsapp/config")).data || {}).length > 0],
  ];

  await Promise.all(
    tarefas.map(async ([key, fn]) => {
      checks[key] = await safeCheck(fn);
    }),
  );

  return checks;
}
```

- [ ] **Step 4: Run helper tests**

Run:

```powershell
cd frontend
node src/pages/introducaoGuiada/introducaoGuiadaChecks.test.mjs
```

Expected: PASS with 3 passing tests.

- [ ] **Step 5: Commit**

Run:

```powershell
git add frontend/src/pages/introducaoGuiada/introducaoGuiadaChecks.js frontend/src/pages/introducaoGuiada/introducaoGuiadaChecks.test.mjs
git commit -m "feat: extrai checks do onboarding inicial"
```

---

### Task 4: Update IntroducaoGuiada Page

**Files:**
- Modify: `frontend/src/pages/IntroducaoGuiada.jsx`
- Test: `frontend/scripts/test-onboarding-inicial-contract.mjs`
- Test: `frontend/src/pages/introducaoGuiada/introducaoGuiadaChecks.test.mjs`

- [ ] **Step 1: Replace embedded config imports**

In `frontend/src/pages/IntroducaoGuiada.jsx`, replace the local `SECOES`, `toCount`, and `buildGuiaHref` declarations with:

```js
import {
  BADGE_LABELS,
  SECOES_ONBOARDING,
  buildGuiaHref,
  flattenOnboardingItems,
} from "./introducaoGuiada/introducaoGuiadaConfig";
import { executarIntroducaoChecks } from "./introducaoGuiada/introducaoGuiadaChecks";
```

Then replace references:

```js
const SECOES = SECOES_ONBOARDING;
```

and:

```js
const todosItens = useMemo(() => flattenOnboardingItems(SECOES), []);
```

- [ ] **Step 2: Replace automatic check execution**

Replace the body of `executarChecksAutomaticos` with:

```js
const executarChecksAutomaticos = async () => {
  setCarregandoChecks(true);
  const results = await executarIntroducaoChecks(api);
  setAutoChecks(results);
  setCarregandoChecks(false);
};
```

- [ ] **Step 3: Update badge rendering**

Replace:

```js
const badgeObrigatorio = item.obrigatorio ? "Obrigatorio" : "Opcional";
```

with:

```js
const badgeLabel = BADGE_LABELS[item.tipo] || "Recomendado";
const badgeClass =
  item.tipo === "obrigatorio"
    ? "bg-red-100 text-red-700"
    : item.tipo === "condicional"
      ? "bg-amber-100 text-amber-700"
      : "bg-gray-100 text-gray-600";
```

Replace the badge span content with:

```jsx
<span className={`text-xs px-2 py-0.5 rounded-full ${badgeClass}`}>
  {badgeLabel}
</span>
```

- [ ] **Step 4: Add section summary text**

Under the section title, add:

```jsx
{secao.resumo && <p className="text-sm text-gray-600 mb-4">{secao.resumo}</p>}
```

- [ ] **Step 5: Run focused tests**

Run:

```powershell
cd frontend
npm run test:onboarding-inicial
node src/pages/introducaoGuiada/introducaoGuiadaChecks.test.mjs
```

Expected: both commands pass.

- [ ] **Step 6: Commit**

Run:

```powershell
git add frontend/src/pages/IntroducaoGuiada.jsx
git commit -m "feat: atualiza tela de introducao guiada"
```

---

### Task 5: Update Central Help Content

**Files:**
- Modify: `frontend/src/pages/centralAjuda/centralAjudaKnowledge.js`
- Modify: `frontend/scripts/test-onboarding-inicial-contract.mjs`

- [ ] **Step 1: Extend contract to guard help articles**

Append these checks to `frontend/scripts/test-onboarding-inicial-contract.mjs` before the final `console.log("Onboarding inicial contract OK");` line:

```js
import fs from "node:fs";
import path from "node:path";
import process from "node:process";

const root = process.cwd();
const ajudaSource = fs.readFileSync(
  path.join(root, "src/pages/centralAjuda/centralAjudaKnowledge.js"),
  "utf8",
);

for (const requiredText of [
  "Primeiros passos para configurar o Sistema Pet",
  "Financeiro obrigatorio antes da primeira venda",
  "Compras, entrada XML e Bling",
  "/cadastros/financeiro/formas-pagamento",
  "/compras/entrada-xml",
  "/ecommerce/configuracoes",
]) {
  assert(ajudaSource.includes(requiredText), `Central de Ajuda sem texto: ${requiredText}`);
}
```

- [ ] **Step 2: Run contract to verify failure**

Run:

```powershell
cd frontend
npm run test:onboarding-inicial
```

Expected: FAIL with missing `Primeiros passos para configurar o Sistema Pet`.

- [ ] **Step 3: Add Central Help articles**

In `frontend/src/pages/centralAjuda/centralAjudaKnowledge.js`, add a new module block near the top of `BASE_CONHECIMENTO`:

```js
{
  modulo: "primeiros-passos",
  label: "Primeiros Passos",
  icone: FiBookOpen,
  cor: "emerald",
  artigos: [
    {
      titulo: "Primeiros passos para configurar o Sistema Pet",
      tags: ["inicio", "configuracao", "onboarding", "primeiros passos"],
      conteudo: [
        "Comece pela aba **Ajuda e Planos -> Introducao Guiada**.",
        "Siga a ordem: empresa e fiscal, financeiro obrigatorio, cadastros base, PDV/caixa, compras/estoque, modulos da operacao e validacao final.",
        "Os itens obrigatorios deixam o sistema pronto para vender e conferir dinheiro.",
        "Os itens condicionais aparecem quando a empresa usa modulo extra, como Entregas, Banho & Tosa, Veterinario, Ecommerce, Campanhas, WhatsApp ou Bling.",
      ],
    },
    {
      titulo: "Financeiro obrigatorio antes da primeira venda",
      tags: ["financeiro", "formas de pagamento", "bancos", "dre", "caixa"],
      conteudo: [
        "Antes da primeira venda real, confira **Bancos**, **Formas de Pagamento**, **Operadoras de Cartao**, **Categorias Financeiras** e **DRE**.",
        "Acesse **Cadastros -> Bancos** em `/cadastros/financeiro/bancos`.",
        "Acesse **Cadastros -> Formas de Pagamento** em `/cadastros/financeiro/formas-pagamento`.",
        "Acesse **Cadastros -> Operadoras de Cartao** em `/cadastros/financeiro/operadoras` se vender em cartao.",
        "Sem essa base, a venda ate pode acontecer, mas recebimentos, taxas e relatorios ficam menos confiaveis.",
      ],
    },
    {
      titulo: "Compras, entrada XML e Bling",
      tags: ["compras", "entrada xml", "bling", "estoque", "nota"],
      conteudo: [
        "Use **Compras -> Pedidos de Compra** em `/compras/pedidos` para controlar reposicao por fornecedor.",
        "Use **Compras -> Central NF-e Entradas** em `/compras/entrada-xml` para conferir XML, custos, frete, impostos, divergencias e estoque.",
        "Use **Produtos / Estoque -> Sinc. Bling** em `/produtos/sinc-bling` quando a empresa usa integracao Bling.",
        "Depois de processar uma entrada, confira o produto, o custo e o estoque antes de considerar a implantacao pronta.",
      ],
    },
    {
      titulo: "Configuracoes por modulo",
      tags: ["modulos", "ecommerce", "campanhas", "veterinario", "banho e tosa"],
      conteudo: [
        "Cada modulo tem configuracao propria e deve ser revisado somente quando estiver ativo para a empresa.",
        "Ecommerce: `/ecommerce/configuracoes` e `/ecommerce/aparencia`.",
        "Campanhas: `/campanhas`.",
        "Banho & Tosa: `/banho-tosa/servicos`, `/banho-tosa/parametros`, `/banho-tosa/agenda`.",
        "Veterinario: `/veterinario/configuracoes`, `/veterinario/agenda`, `/veterinario/catalogo`.",
        "Entregas: `/configuracoes/entregas` e `/entregas/abertas`.",
      ],
    },
  ],
},
```

- [ ] **Step 4: Run contract**

Run:

```powershell
cd frontend
npm run test:onboarding-inicial
```

Expected: PASS and `Onboarding inicial contract OK`.

- [ ] **Step 5: Commit**

Run:

```powershell
git add frontend/src/pages/centralAjuda/centralAjudaKnowledge.js frontend/scripts/test-onboarding-inicial-contract.mjs
git commit -m "docs: atualiza central de ajuda do onboarding"
```

---

### Task 6: Add Internal Implementation and Creative Docs

**Files:**
- Create: `docs/implantacao/GUIA_IMPLANTACAO_INICIAL.md`
- Create: `docs/marketing/MATRIZ_CRIATIVOS_SISTEMA.md`
- Modify: `docs/INDICE_OPERACIONAL.md`

- [ ] **Step 1: Create implementation guide**

Create `docs/implantacao/GUIA_IMPLANTACAO_INICIAL.md`:

```md
# Guia de Implantacao Inicial - Sistema Pet

Uso: checklist interno para Lucas/suporte configurar ou revisar uma conta nova.

## 1. Identificacao

- Cliente/tenant:
- Responsavel pela implantacao:
- Data de inicio:
- Plano:
- Modulos ativos:
- Pendencias bloqueantes:
- Pendencias nao bloqueantes:

## 2. Empresa e acesso

- [ ] Dados cadastrais conferidos em `/configuracoes`.
- [ ] Dados fiscais conferidos em `/configuracoes/fiscal`.
- [ ] Usuarios criados em `/admin/usuarios`.
- [ ] Permissoes revisadas em `/admin/roles`.
- [ ] Plano e modulos conferidos em `/meu-plano`.

## 3. Financeiro obrigatorio

- [ ] Bancos, caixas e carteiras conferidos em `/cadastros/financeiro/bancos`.
- [ ] Formas de pagamento conferidas em `/cadastros/financeiro/formas-pagamento`.
- [ ] Operadoras de cartao cadastradas em `/cadastros/financeiro/operadoras`, quando houver cartao.
- [ ] Categorias financeiras revisadas em `/cadastros/categorias-financeiras`.
- [ ] DRE e tipos de despesa revisados em `/financeiro/dre` e `/cadastros/tipos-despesa`.

## 4. Cadastros base

- [ ] Departamentos, categorias e marcas conferidos.
- [ ] Produtos cadastrados ou importados.
- [ ] Estoque inicial e estoque minimo revisados.
- [ ] Clientes, fornecedores, funcionarios, veterinarios e entregadores cadastrados conforme operacao.
- [ ] Pets cadastrados quando a operacao usa atendimento por tutor/pet.
- [ ] Especies, racas e opcoes de racao revisadas.

## 5. Operacao de venda

- [ ] Caixa aberto no PDV.
- [ ] Venda teste feita.
- [ ] Pagamento em dinheiro ou PIX testado.
- [ ] Pagamento em cartao testado quando houver operadora.
- [ ] Baixa de estoque conferida.
- [ ] Conta a receber conferida quando a forma de pagamento gera recebivel.
- [ ] Caixa fechado e diferenca conferida.

## 6. Modulos condicionais

- [ ] Entregas configurado quando ativo.
- [ ] Comissoes configurado quando ativo.
- [ ] Banho & Tosa configurado quando ativo.
- [ ] Veterinario configurado quando ativo.
- [ ] Ecommerce configurado quando ativo.
- [ ] Campanhas configurado quando ativo.
- [ ] WhatsApp configurado quando ativo.
- [ ] Bling configurado quando ativo.
- [ ] App mobile habilitado quando ativo.

## 7. Validacao final

- [ ] Fluxo de caixa conferido.
- [ ] DRE conferido.
- [ ] Relatorio de vendas conferido.
- [ ] Estoque conferido depois da venda teste.
- [ ] Usuario operacional testado sem acesso admin.
- [ ] Evidencias registradas: prints, video curto ou anotacao.

## 8. Observacoes comerciais

- Dor principal do cliente:
- Funcionalidades que mais geraram interesse:
- Modulos com potencial de venda:
- Criativos sugeridos para este perfil:
```

- [ ] **Step 2: Create creative matrix**

Create `docs/marketing/MATRIZ_CRIATIVOS_SISTEMA.md`:

```md
# Matriz de Criativos e Videos - Sistema Pet

Uso: base para gravar videos do sistema e criar criativos de venda.

## Videos demonstrativos

| Tema | Roteiro curto | Tela base | Duracao sugerida |
|---|---|---|---|
| Primeiros passos | Mostrar a Introducao Guiada e a ordem de configuracao | `/ajuda` | 45s |
| Financeiro pronto | Bancos, formas de pagamento, venda e contas a receber | `/cadastros/financeiro/formas-pagamento`, `/pdv`, `/financeiro/contas-receber` | 60s |
| PDV e estoque | Cadastrar produto, vender e conferir baixa de estoque | `/produtos`, `/pdv` | 60s |
| Compras e XML | Entrada XML atualizando custo e estoque | `/compras/entrada-xml` | 60s |
| Banho & Tosa | Servicos, agenda e fila do dia | `/banho-tosa/servicos`, `/banho-tosa/agenda`, `/banho-tosa/fila` | 45s |
| Veterinario | Agenda, prontuario e catalogos | `/veterinario/agenda`, `/veterinario/consultas`, `/veterinario/catalogo` | 60s |
| Ecommerce/App | Loja, catalogo e pedidos online | `/ecommerce/configuracoes`, `/ecommerce` | 45s |

## Criativos por dor

| Dor | Gancho | Funcionalidade mostrada | CTA |
|---|---|---|---|
| Nao sei se tive lucro | "Vender muito nao significa lucrar" | DRE e relatorio de vendas | "Veja seu lucro real no Sistema Pet" |
| Estoque some | "Produto saiu, mas ninguem sabe para onde" | PDV com baixa de estoque e alertas | "Controle seu estoque em tempo real" |
| Pagamentos baguncados | "Dinheiro, PIX e cartao no mesmo caixa?" | Formas de pagamento e contas a receber | "Organize seus recebimentos" |
| Agenda manual | "Banho e tosa no papel vira confusao" | Agenda e fila do banho/tosa | "Organize sua rotina de servicos" |
| Prontuario espalhado | "Historico clinico nao pode ficar perdido" | Modulo veterinario | "Centralize o atendimento veterinario" |
| Quer vender online | "Sua loja tambem pode vender fora do balcao" | Ecommerce e app | "Venda pelo app e pela loja online" |

## Dados ficticios para gravacao

- Cliente: Maria Oliveira.
- Pet: Thor.
- Produto: Racao Adulto 10kg.
- Forma de pagamento: PIX e Cartao de credito.
- Fornecedor: Distribuidora Pet Brasil.
- Servico banho/tosa: Banho medio completo.
- Consulta veterinaria: Avaliacao preventiva.
```

- [ ] **Step 3: Update operational index**

In `docs/INDICE_OPERACIONAL.md`, add a section or entries pointing to:

```md
- `docs/implantacao/GUIA_IMPLANTACAO_INICIAL.md`
- `docs/marketing/MATRIZ_CRIATIVOS_SISTEMA.md`
```

- [ ] **Step 4: Validate docs exist**

Run:

```powershell
Test-Path docs\implantacao\GUIA_IMPLANTACAO_INICIAL.md
Test-Path docs\marketing\MATRIZ_CRIATIVOS_SISTEMA.md
rg -n "GUIA_IMPLANTACAO_INICIAL|MATRIZ_CRIATIVOS_SISTEMA" docs\INDICE_OPERACIONAL.md
```

Expected: two `True` lines and at least one `rg` match for each new doc.

- [ ] **Step 5: Commit**

Run:

```powershell
git add docs/implantacao/GUIA_IMPLANTACAO_INICIAL.md docs/marketing/MATRIZ_CRIATIVOS_SISTEMA.md docs/INDICE_OPERACIONAL.md
git commit -m "docs: adiciona guia interno e matriz de criativos"
```

---

### Task 7: Final Verification

**Files:**
- Verify all modified files.

- [ ] **Step 1: Run focused frontend checks**

Run:

```powershell
cd frontend
npm run test:onboarding-inicial
node src/pages/introducaoGuiada/introducaoGuiadaChecks.test.mjs
npm run test:app-routes-refactor
npm run lint:core
npm run build
```

Expected:

- `test:onboarding-inicial`: prints `Onboarding inicial contract OK`.
- `introducaoGuiadaChecks.test.mjs`: all tests pass.
- `test:app-routes-refactor`: prints `App route refactor contract OK`.
- `lint:core`: exits with code 0.
- `build`: exits with code 0.

- [ ] **Step 2: Check Git scope**

Run:

```powershell
git status --short
git log --oneline -5
```

Expected:

- No unstaged source changes from this implementation.
- Recent commits show the onboarding plan and the task commits.
- Any unrelated user file, such as `app-mobile/app.json`, remains untouched and unstaged.

- [ ] **Step 3: Report result**

Tell Lucas:

- what changed in the guide;
- what changed in the Central de Ajuda;
- where the internal checklist is;
- where the creative matrix is;
- which verification commands passed;
- whether any unrelated local changes were left untouched.
