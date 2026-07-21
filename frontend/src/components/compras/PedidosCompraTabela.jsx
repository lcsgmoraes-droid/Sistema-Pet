import { Fragment, useState } from "react";
import { Check, Eye, MoreHorizontal, Package, RotateCcw, Search, Send, Trash2 } from "lucide-react";
import ActionButton from "../ui/ActionButton";
import ExportActionButton from "../ui/ExportActionButton";
import MoneyCell from "../ui/MoneyCell";
import PaginationControls from "../ui/PaginationControls";
import StatusBadge from "../ui/StatusBadge";

const STATUS_PEDIDO_META = {
  rascunho: { label: "RASCUNHO", intent: "neutral" },
  enviado: { label: "ENVIADO", intent: "info" },
  confirmado: { label: "CONFIRMADO", intent: "success" },
  recebido_parcial: { label: "PARCIAL", intent: "warning" },
  recebido_total: { label: "RECEBIDO", intent: "success" },
  cancelado: { label: "CANCELADO", intent: "danger" },
};

function PedidoStatusBadge({ status }) {
  const meta = STATUS_PEDIDO_META[status] || {
    label: String(status || "-")
      .replace("_", " ")
      .toUpperCase(),
    intent: "neutral",
  };

  return (
    <StatusBadge intent={meta.intent} size="md">
      {meta.label}
    </StatusBadge>
  );
}

function formatarDataPedido(dataPedido) {
  if (!dataPedido) return "-";
  return new Date(dataPedido).toLocaleDateString();
}

export default function PedidosCompraTabela({
  abrirConfronto,
  abrirEdicao,
  abrirRecebimento,
  cancelarPedido,
  confirmarPedido,
  enviarPedido,
  exportarExcel,
  exportarPDF,
  loading = false,
  obterFornecedorPorId,
  onItemsPerPageChange,
  onPageChange,
  paginaAtual = 1,
  paginasTotal = 0,
  pedidos,
  pedidosPorPagina = 20,
  reverterStatus,
  totalPedidos = 0,
  verDetalhes,
}) {
  const [pedidoAcoesAberto, setPedidoAcoesAberto] = useState(null);

  const executarAcao = (acao) => {
    setPedidoAcoesAberto(null);
    acao();
  };

  const acaoPrincipal = (pedido) => {
    if (pedido.status === "rascunho") {
      return (
        <ActionButton
          icon={Send}
          intent="edit"
          onClick={() => enviarPedido(pedido)}
          size="xs"
          tone="soft"
          title="Enviar pedido ao fornecedor"
        >
          Enviar
        </ActionButton>
      );
    }
    if (pedido.status === "enviado") {
      return (
        <ActionButton
          icon={Check}
          intent="create"
          onClick={() => confirmarPedido(pedido.id)}
          size="xs"
          tone="soft"
          title="Confirmar recebimento do pedido pelo fornecedor"
        >
          Confirmar
        </ActionButton>
      );
    }
    if (pedido.status === "confirmado") {
      return (
        <ActionButton
          icon={Search}
          intent="info"
          onClick={() => abrirConfronto(pedido)}
          size="xs"
          tone="soft"
          title="Confrontar pedido com nota fiscal"
        >
          Conferir NF
        </ActionButton>
      );
    }
    if (pedido.status === "recebido_parcial") {
      return (
        <ActionButton
          icon={Package}
          intent="neutral"
          onClick={() => abrirRecebimento(pedido)}
          size="xs"
          tone="soft"
          title="Registrar o recebimento restante"
        >
          Receber restante
        </ActionButton>
      );
    }
    return null;
  };

  const abrirPedido = (pedido) => {
    if (pedido.status === "rascunho") {
      abrirEdicao(pedido);
      return;
    }
    verDetalhes(pedido);
  };

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="overflow-x-auto">
        <table className={`w-full transition-opacity ${loading ? "opacity-50" : "opacity-100"}`}>
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-semibold">Número</th>
              <th className="px-4 py-3 text-left text-sm font-semibold">Fornecedor</th>
              <th className="px-4 py-3 text-left text-sm font-semibold">Data</th>
              <th className="px-4 py-3 text-right text-sm font-semibold">Valor</th>
              <th className="px-4 py-3 text-center text-sm font-semibold">Status</th>
              <th className="px-4 py-3 text-center text-sm font-semibold">Próxima ação</th>
            </tr>
          </thead>
          <tbody>
            {pedidos.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-10 text-center text-sm text-slate-500">
                  Nenhum pedido encontrado.
                </td>
              </tr>
            ) : (
              pedidos.map((pedido) => (
                <Fragment key={pedido.id}>
                  <tr
                    className="cursor-pointer border-t hover:bg-slate-50"
                    onClick={() => abrirPedido(pedido)}
                    title={pedido.status === "rascunho" ? "Clique para editar" : "Clique para ver"}
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          className="font-semibold text-blue-700 hover:underline"
                          onClick={(event) => {
                            event.stopPropagation();
                            abrirPedido(pedido);
                          }}
                        >
                          {pedido.numero_pedido}
                        </button>
                        {pedido.foi_alterado_apos_envio && (
                          <span
                            className="rounded bg-orange-100 px-2 py-1 text-xs font-semibold text-orange-700"
                            title="Este pedido foi alterado apos o envio"
                          >
                            Alterado
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {obterFornecedorPorId(pedido.fornecedor_id)?.nome || pedido.fornecedor_id}
                    </td>
                    <td className="px-4 py-3">{formatarDataPedido(pedido.data_pedido)}</td>
                    <td className="px-4 py-3 text-right font-semibold">
                      <MoneyCell value={pedido.valor_final} />
                    </td>
                    <td className="px-4 py-3 text-center">
                      <PedidoStatusBadge status={pedido.status} />
                    </td>
                    <td
                      className="px-4 py-3 text-center"
                      onClick={(event) => event.stopPropagation()}
                    >
                      <div className="flex justify-center gap-2">
                        {acaoPrincipal(pedido)}
                        <ActionButton
                          icon={MoreHorizontal}
                          intent="neutral"
                          onClick={() =>
                            setPedidoAcoesAberto((atual) =>
                              atual === pedido.id ? null : pedido.id,
                            )
                          }
                          size="xs"
                          tone="soft"
                          title="Mostrar todas as acoes"
                          aria-expanded={pedidoAcoesAberto === pedido.id}
                        >
                          Mais
                        </ActionButton>
                      </div>
                    </td>
                  </tr>

                  {pedidoAcoesAberto === pedido.id ? (
                    <tr className="border-t border-blue-100 bg-blue-50/60">
                      <td colSpan={6} className="px-4 py-3">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                          <div>
                            <p className="text-xs font-bold uppercase tracking-wide text-blue-700">
                              Acoes do pedido {pedido.numero_pedido}
                            </p>
                            <p className="text-xs text-slate-500">
                              Consulta, exportação e mudanças menos frequentes
                            </p>
                          </div>
                          <div className="flex flex-wrap items-center justify-end gap-2">
                            <ActionButton
                              icon={Eye}
                              intent="neutral"
                              onClick={() => executarAcao(() => verDetalhes(pedido))}
                              size="xs"
                              tone="soft"
                            >
                              Ver detalhes
                            </ActionButton>
                            <ExportActionButton
                              type="pdf"
                              onClick={() => executarAcao(() => exportarPDF(pedido.id))}
                              title="Exportar PDF"
                            >
                              PDF
                            </ExportActionButton>
                            <ExportActionButton
                              type="excel"
                              onClick={() => executarAcao(() => exportarExcel(pedido.id))}
                              title="Exportar Excel"
                            >
                              Excel
                            </ExportActionButton>

                            {pedido.status === "confirmado" ? (
                              <ActionButton
                                icon={Package}
                                intent="neutral"
                                onClick={() => executarAcao(() => abrirRecebimento(pedido))}
                                size="xs"
                                tone="soft"
                              >
                                Receber sem confronto
                              </ActionButton>
                            ) : null}
                            {pedido.status === "recebido_parcial" ? (
                              <ActionButton
                                icon={Search}
                                intent="info"
                                onClick={() => executarAcao(() => abrirConfronto(pedido))}
                                size="xs"
                                tone="soft"
                              >
                                Conferir NF
                              </ActionButton>
                            ) : null}
                            {pedido.status !== "rascunho" && pedido.status !== "recebido_total" ? (
                              <ActionButton
                                icon={RotateCcw}
                                intent="warning"
                                onClick={() => executarAcao(() => reverterStatus(pedido.id))}
                                size="xs"
                                tone="soft"
                              >
                                Reverter
                              </ActionButton>
                            ) : null}
                            {pedido.status !== "recebido_total" && pedido.status !== "cancelado" ? (
                              <ActionButton
                                icon={Trash2}
                                intent="delete"
                                onClick={() => executarAcao(() => cancelarPedido(pedido))}
                                size="xs"
                                tone="soft"
                              >
                                {pedido.status === "rascunho" ? "Excluir" : "Cancelar"}
                              </ActionButton>
                            ) : null}
                          </div>
                        </div>
                      </td>
                    </tr>
                  ) : null}
                </Fragment>
              ))
            )}
          </tbody>
        </table>
      </div>
      <PaginationControls
        currentPage={paginaAtual}
        disabled={loading}
        itemName="pedidos"
        itemsPerPage={pedidosPorPagina}
        onItemsPerPageChange={onItemsPerPageChange}
        onPageChange={onPageChange}
        pageSizeOptions={[10, 20, 50]}
        totalItems={totalPedidos}
        totalPages={paginasTotal}
        variant="bottom"
      />
    </div>
  );
}
