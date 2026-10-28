import { useId } from "react";
import { formatMoneyBRL } from "../../../utils/formatters";

// Saldos e limites precisam de altura livre; os botões de ação têm altura fixa.
export default function BotaoSaldo({
  label,
  saldo,
  icone,
  detalhes = [],
  help = "",
  error = "",
  selecionado = false,
  disabled = false,
  onClick,
}) {
  const descricaoId = useId();

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-pressed={selecionado}
      aria-describedby={error || help ? descricaoId : undefined}
      className={[
        "flex h-full min-w-0 w-full flex-col items-start gap-2 rounded-xl border-2 p-3 text-left transition-colors",
        "whitespace-normal break-words focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-slate-900",
        "disabled:cursor-not-allowed disabled:opacity-60",
        error
          ? "border-red-500 bg-red-50 text-red-900 dark:bg-red-950 dark:text-red-100"
          : selecionado
            ? "border-blue-700 bg-blue-700 text-white dark:border-blue-500 dark:bg-blue-700"
            : "border-slate-300 bg-white text-slate-800 hover:border-blue-500 hover:bg-blue-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100 dark:hover:border-blue-400 dark:hover:bg-slate-700",
      ].join(" ")}
    >
      <span className="flex w-full min-w-0 items-center gap-2 text-sm font-semibold">
        {icone ? (
          <span className="shrink-0 text-xl" aria-hidden="true">
            {icone}
          </span>
        ) : null}
        <span className="min-w-0">{label}</span>
      </span>
      <span className="block w-full min-w-0 text-base font-semibold tabular-nums">
        Saldo: {formatMoneyBRL(saldo)}
      </span>
      {detalhes.map((detalhe) => (
        <span key={detalhe} className="block w-full min-w-0 text-xs leading-relaxed">
          {detalhe}
        </span>
      ))}
      {error || help ? (
        <span id={descricaoId} className="block w-full min-w-0 text-xs leading-relaxed">
          {error || help}
        </span>
      ) : null}
    </button>
  );
}
