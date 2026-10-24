import { formatBRL, formatMoneyBRL } from "../../utils/formatters";

export const IFOOD_FILTROS = [
  { value: "todos", label: "Todos os produtos" },
  { value: "selecionados", label: "Selecionados para o iFood" },
  { value: "pendencias", label: "Com pendências" },
  { value: "sem_estoque", label: "Sem estoque disponível" },
  { value: "preco_especifico", label: "Com preço específico" },
  { value: "nao_selecionados", label: "Fora da seleção" },
];

export const IFOOD_MODALIDADES = [
  { valor: "MERCHANT", rotulo: "Entrega própria" },
  { valor: "IFOOD", rotulo: "Entrega iFood" },
];

export const IFOOD_STATUS = {
  pronto_para_envio: {
    label: "Pronto para envio",
    className: "bg-emerald-50 text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-200",
  },
  pendente: {
    label: "Com pendências",
    className: "bg-amber-50 text-amber-800 dark:bg-amber-500/15 dark:text-amber-200",
  },
  pausado: {
    label: "Pausa local",
    className: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  },
  sem_estoque: {
    label: "Sem estoque",
    className: "bg-amber-50 text-amber-800 dark:bg-amber-500/15 dark:text-amber-200",
  },
  nao_selecionado: {
    label: "Fora da seleção",
    className: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
  },
};

export const IFOOD_PENDING_LABELS = {
  bloqueio: "Impede o envio",
  operacional: "Disponibilidade",
  rentabilidade: "Rentabilidade",
  recomendacao: "Recomendação",
};

export function statusEnvioIfood(status) {
  return (
    {
      sending: "Envio em andamento — resultado ainda não confirmado",
      accepted: "Aceito pela API — confira no Portal",
      error: "Falha no envio",
      uncertain: "Resultado do envio desconhecido — confira no Portal",
      nao_enviado: "Nenhum envio registrado neste acompanhamento",
    }[status || "nao_enviado"] || "Situação do envio a conferir"
  );
}

export function valorConhecido(value) {
  return value !== null && value !== undefined && value !== "" && Number.isFinite(Number(value));
}

// Os formatadores do ERP convertem null em zero. Aqui, null significa desconhecido.
export function moedaIfood(value) {
  return valorConhecido(value) ? formatMoneyBRL(value) : "Não informado";
}

export function percentualIfood(value) {
  return valorConhecido(value) ? `${formatBRL(value)}%` : "Não informado";
}

export function mensagemErroIfood(error, fallback) {
  if (error?.response?.status === 403) {
    return "Você não tem permissão para esta ação. Solicite acesso ao administrador da loja.";
  }
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
  return fallback;
}
