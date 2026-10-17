export const SEM_VENDEDOR = "sem-vendedor";

export function chaveVendedor(venda) {
  return venda.vendedor_funcionario_id == null
    ? SEM_VENDEDOR
    : String(venda.vendedor_funcionario_id);
}

export function agruparVendasPorVendedor(vendas = []) {
  const grupos = new Map();
  for (const venda of vendas) {
    const chave = chaveVendedor(venda);
    if (!grupos.has(chave)) {
      grupos.set(chave, {
        chave,
        vendedor: venda.vendedor_nome || "Sem vendedor",
        quantidade: 0,
        total: 0,
        vendas: [],
      });
    }
    const grupo = grupos.get(chave);
    grupo.quantidade += 1;
    grupo.total += Number(venda.total_venda || 0);
    grupo.vendas.push(venda);
  }
  return [...grupos.values()]
    .map((grupo) => ({ ...grupo, total: Math.round(grupo.total * 100) / 100 }))
    .sort((a, b) => b.total - a.total || a.vendedor.localeCompare(b.vendedor));
}

export function planilhasVendasPorVendedor(grupos, periodo) {
  const resumo = [
    ["Vendedor", "Quantidade de vendas", "Total vendido", "Período inicial", "Período final"],
    ...grupos.map((grupo) => [
      grupo.vendedor,
      grupo.quantidade,
      grupo.total,
      periodo.inicio,
      periodo.fim,
    ]),
  ];
  const vendas = [["Vendedor", "Data", "Número da venda", "Cliente", "Total da venda"]];
  const produtos = [
    ["Vendedor", "Número da venda", "Produto", "Quantidade", "Preço unitário", "Valor bruto"],
  ];
  for (const grupo of grupos) {
    for (const venda of grupo.vendas) {
      vendas.push([
        grupo.vendedor,
        venda.data_venda,
        venda.numero_venda,
        venda.cliente_nome,
        Number(venda.total_venda || 0),
      ]);
      for (const item of venda.itens || []) {
        produtos.push([
          grupo.vendedor,
          venda.numero_venda,
          item.produto_nome || "Produto removido",
          Number(item.quantidade || 0),
          Number(item.preco_unitario || 0),
          Number(item.venda_bruta || 0),
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
