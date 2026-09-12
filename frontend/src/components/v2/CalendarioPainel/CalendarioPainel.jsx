import { ChevronLeft, ChevronRight } from "lucide-react";
import { forwardRef } from "react";
import {
  DIAS_SEMANA_ABREV,
  NOMES_MES,
  adicionarMeses,
  isoEntre,
  isoHoje,
  obterGradeMes,
} from "../utils/calendario";

const CalendarioPainel = forwardRef(function CalendarioPainel(
  { intervalo, mesVisivel, onMudarMes, onSelecionarDia, rodape, selecionados = [] },
  ref,
) {
  const dias = obterGradeMes(mesVisivel);
  const hoje = isoHoje();

  return (
    <div
      ref={ref}
      className="absolute z-20 mt-1 w-72 rounded-lg border border-slate-200 bg-white p-3 shadow-lg dark:border-slate-700 dark:bg-slate-900"
    >
      <div className="mb-2 flex items-center justify-between">
        <button
          type="button"
          aria-label="Mês anterior"
          onClick={() => onMudarMes(adicionarMeses(mesVisivel, -1))}
          className="rounded p-1 text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">
          {NOMES_MES[mesVisivel.getMonth()]} {mesVisivel.getFullYear()}
        </span>
        <button
          type="button"
          aria-label="Próximo mês"
          onClick={() => onMudarMes(adicionarMeses(mesVisivel, 1))}
          className="rounded p-1 text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>

      <div className="grid grid-cols-7 gap-y-1 text-center text-xs">
        {DIAS_SEMANA_ABREV.map((dia) => (
          <span key={dia} className="py-1 font-semibold text-slate-400 dark:text-slate-500">
            {dia}
          </span>
        ))}
        {dias.map(({ data, iso, noMesAtual }) => {
          const selecionado = selecionados.includes(iso);
          const noIntervalo = intervalo && isoEntre(iso, intervalo.inicio, intervalo.fim);
          const ehHoje = iso === hoje;

          return (
            <button
              key={iso}
              type="button"
              onClick={() => onSelecionarDia(iso)}
              className={[
                "mx-auto flex h-7 w-7 items-center justify-center rounded-full transition-colors",
                !noMesAtual
                  ? "text-slate-300 dark:text-slate-600"
                  : "text-slate-700 dark:text-slate-200",
                noIntervalo && !selecionado ? "bg-blue-50 dark:bg-slate-800" : "",
                selecionado
                  ? "bg-blue-600 text-white hover:bg-blue-700"
                  : "hover:bg-slate-100 dark:hover:bg-slate-800",
                ehHoje && !selecionado ? "ring-1 ring-inset ring-blue-400" : "",
              ].join(" ")}
            >
              {data.getDate()}
            </button>
          );
        })}
      </div>

      {rodape ? (
        <div className="mt-3 border-t border-slate-100 pt-3 dark:border-slate-800">{rodape}</div>
      ) : null}
    </div>
  );
});

export default CalendarioPainel;
