export const SEM_VENDEDOR = "sem-vendedor";

export function chaveVendedor(venda) {
  return venda.vendedor_funcionario_id == null
    ? SEM_VENDEDOR
    : String(venda.vendedor_funcionario_id);
}

function valorBrutoItem(item) {
  return item.venda_bruta == null
    ? Number(item.quantidade || 0) * Number(item.preco_unitario || 0)
    : Number(item.venda_bruta);
}

function quantidadeItens(itens) {
  return itens.reduce((total, item) => total + Number(item.quantidade || 0), 0);
}

export function opcoesProdutosVendas(vendas = []) {
  const produtos = new Map();
  for (const venda of vendas) {
    for (const item of venda.itens || []) {
      if (item.produto_id == null || item.produto_id === "") continue;
      const value = String(item.produto_id);
      if (!produtos.has(value)) {
        produtos.set(value, {
          value,
          label: `${item.produto_nome || "Produto removido"} (#${value})`,
        });
      }
    }
  }
  return [...produtos.values()].sort((a, b) => a.label.localeCompare(b.label, "pt-BR"));
}

export function agruparVendasPorVendedor(vendas = [], produtoId = "") {
  const filtrarProduto = produtoId !== "" && produtoId != null;
  const grupos = new Map();
  for (const venda of vendas) {
    const itens = filtrarProduto
      ? (venda.itens || []).filter(
          (item) => item.produto_id != null && String(item.produto_id) === String(produtoId),
        )
      : [...(venda.itens || [])];
    if (filtrarProduto && !itens.length) continue;
    const totalRelatorio = filtrarProduto
      ? Math.round(itens.reduce((total, item) => total + valorBrutoItem(item), 0) * 100) / 100
      : Number(venda.total_venda || 0);
    const chave = chaveVendedor(venda);
    if (!grupos.has(chave)) {
      grupos.set(chave, {
        chave,
        vendedor: venda.vendedor_nome || "Sem vendedor",
        quantidade: 0,
        quantidadeProdutos: 0,
        total: 0,
        vendas: [],
      });
    }
    const grupo = grupos.get(chave);
    grupo.quantidade += 1;
    grupo.quantidadeProdutos += quantidadeItens(itens);
    grupo.total += totalRelatorio;
    grupo.vendas.push({ ...venda, itens, total_relatorio: totalRelatorio });
  }
  return [...grupos.values()]
    .map((grupo) => ({
      ...grupo,
      total: Math.round(grupo.total * 100) / 100,
      quantidadeProdutos: Math.round(grupo.quantidadeProdutos * 1000) / 1000,
    }))
    .sort((a, b) => b.total - a.total || a.vendedor.localeCompare(b.vendedor));
}

export function planilhasVendasPorVendedor(grupos, periodo, produto = null) {
  const resumo = [
    produto
      ? [
          "Vendedor",
          "Quantidade de vendas",
          "Quantidade do produto",
          "Valor bruto do produto",
          "Produto",
          "Período inicial",
          "Período final",
        ]
      : ["Vendedor", "Quantidade de vendas", "Total vendido", "Período inicial", "Período final"],
    ...grupos.map((grupo) => [
      grupo.vendedor,
      grupo.quantidade,
      ...(produto ? [grupo.quantidadeProdutos] : []),
      grupo.total,
      ...(produto ? [produto.label] : []),
      periodo.inicio,
      periodo.fim,
    ]),
  ];
  const vendas = [
    produto
      ? [
          "Vendedor",
          "Data",
          "Número da venda",
          "Cliente",
          "Quantidade do produto",
          "Valor bruto do produto",
        ]
      : ["Vendedor", "Data", "Número da venda", "Cliente", "Total da venda"],
  ];
  const produtos = [
    [
      "Vendedor",
      "Número da venda",
      "Produto",
      "Quantidade",
      "Preço unitário",
      produto ? "Valor bruto do produto" : "Valor bruto",
    ],
  ];
  for (const grupo of grupos) {
    for (const venda of grupo.vendas) {
      vendas.push([
        grupo.vendedor,
        venda.data_venda,
        venda.numero_venda,
        venda.cliente_nome,
        ...(produto
          ? [Math.round(quantidadeItens(venda.itens || []) * 1000) / 1000, venda.total_relatorio]
          : [Number(venda.total_venda || 0)]),
      ]);
      for (const item of venda.itens || []) {
        produtos.push([
          grupo.vendedor,
          venda.numero_venda,
          item.produto_nome || "Produto removido",
          Number(item.quantidade || 0),
          Number(item.preco_unitario || 0),
          produto ? valorBrutoItem(item) : Number(item.venda_bruta || 0),
        ]);
      }
    }
  }
  return [
    { sheet: "Resumo por vendedor", linhas: resumo },
    { sheet: "Vendas", linhas: vendas },
    { sheet: "Produtos por venda", linhas: produtos },
  ];
}
