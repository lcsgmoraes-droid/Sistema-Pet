export const EXTRATO_COLUNAS = [
  { chave: "agrupador", titulo: "Lancamento" },
  { chave: "origem_label", titulo: "Origem" },
  { chave: "data_hora", titulo: "Data" },
  { chave: "referencia", titulo: "Ref." },
  { chave: "codigo", titulo: "Codigo" },
  { chave: "nome", titulo: "Descricao" },
  { chave: "quantidade", titulo: "Qtd." },
  { chave: "unidade", titulo: "Un." },
  { chave: "custo_unitario", titulo: "Custo un." },
  { chave: "custo_total", titulo: "Custo" },
  { chave: "preco_unitario", titulo: "Venda un." },
  { chave: "preco_total", titulo: "Venda" },
  { chave: "margem_valor", titulo: "Margem" },
  { chave: "margem_percentual", titulo: "Margem %" },
  { chave: "contabilizar_label", titulo: "Total" },
  { chave: "estoque_baixado_label", titulo: "Estoque" },
];

export const EXTRATO_COLUNAS_DEFAULT = [
  "agrupador",
  "origem_label",
  "nome",
  "quantidade",
  "unidade",
  "custo_total",
  "preco_total",
  "margem_valor",
  "contabilizar_label",
];

const COLUNAS_VALIDAS = new Set(EXTRATO_COLUNAS.map((coluna) => coluna.chave));

export function normalizarColunasSelecionadas(colunas) {
  const candidatos = Array.isArray(colunas) ? colunas : String(colunas || "").split(",");
  const validas = [];
  candidatos.forEach((coluna) => {
    const chave = String(coluna || "").trim();
    if (COLUNAS_VALIDAS.has(chave) && !validas.includes(chave)) {
      validas.push(chave);
    }
  });
  return validas.length ? validas : [...EXTRATO_COLUNAS_DEFAULT];
}

export function buildExtratoParams(contexto = {}, colunas = EXTRATO_COLUNAS_DEFAULT) {
  const params = {};
  if (contexto.consultaId) params.consulta_id = Number(contexto.consultaId);
  if (contexto.internacaoId) params.internacao_id = Number(contexto.internacaoId);
  const colunasNormalizadas = normalizarColunasSelecionadas(colunas);
  if (colunasNormalizadas.length) {
    params.colunas = colunasNormalizadas.join(",");
  }
  return params;
}

export function resumirLinhasExtrato(linhas = []) {
  return linhas.reduce((acc, linha) => {
    if (linha?.contabilizar_total) {
      acc.contabilizadas += 1;
    } else {
      acc.detalhes += 1;
    }
    return acc;
  }, { contabilizadas: 0, detalhes: 0 });
}

export function buildExtratoDownloadName(contexto = {}, formato = "pdf") {
  if (contexto.consultaId) {
    return `extrato_veterinario_consulta_${contexto.consultaId}.${formato}`;
  }
  if (contexto.internacaoId) {
    return `extrato_veterinario_internacao_${contexto.internacaoId}.${formato}`;
  }
  return `extrato_veterinario_atendimento.${formato}`;
}

export function downloadBlob(blob, nomeArquivo) {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = nomeArquivo;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
