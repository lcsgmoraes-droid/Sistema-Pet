export function toNumber(value) {
  if (value == null || value === "") return 0;
  let normalized = String(value).trim();
  if (normalized.includes(",") && normalized.includes(".")) {
    normalized = normalized.lastIndexOf(",") > normalized.lastIndexOf(".")
      ? normalized.replace(/\./g, "").replace(",", ".")
      : normalized.replace(/,/g, "");
  } else if (normalized.includes(",")) {
    normalized = normalized.replace(",", ".");
  } else if ((normalized.match(/\./g) || []).length > 1) {
    const parts = normalized.split(".");
    normalized = `${parts.slice(0, -1).join("")}.${parts.at(-1)}`;
  }
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : 0;
}

export function roundMoney(value) {
  return Math.round((toNumber(value) + Number.EPSILON) * 100) / 100;
}

export function calcularMargem(precoTotal, custoTotal) {
  const margemValor = roundMoney(precoTotal - custoTotal);
  const margemPercentual = precoTotal > 0 ? roundMoney((margemValor / precoTotal) * 100) : 0;
  return { margem_valor: margemValor, margem_percentual: margemPercentual };
}

export function criarItemBaseOrcamento({
  origem = "manual",
  catalogo_id = null,
  produto_id = null,
  nome = "Item do orçamento",
  descricao = "",
  unidade = "",
  quantidade = 1,
  custo_unitario_estimado = 0,
  preco_unitario_sugerido = 0,
  preco_unitario,
  insumos = [],
  observacoes = "",
}) {
  const quantidadeNumerica = Math.max(toNumber(quantidade), 1);
  const custoUnitario = roundMoney(custo_unitario_estimado);
  const precoSugerido = roundMoney(preco_unitario_sugerido);
  const precoCobrado = roundMoney(preco_unitario ?? precoSugerido);
  const custoTotal = roundMoney(custoUnitario * quantidadeNumerica);
  const precoTotal = roundMoney(precoCobrado * quantidadeNumerica);
  const margem = calcularMargem(precoTotal, custoTotal);

  return {
    origem,
    catalogo_id,
    produto_id,
    nome,
    descricao,
    unidade,
    quantidade: quantidadeNumerica,
    custo_unitario_estimado: custoUnitario,
    preco_unitario_sugerido: precoSugerido,
    preco_unitario: precoCobrado,
    custo_total_estimado: custoTotal,
    preco_total: precoTotal,
    ...margem,
    insumos,
    observacoes,
  };
}

export function criarItemCatalogoOrcamento(catalogo, quantidade = 1, precoUnitario) {
  return criarItemBaseOrcamento({
    origem: "catalogo",
    catalogo_id: catalogo?.id ?? null,
    nome: catalogo?.nome || "Procedimento",
    descricao: catalogo?.descricao || "",
    quantidade,
    custo_unitario_estimado: catalogo?.custo_estimado || 0,
    preco_unitario_sugerido: catalogo?.valor_padrao || 0,
    preco_unitario: precoUnitario,
    insumos: Array.isArray(catalogo?.insumos) ? catalogo.insumos : [],
  });
}

export function criarItemProdutoOrcamento(produto, quantidade = 1, precoUnitario) {
  return criarItemBaseOrcamento({
    origem: "produto",
    produto_id: produto?.id ?? null,
    nome: produto?.nome || "Produto",
    unidade: produto?.unidade || "",
    quantidade,
    custo_unitario_estimado: produto?.preco_custo || 0,
    preco_unitario_sugerido: produto?.preco_venda || 0,
    preco_unitario: precoUnitario,
  });
}

export function criarItemDiariaOrcamento({ nome, custo_unitario_estimado, preco_unitario, dias }) {
  return criarItemBaseOrcamento({
    origem: "diaria",
    nome: nome || "Internação",
    unidade: "dia",
    quantidade: dias || 1,
    custo_unitario_estimado,
    preco_unitario_sugerido: preco_unitario,
    preco_unitario,
  });
}

export function recalcularItemOrcamento(item, updates = {}) {
  return criarItemBaseOrcamento({ ...item, ...updates });
}

export function calcularTotaisOrcamento(itens) {
  const custoTotal = roundMoney((itens || []).reduce((total, item) => total + toNumber(item.custo_total_estimado), 0));
  const precoTotal = roundMoney((itens || []).reduce((total, item) => total + toNumber(item.preco_total), 0));
  const margem = calcularMargem(precoTotal, custoTotal);
  return {
    custo_total_estimado: custoTotal,
    preco_total: precoTotal,
    ...margem,
  };
}
