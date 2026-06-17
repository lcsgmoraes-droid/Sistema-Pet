import { X } from "lucide-react";
import EmptyState from "../ui/EmptyState";
import ProductIdentity from "../ui/ProductIdentity";
import StatusBadge from "../ui/StatusBadge";

const formatarQuantidadePadrao = (valor) =>
  new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 3,
  }).format(Number(valor || 0));

const formatarDataHora = (valor) => {
  if (!valor) return "-";
  const data = new Date(valor);
  return Number.isNaN(data.getTime()) ? "-" : data.toLocaleString("pt-BR");
};

export default function ReservasAtivasModal({
  abrirPedidoReservado,
  formatarQuantidade = formatarQuantidadePadrao,
  onClose,
  reservasAtivas = [],
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="max-h-[85vh] w-full max-w-3xl overflow-hidden rounded-2xl bg-white shadow-2xl">
        <div className="flex items-start justify-between gap-4 border-b border-slate-200 px-6 py-4">
          <div>
            <h3 className="text-lg font-bold text-slate-900">Pedidos com reserva ativa</h3>
            <p className="mt-1 text-sm text-slate-500">
              {reservasAtivas.length} pedido{reservasAtivas.length !== 1 ? "s" : ""} segurando este
              produto.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-2 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
            aria-label="Fechar"
          >
            <X size={20} aria-hidden="true" />
          </button>
        </div>

        <div className="max-h-[70vh] overflow-y-auto px-6 py-4">
          {reservasAtivas.length === 0 ? (
            <EmptyState
              compact
              description="Nenhum pedido segurando este produto agora."
              title="Nenhuma reserva ativa"
            />
          ) : (
            <div className="space-y-3">
              {reservasAtivas.map((pedido) => (
                <div
                  key={pedido.pedido_integrado_id}
                  className="rounded-xl border border-slate-200 bg-white px-4 py-4 shadow-sm"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <button
                        type="button"
                        onClick={() => abrirPedidoReservado(pedido)}
                        className="text-left text-base font-bold text-blue-600 hover:underline"
                      >
                        #
                        {pedido.pedido_bling_numero ||
                          pedido.pedido_bling_id ||
                          pedido.pedido_integrado_id}
                      </button>
                      <div className="mt-1 flex flex-wrap gap-2 text-xs">
                        {pedido.canal_label ? (
                          <StatusBadge intent="info" size="xs">
                            {pedido.canal_label}
                          </StatusBadge>
                        ) : null}
                        {pedido.status ? <StatusBadge size="xs" status={pedido.status} /> : null}
                        {pedido.nf_numero ? (
                          <StatusBadge intent="success" size="xs">
                            NF {pedido.nf_numero}
                          </StatusBadge>
                        ) : null}
                      </div>
                    </div>

                    <div className="text-right">
                      <div className="text-[11px] uppercase tracking-wide text-slate-400">
                        Reservado neste produto
                      </div>
                      <div className="mt-1 text-lg font-black text-amber-700">
                        {formatarQuantidade(pedido.quantidade_reservada)}
                      </div>
                    </div>
                  </div>

                  <div className="mt-3 grid gap-2 text-sm text-slate-600 md:grid-cols-3">
                    <div>
                      <span className="font-medium text-slate-800">Pedido na loja:</span>{" "}
                      {pedido.numero_pedido_loja || "-"}
                    </div>
                    <div>
                      <span className="font-medium text-slate-800">Criado em:</span>{" "}
                      {formatarDataHora(pedido.criado_em)}
                    </div>
                    <div>
                      <span className="font-medium text-slate-800">Expira em:</span>{" "}
                      {formatarDataHora(pedido.expira_em)}
                    </div>
                  </div>

                  <div className="mt-3 space-y-2">
                    {Array.isArray(pedido.itens) &&
                      pedido.itens.map((item) => (
                        <div
                          key={`${pedido.pedido_integrado_id}-${item.item_id}-${item.sku}`}
                          className="rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-700"
                        >
                          <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
                            <ProductIdentity
                              code={item.sku || "SEM-SKU"}
                              name={item.descricao || "-"}
                            />
                          </div>
                          <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
                            <span>Qtd pedido: {formatarQuantidade(item.quantidade_item)}</span>
                            <span>
                              Reserva neste produto:{" "}
                              {formatarQuantidade(item.quantidade_reservada_produto)}
                            </span>
                            {item.origem_reserva === "componente_kit_virtual" ? (
                              <span>
                                Origem: componente do kit{" "}
                                {item.kit_origem_sku || item.kit_origem_nome || "-"}
                              </span>
                            ) : null}
                          </div>
                        </div>
                      ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
