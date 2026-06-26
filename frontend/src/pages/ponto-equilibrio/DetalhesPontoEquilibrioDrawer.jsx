import { RefreshCcw, X } from "lucide-react";
import { formatMoneyBRL } from "../../utils/formatters";
import { formatarDataBR } from "./pontoEquilibrioUtils";

export default function DetalhesPontoEquilibrioDrawer({
  linha,
  detalhes,
  loading,
  onClose,
  onPageChange,
}) {
  if (!linha) return null;

  const items = detalhes?.items || [];
  return (
    <div className="fixed inset-0 z-[70] bg-slate-900/30" onClick={onClose}>
      <aside
        className="fixed inset-x-0 bottom-0 max-h-[86dvh] overflow-hidden rounded-t-2xl bg-white shadow-2xl md:inset-y-0 md:left-auto md:right-0 md:max-h-none md:w-[760px] md:rounded-none"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex h-full flex-col">
          <div className="border-b border-slate-200 p-4 md:p-5">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-xs font-semibold uppercase text-slate-500">
                  Lancamentos do ponto de equilibrio
                </p>
                <h2 className="mt-1 text-lg font-bold text-slate-900 md:text-xl">
                  {detalhes?.label || linha.label}
                </h2>
                <p className="mt-1 text-sm text-slate-600">
                  {detalhes?.periodo || "Periodo filtrado"}
                </p>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="rounded-md p-2 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-900"
                aria-label="Fechar detalhes"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <p className="text-xs font-semibold uppercase text-slate-500">Total da linha</p>
                <p className="mt-1 text-lg font-bold text-slate-900">
                  {formatMoneyBRL(detalhes?.total ?? linha.valor ?? 0)}
                </p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <p className="text-xs font-semibold uppercase text-slate-500">Lancamentos</p>
                <p className="mt-1 text-lg font-bold text-slate-900">
                  {detalhes?.total_itens ?? "-"}
                </p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <p className="text-xs font-semibold uppercase text-slate-500">Origem</p>
                <p className="mt-1 text-sm font-semibold text-slate-800">
                  {items[0]?.origem_label || linha.origem}
                </p>
              </div>
            </div>
            {detalhes?.origem && (
              <p className="mt-3 rounded-lg bg-blue-50 px-3 py-2 text-sm text-blue-800">
                {detalhes.origem}
              </p>
            )}
          </div>

          <div className="flex-1 overflow-y-auto p-4 md:p-5">
            {loading ? (
              <div className="flex h-48 items-center justify-center text-slate-500">
                <RefreshCcw className="mr-2 h-4 w-4 animate-spin" />
                Carregando lancamentos...
              </div>
            ) : items.length === 0 ? (
              <div className="rounded-lg border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">
                Nenhum lancamento encontrado para esta linha no periodo.
              </div>
            ) : (
              <div className="overflow-x-auto rounded-lg border border-slate-200">
                <div className="grid min-w-[460px] grid-cols-[110px_minmax(220px,1fr)_120px] bg-slate-50 px-3 py-2 text-xs font-bold uppercase text-slate-500">
                  <span>Data</span>
                  <span>Descricao</span>
                  <span className="text-right">Valor</span>
                </div>
                <div className="divide-y divide-slate-100 bg-white">
                  {items.map((item, index) => (
                    <div
                      key={item.id || `${linha.grupo}-${index}`}
                      className="grid min-w-[460px] grid-cols-[110px_minmax(220px,1fr)_120px] gap-3 px-3 py-3 text-sm"
                    >
                      <span className="text-slate-600">{formatarDataBR(item.data)}</span>
                      <span className="min-w-0">
                        <span
                          className="block truncate font-semibold text-slate-900"
                          title={item.descricao}
                        >
                          {item.descricao}
                        </span>
                        {(item.contraparte || item.observacao || item.origem_classificacao) && (
                          <span className="mt-1 block truncate text-xs text-slate-500">
                            {item.contraparte || item.observacao || item.origem_classificacao}
                          </span>
                        )}
                      </span>
                      <span className="text-right font-bold text-slate-900">
                        {formatMoneyBRL(item.valor || 0)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {detalhes && detalhes.pages > 1 && (
            <div className="flex items-center justify-between border-t border-slate-200 p-4 text-sm">
              <button
                type="button"
                disabled={loading || detalhes.page <= 1}
                onClick={() => onPageChange(detalhes.page - 1)}
                className="rounded-md border border-slate-200 px-3 py-2 font-semibold text-slate-700 disabled:opacity-50"
              >
                Anterior
              </button>
              <span className="text-slate-600">
                Pagina {detalhes.page} de {detalhes.pages}
              </span>
              <button
                type="button"
                disabled={loading || detalhes.page >= detalhes.pages}
                onClick={() => onPageChange(detalhes.page + 1)}
                className="rounded-md border border-slate-200 px-3 py-2 font-semibold text-slate-700 disabled:opacity-50"
              >
                Proxima
              </button>
            </div>
          )}
        </div>
      </aside>
    </div>
  );
}
