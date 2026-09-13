// Vocabulário de tom semântico padrão dos componentes v2: neutro, sucesso, perigo, informativo, atencao.
// Mesmo significado usado em BotaoBase.variante — qualquer componente novo que precise comunicar
// status por cor deve reaproveitar essas mesmas 5 chaves em vez de inventar outra nomenclatura.
export const TONS_BADGE = {
  neutro:
    "border-slate-200 bg-slate-100 text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200",
  sucesso:
    "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-200",
  perigo:
    "border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-200",
  informativo:
    "border-blue-200 bg-blue-50 text-blue-800 dark:border-blue-500/30 dark:bg-blue-500/10 dark:text-blue-200",
  atencao:
    "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200",
};

export const TONS_ICONE = {
  neutro: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
  sucesso: "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300",
  perigo: "bg-rose-50 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300",
  informativo: "bg-blue-50 text-blue-700 dark:bg-blue-500/15 dark:text-blue-300",
  atencao: "bg-amber-50 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300",
};
