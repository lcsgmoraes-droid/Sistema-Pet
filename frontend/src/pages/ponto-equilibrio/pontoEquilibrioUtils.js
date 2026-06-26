import { formatMoneyBRL, formatPercent } from "../../utils/formatters";
import { LINHAS_CLASSIFICACAO_PE } from "./pontoEquilibrioConstants";

export function formatarDataInput(data) {
  const local = new Date(data.getTime() - data.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 10);
}

export function inicioMesAtual() {
  const hoje = new Date();
  return formatarDataInput(new Date(hoje.getFullYear(), hoje.getMonth(), 1));
}

export function fimMesAtual() {
  const hoje = new Date();
  return formatarDataInput(new Date(hoje.getFullYear(), hoje.getMonth() + 1, 0));
}

export function buildInitialFilters() {
  return {
    data_inicio: inicioMesAtual(),
    data_fim: fimMesAtual(),
    canal: "",
    fonte_margem: "media_12_meses_fechados",
    modo_custo_fiscal: "gerencial_completo",
  };
}

export function formatarDataBR(data) {
  if (!data) return "-";
  const [ano, mes, dia] = String(data).split("T")[0].split("-");
  if (!ano || !mes || !dia) return data;
  return `${dia}/${mes}/${ano}`;
}

export function linhaValorClassName(tipo) {
  if (tipo === "receita") return "text-emerald-700";
  if (tipo === "alerta") return "text-amber-700";
  if (tipo === "informativo") return "text-slate-700";
  return "text-red-700";
}

export function montarLinhasDetalhamentoPontoEquilibrio(dados) {
  const subtotais = dados?.detalhes_margem?.subtotais || [];
  const linhasMargem = subtotais
    .filter(
      (subtotal) => Math.abs(Number(subtotal.valor || 0)) > 0 || subtotal.id === "custo_fiscal",
    )
    .map((subtotal) => ({
      ...subtotal,
      grupo: subtotal.id,
      origem: "Snapshot financeiro das vendas",
    }));

  const linhasClassificacao = LINHAS_CLASSIFICACAO_PE.map((linha) => ({
    ...linha,
    grupo: linha.id,
    valor: Number(dados?.[linha.valorKey] || 0),
  })).filter((linha) => Math.abs(Number(linha.valor || 0)) > 0 || linha.id === "sem_classificacao");

  return [...linhasMargem, ...linhasClassificacao];
}

export function formatarImpactoMoeda(valor) {
  if (valor == null) return "-";
  if (valor > 0) return `+ ${formatMoneyBRL(valor)}`;
  if (valor < 0) return `- ${formatMoneyBRL(Math.abs(valor))}`;
  return formatMoneyBRL(0);
}

export function formatarImpactoVendas(valor) {
  if (valor == null) return "-";
  if (valor > 0) return `+${valor}`;
  return String(valor);
}

export function formatarVariacaoPercentual(valor) {
  if (valor == null) return "-";
  if (valor > 0) return `+${formatPercent(valor)}`;
  return formatPercent(valor);
}

export function statusParecerClasses(status) {
  if (status === "saudavel") return "border-emerald-200 bg-emerald-50 text-emerald-800";
  if (status === "atencao") return "border-amber-200 bg-amber-50 text-amber-800";
  return "border-red-200 bg-red-50 text-red-800";
}

export function statusParecerLabel(status) {
  if (status === "saudavel") return "Saudavel";
  if (status === "atencao") return "Atencao";
  return "Acima do ideal";
}

export function statusParecerLabelGerencial(parecer) {
  if (parecer.id === "total_fixo") return statusParecerLabel(parecer.status);
  if (parecer.status === "saudavel") return "Dentro da meta";
  if (parecer.status === "atencao") return "Pressiona total";
  return "Acima da referencia";
}

export function getStatusResumo(dados) {
  if (!dados) return null;
  if (dados.status === "atingido") {
    return {
      tone: "green",
      title: "Ponto de Equilibrio atingido",
      text: `A empresa ja faturou ${formatMoneyBRL(dados.faturamento)} no periodo e passou do minimo estimado.`,
    };
  }
  if (dados.status === "nao_atingido") {
    return {
      tone: "amber",
      title: "Ainda falta faturar",
      text: `Faltam ${formatMoneyBRL(dados.falta_faturar || 0)} para cobrir os custos fixos pela margem usada.`,
    };
  }
  if (dados.status === "margem_insuficiente") {
    return {
      tone: "red",
      title: "Margem insuficiente",
      text: "O faturamento existe, mas os custos variaveis estao consumindo a margem de contribuicao.",
    };
  }
  return {
    tone: "slate",
    title: "Sem faturamento no periodo",
    text: "Selecione um periodo com vendas para calcular a margem.",
  };
}

export function montarParametrosPontoEquilibrio(filtros, extras = {}) {
  const params = {
    data_inicio: filtros.data_inicio,
    data_fim: filtros.data_fim,
    fonte_margem: filtros.fonte_margem,
    modo_custo_fiscal: filtros.modo_custo_fiscal,
    ...extras,
  };
  if (filtros.canal) {
    params.canais = filtros.canal;
  }
  return params;
}
