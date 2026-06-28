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
    [
      "empresaFiscal",
      async () => {
        const { data = {} } = await api.get("/empresa/fiscal");
        return Boolean(
          data.regime_tributario || data.cnae_principal || data.aliquota_simples_vigente,
        );
      },
    ],
    [
      "empresaDados",
      async () => {
        const { data = {} } = await api.get("/empresa/dados-cadastrais");
        return Boolean(
          data.cnpj &&
            data.razao_social &&
            data.endereco &&
            data.numero &&
            data.bairro &&
            data.cidade &&
            data.uf,
        );
      },
    ],
    ["usuarios", async () => toCount((await api.get("/usuarios?limit=2")).data) > 1],
    [
      "contasBancarias",
      async () => toCount((await api.get("/contas-bancarias?apenas_ativas=true")).data) > 0,
    ],
    [
      "formasPagamento",
      async () =>
        toCount((await api.get("/financeiro/formas-pagamento?apenas_ativas=true")).data) > 0,
    ],
    [
      "operadoras",
      async () => toCount((await api.get("/operadoras-cartao?apenas_ativas=true")).data) > 0,
    ],
    [
      "categoriasFinanceiras",
      async () => toCount((await api.get("/financeiro/categorias")).data) > 0,
    ],
    [
      "dreBase",
      async () => {
        const categorias = toCount((await api.get("/dre/categorias")).data);
        const subcategorias = toCount((await api.get("/dre/subcategorias")).data);
        return categorias > 0 && subcategorias > 0;
      },
    ],
    [
      "categoriasProduto",
      async () => toCount((await api.get("/produtos/categorias")).data) > 0,
    ],
    [
      "produtos",
      async () => {
        const { data = {} } = await api.get("/produtos?per_page=1");
        return Boolean((Array.isArray(data.produtos) && data.produtos.length > 0) || data.total > 0);
      },
    ],
    [
      "estoqueMinimo",
      async () =>
        toCount((await api.get("/produtos?per_page=1&estoque_minimo_configurado=true")).data) > 0,
    ],
    ["pessoas", async () => toCount((await api.get("/clientes/?limit=1")).data) > 0],
    [
      "fornecedores",
      async () => toCount((await api.get("/clientes/?tipo=fornecedor&limit=1")).data) > 0,
    ],
    ["pets", async () => toCount((await api.get("/pets?limit=1")).data) > 0],
    [
      "opcoesRacao",
      async () => toCount((await api.get("/opcoes-racao/linhas?apenas_ativos=false")).data) > 0,
    ],
    ["caixaAberto", async () => Boolean((await api.get("/caixas/aberto")).data?.id)],
    [
      "temVendas",
      async () => Number((await api.get("/vendas?page=1&per_page=1")).data?.total || 0) > 0,
    ],
    [
      "pedidoCompra",
      async () => toCount((await api.get("/compras/pedidos?limit=1")).data) > 0,
    ],
    [
      "entradaXml",
      async () => toCount((await api.get("/compras/entrada-xml?limit=1")).data) > 0,
    ],
    ["blingConfig", async () => toCount((await api.get("/bling/status")).data) > 0],
    [
      "configEntrega",
      async () => Object.keys((await api.get("/configuracoes/entregas")).data || {}).length > 0,
    ],
    [
      "entregadores",
      async () =>
        toCount((await api.get("/clientes/?is_entregador=true&incluir_inativos=false&limit=1")).data) >
        0,
    ],
    [
      "comissoesConfig",
      async () => {
        const lista = (await api.get("/comissoes/configuracoes/funcionarios")).data?.data || [];
        return lista.some((funcionario) => Number(funcionario.total_configuracoes || 0) > 0);
      },
    ],
    [
      "banhoTosaServicos",
      async () => toCount((await api.get("/banho-tosa/servicos?limit=1")).data) > 0,
    ],
    [
      "vetConfig",
      async () => Object.keys((await api.get("/veterinario/configuracoes")).data || {}).length > 0,
    ],
    [
      "ecommerceConfig",
      async () => Object.keys((await api.get("/ecommerce-config")).data || {}).length > 0,
    ],
    ["campanhas", async () => toCount((await api.get("/campanhas?limit=1")).data) > 0],
    [
      "whatsappConfig",
      async () => Object.keys((await api.get("/whatsapp/config")).data || {}).length > 0,
    ],
  ];

  await Promise.all(
    tarefas.map(async ([key, fn]) => {
      checks[key] = await safeCheck(fn);
    }),
  );

  return checks;
}
