import { Loader2 } from "lucide-react";
import { forwardRef } from "react";

const VARIANTES = {
  neutro:
    "border-slate-900 bg-slate-900 text-white hover:bg-slate-700 dark:border-slate-600 dark:bg-slate-700 dark:hover:bg-slate-600",
  neutroSuave:
    "border-slate-300 bg-white text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800",
  sucesso:
    "border-emerald-600 bg-emerald-600 text-white hover:bg-emerald-700 dark:border-emerald-700 dark:bg-emerald-700 dark:hover:bg-emerald-800",
  perigo:
    "border-red-600 bg-red-600 text-white hover:bg-red-700 dark:border-red-700 dark:bg-red-700 dark:hover:bg-red-800",
  informativo:
    "border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100 dark:border-blue-400/30 dark:bg-blue-500/10 dark:text-blue-200 dark:hover:bg-blue-500/20",
};

// Casca interna dos botões v2 — telas usam BotaoSalva/BotaoCancelar/BotaoExcluir/BotaoAjuda/BotaoInteracao, não este diretamente.
const BotaoBase = forwardRef(function BotaoBase(
  {
    children,
    disabled = false,
    icon: Icone,
    loading = false,
    onClick,
    type = "button",
    variante = "neutro",
  },
  ref,
) {
  const desabilitado = disabled || loading;

  return (
    <button
      ref={ref}
      type={type}
      disabled={desabilitado}
      onClick={onClick}
      className={[
        "inline-flex h-9 items-center justify-center gap-1.5 whitespace-nowrap rounded-lg border px-3.5 text-sm font-medium transition-colors",
        "disabled:cursor-not-allowed disabled:border-gray-200 disabled:bg-gray-100 disabled:text-gray-400",
        "dark:disabled:border-slate-700 dark:disabled:bg-slate-800 dark:disabled:text-slate-500",
        VARIANTES[variante] || VARIANTES.neutro,
      ].join(" ")}
    >
      {loading ? (
        <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
      ) : Icone ? (
        <Icone className="h-4 w-4" aria-hidden="true" />
      ) : null}
      {children}
    </button>
  );
});

export default BotaoBase;
