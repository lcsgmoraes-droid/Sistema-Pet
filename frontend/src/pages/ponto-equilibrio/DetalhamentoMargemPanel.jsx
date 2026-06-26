import { formatMoneyBRL } from "../../utils/formatters";
import {
  linhaValorClassName,
  montarLinhasDetalhamentoPontoEquilibrio,
} from "./pontoEquilibrioUtils";

export default function DetalhamentoMargemPanel({ dados, onAbrirDetalhes }) {
  const linhas = montarLinhasDetalhamentoPontoEquilibrio(dados);

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
        <h2 className="text-base font-semibold text-blue-950">Detalhamento da margem e custos</h2>
        <p className="mt-1 text-sm text-blue-900">
          Clique em detalhes para carregar os lancamentos daquela linha. O resumo fica leve e os
          itens completos aparecem sob demanda, no mesmo estilo da DRE.
        </p>
      </div>

      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
        <div className="grid grid-cols-1 gap-1 bg-slate-50 px-4 py-3 text-xs font-bold uppercase text-slate-500 sm:grid-cols-[minmax(220px,1fr)_160px_130px]">
          <span>Origem das contas e custos fixos</span>
          <span className="sm:text-right">Valor</span>
          <span className="sm:text-right">Acao</span>
        </div>
        <div className="divide-y divide-slate-100">
          {linhas.map((linha) => (
            <button
              key={linha.grupo}
              type="button"
              onClick={() => onAbrirDetalhes(linha)}
              className="grid w-full grid-cols-1 items-center gap-2 px-4 py-3 text-left text-sm transition-colors hover:bg-blue-50 sm:grid-cols-[minmax(220px,1fr)_160px_130px] sm:gap-3"
            >
              <span className="min-w-0">
                <span className="block font-semibold text-slate-900">{linha.label}</span>
                <span className="block truncate text-xs text-slate-500">{linha.origem}</span>
              </span>
              <span className={`font-bold sm:text-right ${linhaValorClassName(linha.tipo)}`}>
                {linha.tipo === "receita" ? "+" : linha.tipo === "informativo" ? "" : "-"}{" "}
                {formatMoneyBRL(Math.abs(linha.valor || 0))}
              </span>
              <span className="sm:text-right">
                <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
                  detalhes
                </span>
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
