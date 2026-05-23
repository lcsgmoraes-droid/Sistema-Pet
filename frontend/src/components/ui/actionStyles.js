const ACTION_INTENTS = {
  create: {
    solid: "border-emerald-600 bg-emerald-600 text-white hover:bg-emerald-700",
    soft: "border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100",
    ghost: "border-transparent bg-transparent text-emerald-700 hover:bg-emerald-50",
  },
  edit: {
    solid: "border-blue-600 bg-blue-600 text-white hover:bg-blue-700",
    soft: "border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100",
    ghost: "border-transparent bg-transparent text-blue-700 hover:bg-blue-50",
  },
  delete: {
    solid: "border-red-600 bg-red-600 text-white hover:bg-red-700",
    soft: "border-red-200 bg-red-50 text-red-700 hover:bg-red-100",
    ghost: "border-transparent bg-transparent text-red-700 hover:bg-red-50",
  },
  neutral: {
    solid: "border-slate-900 bg-slate-900 text-white hover:bg-slate-700",
    soft: "border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100",
    ghost: "border-transparent bg-transparent text-slate-600 hover:bg-slate-50",
  },
  warning: {
    solid: "border-amber-600 bg-amber-600 text-white hover:bg-amber-700",
    soft: "border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100",
    ghost: "border-transparent bg-transparent text-amber-700 hover:bg-amber-50",
  },
  info: {
    solid: "border-cyan-600 bg-cyan-600 text-white hover:bg-cyan-700",
    soft: "border-cyan-200 bg-cyan-50 text-cyan-700 hover:bg-cyan-100",
    ghost: "border-transparent bg-transparent text-cyan-700 hover:bg-cyan-50",
  },
  pdf: {
    solid: "border-red-600 bg-red-600 text-white hover:bg-red-700",
    soft: "border-red-200 bg-red-50 text-red-700 hover:bg-red-100",
    ghost: "border-transparent bg-transparent text-red-700 hover:bg-red-50",
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
    "disabled:cursor-not-allowed disabled:border-gray-200 disabled:bg-gray-100 disabled:text-gray-400",
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
    "disabled:cursor-not-allowed disabled:border-gray-200 disabled:bg-gray-100 disabled:text-gray-400",
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
