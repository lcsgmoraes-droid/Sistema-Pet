import { formatarMoeda } from "../../api/produtos";
import { ResumoTransferenciaCard } from "./transferenciaParceiroComponents";

export default function HistoricoTransferenciaFilters({
  parceiroSelecionado,
  onUsarParceiroAtual,
  onAtualizarHistorico,
  totais,
  filtros,
  atualizarFiltro,
  aplicarPeriodoRapido,
  limparFiltros,
  onSubmit,
}) {
  return (
    <>
      <div className="flex flex-col gap-4 border-b border-gray-100 px-6 py-5 xl:flex-row xl:items-start xl:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Historico de transferencias</h2>
          <p className="mt-1 text-sm text-gray-600">
            Acompanhe o que saiu do estoque, quanto a pessoa ja ressarciu e o que segue em aberto.
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          {parceiroSelecionado ? (
            <button
              type="button"
              onClick={onUsarParceiroAtual}
              className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-medium text-blue-700 transition-colors hover:bg-blue-100"
            >
              Filtrar pessoa atual
            </button>
          ) : null}
          <button
            type="button"
            onClick={onAtualizarHistorico}
            className="rounded-xl border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
          >
            Atualizar historico
          </button>
        </div>
      </div>

      <div className="grid gap-4 border-b border-gray-100 px-6 py-5 md:grid-cols-2 xl:grid-cols-4">
        <ResumoTransferenciaCard
          titulo="Transferencias filtradas"
          valor={String(totais.total_registros || 0)}
          descricao="Documentos localizados no historico atual."
          destaque="slate"
        />
        <ResumoTransferenciaCard
          titulo="Valor transferido"
          valor={formatarMoeda(totais.valor_total || 0)}
          descricao="Total em custo enviado para pessoas com ressarcimento."
          destaque="blue"
        />
        <ResumoTransferenciaCard
          titulo="Saldo em aberto"
          valor={formatarMoeda(totais.saldo_aberto || 0)}
          descricao={`${totais.pendentes || 0} pendente(s) e ${totais.vencidas || 0} vencida(s).`}
          destaque="amber"
        />
        <ResumoTransferenciaCard
          titulo="Valor recebido"
          valor={formatarMoeda(totais.valor_recebido || 0)}
          descricao={`${totais.recebidas || 0} transferencia(s) ja recebida(s).`}
          destaque="emerald"
        />
      </div>

      <form
        onSubmit={onSubmit}
        className="grid gap-4 border-b border-gray-100 px-6 py-5 md:grid-cols-2 xl:grid-cols-5"
      >
        <div className="xl:col-span-2">
          <label className="mb-2 block text-sm font-medium text-gray-700">
            Buscar documento ou pessoa
          </label>
          <input
            type="text"
            value={filtros.busca}
            onChange={(event) => atualizarFiltro("busca", event.target.value)}
            placeholder="Ex.: TRP-2026, nome da pessoa ou observacao"
            className="w-full rounded-2xl border border-gray-300 px-4 py-3 text-sm text-gray-900 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
          />
        </div>

        <div>
          <label className="mb-2 block text-sm font-medium text-gray-700">Status</label>
          <select
            value={filtros.status_filtro}
            onChange={(event) => atualizarFiltro("status_filtro", event.target.value)}
            className="w-full rounded-2xl border border-gray-300 px-4 py-3 text-sm text-gray-900 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
          >
            <option value="">Todos</option>
            <option value="pendente">Pendente</option>
            <option value="parcial">Parcial</option>
            <option value="vencido">Vencida</option>
            <option value="recebido">Recebida</option>
            <option value="cancelado">Cancelada</option>
          </select>
        </div>

        <div>
          <label className="mb-2 block text-sm font-medium text-gray-700">Data inicial</label>
          <input
            type="date"
            value={filtros.data_inicio}
            onChange={(event) => atualizarFiltro("data_inicio", event.target.value)}
            className="w-full rounded-2xl border border-gray-300 px-4 py-3 text-sm text-gray-900 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
          />
        </div>

        <div>
          <label className="mb-2 block text-sm font-medium text-gray-700">Data final</label>
          <input
            type="date"
            value={filtros.data_fim}
            onChange={(event) => atualizarFiltro("data_fim", event.target.value)}
            className="w-full rounded-2xl border border-gray-300 px-4 py-3 text-sm text-gray-900 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
          />
        </div>

        <div className="md:col-span-2 xl:col-span-5 flex flex-wrap justify-end gap-2">
          <button
            type="button"
            onClick={() => aplicarPeriodoRapido("mes_atual")}
            className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-medium text-blue-700 transition-colors hover:bg-blue-100"
          >
            Mes atual
          </button>
          <button
            type="button"
            onClick={() => aplicarPeriodoRapido("mes_anterior")}
            className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-medium text-blue-700 transition-colors hover:bg-blue-100"
          >
            Mes anterior
          </button>
          <button
            type="button"
            onClick={limparFiltros}
            className="rounded-xl border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
          >
            Limpar filtros
          </button>
          <button
            type="submit"
            className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800"
          >
            Aplicar filtros
          </button>
        </div>
      </form>
    </>
  );
}
