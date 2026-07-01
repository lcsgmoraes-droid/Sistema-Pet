const ACTION_INTENTS = {
  create: {
    solid:
      "border-emerald-600 bg-emerald-600 text-white hover:bg-emerald-700 dark:border-emerald-700 dark:bg-emerald-700 dark:hover:bg-emerald-800",
    soft:
      "border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 dark:border-emerald-400/30 dark:bg-emerald-500/10 dark:text-emerald-200 dark:hover:bg-emerald-500/20",
    ghost:
      "border-transparent bg-transparent text-emerald-700 hover:bg-emerald-50 dark:text-emerald-200 dark:hover:bg-emerald-500/10",
  },
  edit: {
    solid:
      "border-blue-600 bg-blue-600 text-white hover:bg-blue-700 dark:border-blue-700 dark:bg-blue-700 dark:hover:bg-blue-800",
    soft:
      "border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100 dark:border-blue-400/30 dark:bg-blue-500/10 dark:text-blue-200 dark:hover:bg-blue-500/20",
    ghost:
      "border-transparent bg-transparent text-blue-700 hover:bg-blue-50 dark:text-blue-200 dark:hover:bg-blue-500/10",
  },
  delete: {
    solid:
      "border-red-600 bg-red-600 text-white hover:bg-red-700 dark:border-red-700 dark:bg-red-700 dark:hover:bg-red-800",
    soft:
      "border-red-200 bg-red-50 text-red-700 hover:bg-red-100 dark:border-red-400/30 dark:bg-red-500/10 dark:text-red-200 dark:hover:bg-red-500/20",
    ghost:
      "border-transparent bg-transparent text-red-700 hover:bg-red-50 dark:text-red-200 dark:hover:bg-red-500/10",
  },
  neutral: {
    solid: "border-slate-900 bg-slate-900 text-white hover:bg-slate-700 dark:border-slate-600 dark:bg-slate-700 dark:hover:bg-slate-600",
    soft:
      "border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800",
    ghost:
      "border-transparent bg-transparent text-slate-600 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800",
  },
  warning: {
    solid:
      "border-amber-600 bg-amber-600 text-white hover:bg-amber-700 dark:border-amber-700 dark:bg-amber-700 dark:hover:bg-amber-800",
    soft:
      "border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100 dark:border-amber-400/30 dark:bg-amber-500/10 dark:text-amber-200 dark:hover:bg-amber-500/20",
    ghost:
      "border-transparent bg-transparent text-amber-700 hover:bg-amber-50 dark:text-amber-200 dark:hover:bg-amber-500/10",
  },
  info: {
    solid:
      "border-cyan-600 bg-cyan-600 text-white hover:bg-cyan-700 dark:border-cyan-700 dark:bg-cyan-700 dark:hover:bg-cyan-800",
    soft:
      "border-cyan-200 bg-cyan-50 text-cyan-700 hover:bg-cyan-100 dark:border-cyan-400/30 dark:bg-cyan-500/10 dark:text-cyan-200 dark:hover:bg-cyan-500/20",
    ghost:
      "border-transparent bg-transparent text-cyan-700 hover:bg-cyan-50 dark:text-cyan-200 dark:hover:bg-cyan-500/10",
  },
  pdf: {
    solid:
      "border-red-600 bg-red-600 text-white hover:bg-red-700 dark:border-red-700 dark:bg-red-700 dark:hover:bg-red-800",
    soft:
      "border-red-200 bg-red-50 text-red-700 hover:bg-red-100 dark:border-red-400/30 dark:bg-red-500/10 dark:text-red-200 dark:hover:bg-red-500/20",
    ghost:
      "border-transparent bg-transparent text-red-700 hover:bg-red-50 dark:text-red-200 dark:hover:bg-red-500/10",
  },
};

const ACTION_SIZES = {
  xs: "h-7 gap-1 rounded-md px-2.5 text-xs",
  sm: "h-8 gap-1.5 rounded-md px-3 text-xs",
  md: "h-9 gap-2 rounded-lg px-3.5 text-sm",
  lg: "h-10 gap-2 rounded-lg px-3.5 text-sm shadow-sm",
};

const ICON_ACTION_SIZES = {
  xs: "h-7 w-7 rounded-md",
  sm: "h-8 w-8 rounded-md",
  md: "h-9 w-9 rounded-lg",
  lg: "h-10 w-10 rounded-lg shadow-sm",
};

export function actionButtonClasses({
  intent = "neutral",
  tone = "solid",
  size = "sm",
  className = "",
} = {}) {
  const intentClasses = ACTION_INTENTS[intent] || ACTION_INTENTS.neutral;
  const toneClasses = intentClasses[tone] || intentClasses.solid;
  const sizeClasses = ACTION_SIZES[size] || ACTION_SIZES.sm;

  return [
    "inline-flex items-center justify-center whitespace-nowrap border font-medium transition-colors",
    "disabled:cursor-not-allowed disabled:border-gray-200 disabled:bg-gray-100 disabled:text-gray-400 dark:disabled:border-slate-700 dark:disabled:bg-slate-800 dark:disabled:text-slate-400",
    sizeClasses,
    toneClasses,
    className,
  ]
    .filter(Boolean)
    .join(" ");
}

export function iconActionButtonClasses({
  intent = "neutral",
  tone = "soft",
  size = "sm",
  active = false,
  className = "",
} = {}) {
  const intentClasses = ACTION_INTENTS[intent] || ACTION_INTENTS.neutral;
  const toneClasses = intentClasses[active ? "solid" : tone] || intentClasses.soft;
  const sizeClasses = ICON_ACTION_SIZES[size] || ICON_ACTION_SIZES.sm;

  return [
    "relative inline-flex items-center justify-center border font-medium transition-colors",
    "disabled:cursor-not-allowed disabled:border-gray-200 disabled:bg-gray-100 disabled:text-gray-400 dark:disabled:border-slate-700 dark:disabled:bg-slate-800 dark:disabled:text-slate-400",
    sizeClasses,
    toneClasses,
    className,
  ]
    .filter(Boolean)
    .join(" ");
}

export const ACTION_COLOR_RULES = {
  create: "Criar/adicionar/cadastrar",
  edit: "Editar/salvar/atualizar",
  delete: "Excluir/remover/cancelar destrutivo",
  neutral: "Navegar, fechar, limpar, atualizar sem risco",
  warning: "Atencao, conflito, pendencia ou acao reversivel sensivel",
  pdf: "Importacao ou acao relacionada a PDF",
};
