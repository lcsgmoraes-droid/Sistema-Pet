import { Calculator, RefreshCcw } from "lucide-react";
import {
  CANAIS,
  MARGEM_PONTO_EQUILIBRIO_OPCOES,
  MODO_CUSTO_FISCAL_OPCOES,
} from "./pontoEquilibrioConstants";

export default function PontoEquilibrioHeaderFilters({
  carregarDados,
  filtros,
  loading,
  setFiltros,
}) {
  return (
    <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
      <div>
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-blue-100 p-3 text-blue-700">
            <Calculator className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Ponto de Equilibrio</h1>
            <p className="text-sm text-slate-600">
              Quanto precisa vender para empatar os custos fixos pela margem de contribuicao
              escolhida.
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 rounded-lg border border-slate-200 bg-white p-3 md:grid-cols-2 xl:grid-cols-[140px_140px_160px_210px_210px_auto]">
        <div>
          <label className="text-xs font-semibold text-slate-600">Inicio</label>
          <input
            type="date"
            value={filtros.data_inicio}
            onChange={(event) => setFiltros({ ...filtros, data_inicio: event.target.value })}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="text-xs font-semibold text-slate-600">Fim</label>
          <input
            type="date"
            value={filtros.data_fim}
            onChange={(event) => setFiltros({ ...filtros, data_fim: event.target.value })}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="text-xs font-semibold text-slate-600">Canal</label>
          <select
            value={filtros.canal}
            onChange={(event) => setFiltros({ ...filtros, canal: event.target.value })}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          >
            {CANAIS.map((canal) => (
              <option key={canal.value || "todos"} value={canal.value}>
                {canal.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs font-semibold text-slate-600">Fonte da margem</label>
          <select
            value={filtros.fonte_margem}
            onChange={(event) => setFiltros({ ...filtros, fonte_margem: event.target.value })}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          >
            {MARGEM_PONTO_EQUILIBRIO_OPCOES.map((opcao) => (
              <option key={opcao.value} value={opcao.value}>
                {opcao.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs font-semibold text-slate-600">Visao de custo</label>
          <select
            value={filtros.modo_custo_fiscal}
            onChange={(event) => setFiltros({ ...filtros, modo_custo_fiscal: event.target.value })}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          >
            {MODO_CUSTO_FISCAL_OPCOES.map((opcao) => (
              <option key={opcao.value} value={opcao.value}>
                {opcao.label}
              </option>
            ))}
          </select>
        </div>
        <button
          type="button"
          onClick={carregarDados}
          disabled={loading}
          className="inline-flex items-center justify-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-blue-700 disabled:bg-slate-300"
        >
          <RefreshCcw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Atualizar
        </button>
      </div>
    </div>
  );
}
