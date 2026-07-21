import { useState } from "react";
import {
  ChevronDown,
  ChevronUp,
  Filter,
  RefreshCw,
  Search,
  SlidersHorizontal,
  X,
} from "lucide-react";
import FornecedorSelector from "../fornecedores/FornecedorSelector";

const VISAO_PEDIDO_OPTIONS = [
  { value: "em_andamento", label: "Em andamento" },
  { value: "concluidos", label: "Concluídos" },
  { value: "cancelados", label: "Cancelados" },
  { value: "", label: "Todos" },
];

const STATUS_PEDIDO_OPTIONS = [
  { value: "", label: "Todos os status da visão" },
  { value: "rascunho", label: "Rascunho" },
  { value: "enviado", label: "Enviado" },
  { value: "confirmado", label: "Confirmado" },
  { value: "recebido_parcial", label: "Recebido parcialmente" },
  { value: "recebido_total", label: "Recebido" },
  { value: "cancelado", label: "Cancelado" },
];

export default function PedidosCompraFiltros({
  filtrosPedidos,
  filtrosPedidosAtivos,
  fornecedoresOrdenados,
  loadingListaPedidos,
  onAplicar,
  onAtualizarFiltro,
  onLimpar,
  onSelecionarVisao,
  pedidosCount,
}) {
  const [mostrarAvancados, setMostrarAvancados] = useState(false);
  const fornecedorSelecionado =
    fornecedoresOrdenados.find(
      (fornecedor) => String(fornecedor.id) === String(filtrosPedidos.fornecedor_id),
    ) || null;
  const filtrosAvancadosAtivos = [
    filtrosPedidos.status,
    filtrosPedidos.fornecedor_id,
    filtrosPedidos.data_inicio,
    filtrosPedidos.data_fim,
  ].filter((valor) => String(valor || "").trim()).length;

  return (
    <form
      onSubmit={onAplicar}
      className="mb-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
    >
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="mr-2 flex min-w-fit items-center gap-2">
            <Filter className="h-5 w-5 text-blue-600" />
            <div>
              <h2 className="text-sm font-bold text-slate-900">Pedidos</h2>
              <p className="text-xs text-slate-500">{pedidosCount} encontrado(s)</p>
            </div>
          </div>

          <div className="flex flex-wrap gap-1 rounded-lg bg-slate-100 p-1">
            {VISAO_PEDIDO_OPTIONS.map((opcao) => (
              <button
                key={opcao.value || "todos"}
                type="button"
                onClick={() => onSelecionarVisao(opcao.value)}
                className={`h-8 rounded-md px-3 text-xs font-semibold transition-colors ${
                  filtrosPedidos.visao === opcao.value && !filtrosPedidos.status
                    ? "bg-white text-blue-700 shadow-sm"
                    : "text-slate-600 hover:bg-white/70 hover:text-slate-900"
                }`}
              >
                {opcao.label}
              </button>
            ))}
          </div>

          <div className="ml-auto flex min-w-[280px] flex-1 flex-wrap items-center justify-end gap-2 lg:flex-nowrap">
            <label className="relative min-w-[240px] flex-1 lg:max-w-md">
              <span className="sr-only">Buscar pedidos</span>
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                type="search"
                value={filtrosPedidos.busca}
                onChange={(event) => onAtualizarFiltro("busca", event.target.value)}
                placeholder="Número, fornecedor ou observação"
                className="h-10 w-full rounded-lg border border-slate-300 pl-9 pr-3 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
              />
            </label>

            <button
              type="submit"
              disabled={loadingListaPedidos}
              className="inline-flex h-10 items-center gap-2 rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <RefreshCw className={`h-4 w-4 ${loadingListaPedidos ? "animate-spin" : ""}`} />
              Aplicar
            </button>

            <button
              type="button"
              onClick={() => setMostrarAvancados((atual) => !atual)}
              className="inline-flex h-10 items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 text-sm font-semibold text-slate-700 hover:bg-slate-50"
              aria-expanded={mostrarAvancados}
            >
              <SlidersHorizontal className="h-4 w-4" />
              Mais filtros
              {filtrosAvancadosAtivos > 0 ? (
                <span className="rounded-full bg-blue-100 px-1.5 py-0.5 text-[10px] font-bold text-blue-700">
                  {filtrosAvancadosAtivos}
                </span>
              ) : null}
              {mostrarAvancados ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </button>

            {filtrosPedidosAtivos > 0 ? (
              <button
                type="button"
                onClick={() => {
                  setMostrarAvancados(false);
                  onLimpar();
                }}
                className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-300 bg-white px-3 text-slate-600 hover:bg-slate-50"
                title="Limpar filtros"
                aria-label="Limpar filtros"
              >
                <X className="h-4 w-4" />
              </button>
            ) : null}
          </div>
        </div>

        {mostrarAvancados ? (
          <div className="grid gap-3 border-t border-slate-100 pt-4 md:grid-cols-2 xl:grid-cols-4">
            <label className="block">
              <span className="mb-1 block text-xs font-bold uppercase text-slate-500">
                Status específico
              </span>
              <select
                value={filtrosPedidos.status}
                onChange={(event) => onAtualizarFiltro("status", event.target.value)}
                className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
              >
                {STATUS_PEDIDO_OPTIONS.map((opcao) => (
                  <option key={opcao.value || "todos"} value={opcao.value}>
                    {opcao.label}
                  </option>
                ))}
              </select>
            </label>

            <div className="block">
              <span className="mb-1 block text-xs font-bold uppercase text-slate-500">
                Fornecedor
              </span>
              <FornecedorSelector
                fornecedores={fornecedoresOrdenados}
                fornecedorId={filtrosPedidos.fornecedor_id}
                fornecedorSelecionado={fornecedorSelecionado}
                showLabel={false}
                placeholder="Buscar fornecedor..."
                inputClassName="rounded-lg border-slate-300"
                onInputChange={(termo) => {
                  if (!termo || filtrosPedidos.fornecedor_id) {
                    onAtualizarFiltro("fornecedor_id", "");
                  }
                }}
                onSelect={(fornecedor) =>
                  onAtualizarFiltro("fornecedor_id", fornecedor?.id ? String(fornecedor.id) : "")
                }
                onClear={() => onAtualizarFiltro("fornecedor_id", "")}
                onFornecedorCriado={(fornecedor) =>
                  onAtualizarFiltro("fornecedor_id", fornecedor?.id ? String(fornecedor.id) : "")
                }
              />
            </div>

            <label className="block">
              <span className="mb-1 block text-xs font-bold uppercase text-slate-500">Início</span>
              <input
                type="date"
                value={filtrosPedidos.data_inicio}
                onChange={(event) => onAtualizarFiltro("data_inicio", event.target.value)}
                className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
              />
            </label>

            <label className="block">
              <span className="mb-1 block text-xs font-bold uppercase text-slate-500">Fim</span>
              <input
                type="date"
                value={filtrosPedidos.data_fim}
                onChange={(event) => onAtualizarFiltro("data_fim", event.target.value)}
                className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
              />
            </label>
          </div>
        ) : null}
      </div>
    </form>
  );
}
