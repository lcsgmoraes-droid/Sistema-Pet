import { Filter, RefreshCw, Search, X } from 'lucide-react';

const STATUS_PEDIDO_OPTIONS = [
  { value: '', label: 'Todos' },
  { value: 'rascunho', label: 'Rascunho' },
  { value: 'enviado', label: 'Enviado' },
  { value: 'confirmado', label: 'Confirmado' },
  { value: 'recebido_parcial', label: 'Parcial' },
  { value: 'recebido_total', label: 'Recebido' },
  { value: 'cancelado', label: 'Cancelado' },
];

export default function PedidosCompraFiltros({
  filtrosPedidos,
  filtrosPedidosAtivos,
  fornecedoresOrdenados,
  loadingListaPedidos,
  onAplicar,
  onAtualizarFiltro,
  onLimpar,
  onSelecionarStatus,
  pedidosCount,
}) {
  return (
    <form
      onSubmit={onAplicar}
      className="mb-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
    >
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Filter className="h-5 w-5 text-blue-600" />
            <div>
              <h2 className="text-base font-bold text-slate-900">Filtros</h2>
              <p className="text-sm text-slate-500">{pedidosCount} pedido(s) na lista</p>
            </div>
          </div>
          {filtrosPedidosAtivos > 0 && (
            <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-bold text-blue-700">
              {filtrosPedidosAtivos} filtro(s) ativo(s)
            </span>
          )}
        </div>

        <div className="flex flex-wrap gap-2">
          {STATUS_PEDIDO_OPTIONS.map((opcao) => (
            <button
              key={opcao.value || 'todos'}
              type="button"
              onClick={() => onSelecionarStatus(opcao.value)}
              className={`h-9 rounded-lg border px-3 text-sm font-semibold transition-colors ${
                filtrosPedidos.status === opcao.value
                  ? 'border-blue-500 bg-blue-600 text-white'
                  : 'border-slate-200 bg-slate-50 text-slate-700 hover:bg-blue-50 hover:text-blue-700'
              }`}
            >
              {opcao.label}
            </button>
          ))}
        </div>

        <div className="grid gap-3 lg:grid-cols-[1.1fr_1fr_0.7fr_0.7fr_auto]">
          <label className="block">
            <span className="mb-1 block text-xs font-bold uppercase text-slate-500">Buscar</span>
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                type="search"
                value={filtrosPedidos.busca}
                onChange={(event) => onAtualizarFiltro('busca', event.target.value)}
                placeholder="Numero, fornecedor ou observacao"
                className="h-10 w-full rounded-lg border border-slate-300 pl-9 pr-3 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
              />
            </div>
          </label>

          <label className="block">
            <span className="mb-1 block text-xs font-bold uppercase text-slate-500">Fornecedor</span>
            <select
              value={filtrosPedidos.fornecedor_id}
              onChange={(event) => onAtualizarFiltro('fornecedor_id', event.target.value)}
              className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
            >
              <option value="">Todos os fornecedores</option>
              {fornecedoresOrdenados.map((fornecedor) => (
                <option key={fornecedor.id} value={fornecedor.id}>
                  {fornecedor.nome}
                </option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="mb-1 block text-xs font-bold uppercase text-slate-500">Inicio</span>
            <input
              type="date"
              value={filtrosPedidos.data_inicio}
              onChange={(event) => onAtualizarFiltro('data_inicio', event.target.value)}
              className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
            />
          </label>

          <label className="block">
            <span className="mb-1 block text-xs font-bold uppercase text-slate-500">Fim</span>
            <input
              type="date"
              value={filtrosPedidos.data_fim}
              onChange={(event) => onAtualizarFiltro('data_fim', event.target.value)}
              className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
            />
          </label>

          <div className="flex items-end gap-2">
            <button
              type="submit"
              disabled={loadingListaPedidos}
              className="inline-flex h-10 items-center gap-2 rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <RefreshCw className={`h-4 w-4 ${loadingListaPedidos ? 'animate-spin' : ''}`} />
              Aplicar
            </button>
            <button
              type="button"
              onClick={onLimpar}
              className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-300 bg-white px-3 text-sm font-semibold text-slate-700 hover:bg-slate-50"
              title="Limpar filtros"
              aria-label="Limpar filtros"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </form>
  );
}
