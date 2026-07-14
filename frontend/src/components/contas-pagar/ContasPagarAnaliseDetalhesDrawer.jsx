import { useEffect } from "react";
import { FileSearch, RefreshCw, X } from "lucide-react";

import ActionButton from "../ui/ActionButton";

function formatarData(data) {
  if (!data) return "-";
  const [ano, mes, dia] = String(data).split("-");
  if (!ano || !mes || !dia) return data;
  return `${dia}/${mes}/${ano}`;
}

function origemCompleta(item) {
  return [item.origem_lancamento_label, item.origem_referencia].filter(Boolean).join(" - ");
}

export default function ContasPagarAnaliseDetalhesDrawer({
  detalhe,
  dados,
  formatarMoeda,
  loading,
  onClose,
  onPageChange,
}) {
  useEffect(() => {
    const fecharComEsc = (event) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", fecharComEsc);
    return () => window.removeEventListener("keydown", fecharComEsc);
  }, [onClose]);

  if (!detalhe) return null;

  const items = dados?.items || [];
  const total = dados?.total ?? detalhe.total_aberto ?? 0;
  const quantidade = dados?.total_itens ?? detalhe.quantidade ?? 0;

  return (
    <div className="fixed inset-0 z-[70] bg-slate-900/30" onClick={onClose}>
      <aside
        aria-labelledby="contas-pagar-detalhes-titulo"
        aria-modal="true"
        className="fixed inset-x-0 bottom-0 max-h-[88dvh] overflow-hidden rounded-t-2xl bg-white shadow-2xl md:inset-y-0 md:left-auto md:right-0 md:max-h-none md:w-[820px] md:rounded-none"
        onClick={(event) => event.stopPropagation()}
        role="dialog"
      >
        <div className="flex h-full flex-col">
          <div className="border-b border-slate-200 p-4 md:p-5">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Origem dos valores
                </p>
                <h2
                  id="contas-pagar-detalhes-titulo"
                  className="mt-1 text-lg font-bold text-slate-900 md:text-xl"
                >
                  {detalhe.nome}
                </h2>
                <p className="mt-1 text-sm text-slate-600">
                  Contas em aberto que formam este total, respeitando os filtros do relatorio.
                </p>
              </div>
              <ActionButton
                type="button"
                aria-label="Fechar detalhes"
                intent="neutral"
                onClick={onClose}
                size="sm"
                tone="ghost"
              >
                <X size={20} />
              </ActionButton>
            </div>

            <div className="mt-4 grid grid-cols-2 gap-3">
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <p className="text-xs font-medium uppercase text-slate-500">Total em aberto</p>
                <p className="mt-1 text-lg font-bold text-slate-900">{formatarMoeda(total)}</p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <p className="text-xs font-medium uppercase text-slate-500">Lancamentos</p>
                <p className="mt-1 text-lg font-bold text-slate-900">{quantidade}</p>
              </div>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-4 md:p-5">
            {loading ? (
              <div className="flex h-48 items-center justify-center text-slate-500">
                <RefreshCw className="mr-2 animate-spin" size={18} />
                Carregando lancamentos...
              </div>
            ) : items.length === 0 ? (
              <div className="rounded-lg border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">
                <FileSearch className="mx-auto mb-2 h-7 w-7" />
                Nenhum lancamento encontrado para este total.
              </div>
            ) : (
              <>
                <div className="hidden overflow-x-auto rounded-lg border border-slate-200 md:block">
                  <table className="min-w-full divide-y divide-slate-200 text-sm">
                    <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
                      <tr>
                        <th className="px-3 py-2 font-semibold">Vencimento</th>
                        <th className="px-3 py-2 font-semibold">Conta / fornecedor</th>
                        <th className="px-3 py-2 font-semibold">Origem</th>
                        <th className="px-3 py-2 text-right font-semibold">Saldo</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 bg-white">
                      {items.map((item) => (
                        <tr key={item.id} className="align-top hover:bg-slate-50">
                          <td className="whitespace-nowrap px-3 py-3 text-slate-700">
                            {formatarData(item.data_vencimento)}
                          </td>
                          <td className="px-3 py-3">
                            <div className="font-medium text-slate-900">{item.descricao}</div>
                            <div className="mt-0.5 text-xs text-slate-500">
                              {item.fornecedor_nome} • {item.tipo_despesa_nome}
                            </div>
                          </td>
                          <td className="px-3 py-3 text-slate-700">
                            <div>{item.origem_lancamento_label}</div>
                            <div className="mt-0.5 text-xs text-slate-500">
                              {item.origem_referencia || item.documento || "-"}
                            </div>
                          </td>
                          <td className="whitespace-nowrap px-3 py-3 text-right font-semibold text-slate-900">
                            {formatarMoeda(item.saldo_aberto)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="space-y-3 md:hidden">
                  {items.map((item) => (
                    <div key={item.id} className="rounded-lg border border-slate-200 p-3 shadow-sm">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="text-xs font-medium text-slate-500">
                            {formatarData(item.data_vencimento)} • {origemCompleta(item)}
                          </p>
                          <h3 className="mt-1 text-sm font-semibold text-slate-900">
                            {item.descricao}
                          </h3>
                          <p className="mt-1 text-xs text-slate-500">
                            {item.fornecedor_nome} • {item.tipo_despesa_nome}
                          </p>
                        </div>
                        <p className="shrink-0 text-sm font-bold text-slate-900">
                          {formatarMoeda(item.saldo_aberto)}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>

          {dados && dados.pages > 1 ? (
            <div className="flex items-center justify-between border-t border-slate-200 p-4 text-sm">
              <ActionButton
                type="button"
                disabled={loading || dados.page <= 1}
                intent="neutral"
                onClick={() => onPageChange(dados.page - 1)}
                size="sm"
                tone="soft"
              >
                Anterior
              </ActionButton>
              <span className="text-slate-600">
                Pagina {dados.page} de {dados.pages}
              </span>
              <ActionButton
                type="button"
                disabled={loading || dados.page >= dados.pages}
                intent="neutral"
                onClick={() => onPageChange(dados.page + 1)}
                size="sm"
                tone="soft"
              >
                Proxima
              </ActionButton>
            </div>
          ) : null}
        </div>
      </aside>
    </div>
  );
}
