export const CANAIS = [
  { value: "", label: "Todos os canais" },
  { value: "loja_fisica", label: "Loja fisica" },
  { value: "mercado_livre", label: "Mercado Livre" },
  { value: "shopee", label: "Shopee" },
  { value: "amazon", label: "Amazon" },
  { value: "site", label: "Site" },
];

export const MARGEM_PONTO_EQUILIBRIO_OPCOES = [
  { value: "media_12_meses_fechados", label: "Media 12 meses fechados" },
  { value: "media_6_meses_fechados", label: "Media 6 meses fechados" },
  { value: "media_3_meses_fechados", label: "Media 3 meses fechados" },
  { value: "mes_anterior_fechado", label: "Mes anterior fechado" },
  { value: "periodo_atual", label: "Periodo atual" },
];

export const MODO_CUSTO_FISCAL_OPCOES = [
  { value: "gerencial_completo", label: "Visao gerencial completa" },
  { value: "documentos_emitidos", label: "Somente documentos emitidos" },
];

export const CENARIOS_RAPIDOS = [
  { descricao: "Aumento aluguel", valor: "1000", faturamento: "" },
  { descricao: "Novo funcionario", valor: "3000", faturamento: "" },
  { descricao: "Reducao de custo", valor: "-500", faturamento: "" },
];

export const ABAS_PONTO_EQUILIBRIO = [
  { id: "resumo", label: "Resumo" },
  { id: "detalhamento", label: "Detalhamento" },
  { id: "simulador", label: "Simulador" },
  { id: "graficos", label: "Graficos" },
];

export const TOOLTIP_FAIXAS_PORTE =
  "Faixas gerenciais mensais: Pequeno ate R$ 80 mil/mes; Medio de R$ 80 mil a R$ 250 mil/mes; Grande acima de R$ 250 mil/mes. Use como parametro interno, nao como enquadramento fiscal.";

export const CORES_GRAFICO_CUSTOS = [
  "#2563eb",
  "#059669",
  "#d97706",
  "#7c3aed",
  "#dc2626",
  "#0891b2",
  "#64748b",
];

export const PONTO_EQUILIBRIO_REQUEST_TIMEOUT_MS = 120000;

export const DEFAULT_IMPACTO_FORM = {
  descricao: "",
  valor: "",
  faturamento: "",
};

export const LINHAS_CLASSIFICACAO_PE = [
  {
    id: "fixas",
    label: "Despesas fixas",
    tipo: "custo",
    valorKey: "despesas_fixas",
    origem: "Contas a pagar, DRE e folha gerencial",
  },
  {
    id: "variaveis",
    label: "Outros custos variaveis",
    tipo: "deducao",
    valorKey: "outros_variaveis",
    origem: "Contas/DRE fora do snapshot da venda",
  },
  {
    id: "custos_venda_snapshot",
    label: "Custos de venda ja no snapshot",
    tipo: "informativo",
    valorKey: "despesas_variaveis_ja_cobertas",
    origem: "Separados para nao duplicar custos",
  },
  {
    id: "sem_classificacao",
    label: "Sem classificacao",
    tipo: "alerta",
    valorKey: "despesas_sem_classificacao",
    origem: "Contas que precisam de classificacao",
  },
  {
    id: "estoque_excluido",
    label: "Fora do PE",
    tipo: "informativo",
    valorKey: "despesas_estoque_excluidas",
    origem: "Compra de estoque entra via CMV",
  },
];
