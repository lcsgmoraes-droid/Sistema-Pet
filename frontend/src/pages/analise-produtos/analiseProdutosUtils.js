export const PERIODOS_ANALISE = [
  { id: "7dias", label: "7 dias", dias: 7 },
  { id: "30dias", label: "30 dias", dias: 30 },
  { id: "90dias", label: "90 dias", dias: 90 },
  { id: "ano", label: "Este ano", dias: null },
  { id: "personalizado", label: "Personalizado", dias: null },
];

export const CANAIS_VENDA = [
  { value: "", label: "Todos os canais" },
  { value: "loja_fisica", label: "Loja física" },
  { value: "site", label: "Site" },
  { value: "app", label: "Aplicativo" },
  { value: "mercado_livre", label: "Mercado Livre" },
  { value: "shopee", label: "Shopee" },
  { value: "amazon", label: "Amazon" },
  { value: "instagram", label: "Instagram" },
];

function dataLocalIso(data) {
  const ano = data.getFullYear();
  const mes = String(data.getMonth() + 1).padStart(2, "0");
  const dia = String(data.getDate()).padStart(2, "0");
  return `${ano}-${mes}-${dia}`;
}

export function criarPeriodo(dias = 30) {
  const fim = new Date();
  const inicio = new Date(fim);
  inicio.setDate(inicio.getDate() - Math.max(dias - 1, 0));
  return { data_inicio: dataLocalIso(inicio), data_fim: dataLocalIso(fim) };
}

export function criarPeriodoAnoAtual() {
  const hoje = new Date();
  return {
    data_inicio: `${hoje.getFullYear()}-01-01`,
    data_fim: dataLocalIso(hoje),
  };
}

export function criarFiltrosAnalise() {
  return {
    ...criarPeriodo(30),
    categoria_id: "",
    marca_id: "",
    departamento_id: "",
    fornecedor_id: "",
    canal: "",
    busca: "",
  };
}

export function normalizarAnalise(payload = {}) {
  return {
    periodo: payload.periodo || {},
    resumo: payload.resumo || { comparacao: {}, variacoes: {} },
    evolucao: Array.isArray(payload.evolucao) ? payload.evolucao : [],
    produtos: Array.isArray(payload.produtos) ? payload.produtos : [],
    metadados: payload.metadados || {},
  };
}

export function agruparProdutos(produtos, dimensao) {
  const idCampo = `${dimensao}_id`;
  const nomeCampo = `${dimensao}_nome`;
  const grupos = new Map();

  for (const produto of produtos || []) {
    const id = produto[idCampo] ?? "sem-grupo";
    const nome = produto[nomeCampo] || `Sem ${dimensao}`;
    const atual = grupos.get(id) || {
      id,
      nome,
      produtos: 0,
      quantidade: 0,
      faturamento: 0,
      lucro_estimado: 0,
    };
    atual.produtos += 1;
    atual.quantidade += Number(produto.quantidade || 0);
    atual.faturamento += Number(produto.faturamento || 0);
    atual.lucro_estimado += Number(produto.lucro_estimado || 0);
    grupos.set(id, atual);
  }

  const total = [...grupos.values()].reduce((soma, grupo) => soma + grupo.faturamento, 0);
  return [...grupos.values()]
    .map((grupo) => ({
      ...grupo,
      quantidade: Number(grupo.quantidade.toFixed(3)),
      faturamento: Number(grupo.faturamento.toFixed(2)),
      lucro_estimado: Number(grupo.lucro_estimado.toFixed(2)),
      participacao_pct: total ? Number(((grupo.faturamento / total) * 100).toFixed(2)) : 0,
    }))
    .sort((a, b) => b.faturamento - a.faturamento);
}

export function resumirCurvaAbc(produtos, base = "faturamento") {
  const campoClasse = `abc_${base}`;
  const campoValor = base;
  const total = (produtos || []).reduce((soma, item) => soma + Number(item[campoValor] || 0), 0);
  return ["A", "B", "C"].map((classe) => {
    const itens = (produtos || []).filter((item) => item[campoClasse] === classe);
    const valor = itens.reduce((soma, item) => soma + Number(item[campoValor] || 0), 0);
    return {
      classe,
      produtos: itens.length,
      valor,
      participacao_pct: total ? (valor / total) * 100 : 0,
    };
  });
}

function escaparCsv(valor) {
  const texto = String(valor ?? "");
  return `"${texto.replaceAll('"', '""')}"`;
}

export function gerarCsvProdutos(produtos) {
  const cabecalho = [
    "Produto",
    "Código",
    "Categoria",
    "Marca",
    "Quantidade",
    "Faturamento",
    "Lucro estimado",
    "Margem estimada (%)",
    "ABC faturamento",
    "ABC quantidade",
    "Estoque atual",
    "Cobertura (dias)",
  ];
  const linhas = (produtos || []).map((item) => [
    item.produto_nome,
    item.codigo,
    item.categoria_nome,
    item.marca_nome,
    item.quantidade,
    item.faturamento,
    item.lucro_estimado,
    item.margem_estimada_pct,
    item.abc_faturamento,
    item.abc_quantidade,
    item.estoque_atual,
    item.cobertura_estoque_dias ?? "",
  ]);
  return [cabecalho, ...linhas].map((linha) => linha.map(escaparCsv).join(";")).join("\n");
}
