import { ChevronLeft, ChevronRight } from "lucide-react";
import {
  DIAS_SEMANA_ABREV,
  NOMES_MES,
  adicionarMeses,
  isoEntre,
  isoHoje,
  obterGradeMes,
} from "../utils/calendario";

export default function MesGrade({
  intervalo,
  mesVisivel,
  mostrarSetaAnterior = true,
  mostrarSetaProxima = true,
  onMudarMes,
  onSelecionarDia,
  selecionados = [],
}) {
  const dias = obterGradeMes(mesVisivel);
  const hoje = isoHoje();

  return (
    <div className="w-64">
      <div className="mb-2 flex items-center justify-between">
        {mostrarSetaAnterior ? (
          <button
            type="button"
            aria-label="Mês anterior"
            onClick={() => onMudarMes(adicionarMeses(mesVisivel, -1))}
            className="rounded p-1 text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
        ) : (
          <span className="h-6 w-6" />
        )}
        <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">
          {NOMES_MES[mesVisivel.getMonth()]} {mesVisivel.getFullYear()}
        </span>
        {mostrarSetaProxima ? (
          <button
            type="button"
            aria-label="Próximo mês"
            onClick={() => onMudarMes(adicionarMeses(mesVisivel, 1))}
            className="rounded p-1 text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        ) : (
          <span className="h-6 w-6" />
        )}
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
    </div>
  );
}
