import { Check, Eye, Package, RotateCcw, Search, Send, Trash2 } from 'lucide-react';
import ActionButton from '../ui/ActionButton';
import ExportActionButton from '../ui/ExportActionButton';
import MoneyCell from '../ui/MoneyCell';
import StatusBadge from '../ui/StatusBadge';

const STATUS_PEDIDO_META = {
  rascunho: { label: 'RASCUNHO', intent: 'neutral' },
  enviado: { label: 'ENVIADO', intent: 'info' },
  confirmado: { label: 'CONFIRMADO', intent: 'success' },
  recebido_parcial: { label: 'PARCIAL', intent: 'warning' },
  recebido_total: { label: 'RECEBIDO', intent: 'success' },
  cancelado: { label: 'CANCELADO', intent: 'danger' },
};

function PedidoStatusBadge({ status }) {
  const meta = STATUS_PEDIDO_META[status] || {
    label: String(status || '-').replace('_', ' ').toUpperCase(),
    intent: 'neutral',
  };

  return (
    <StatusBadge intent={meta.intent} size="md">
      {meta.label}
    </StatusBadge>
  );
}

function formatarDataPedido(dataPedido) {
  if (!dataPedido) return '-';
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
  obterFornecedorPorId,
  pedidos,
  reverterStatus,
  verDetalhes,
}) {
  return (
    <div className="overflow-hidden rounded-lg bg-white shadow-md">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-semibold">Numero</th>
              <th className="px-4 py-3 text-left text-sm font-semibold">Fornecedor</th>
              <th className="px-4 py-3 text-left text-sm font-semibold">Data</th>
              <th className="px-4 py-3 text-right text-sm font-semibold">Valor</th>
              <th className="px-4 py-3 text-center text-sm font-semibold">Status</th>
              <th className="px-4 py-3 text-center text-sm font-semibold">Acoes</th>
            </tr>
          </thead>
          <tbody>
            {pedidos.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-10 text-center text-sm text-slate-500">
                  Nenhum pedido encontrado.
                </td>
              </tr>
            ) : pedidos.map((pedido) => (
              <tr
                key={pedido.id}
                className={`border-t hover:bg-gray-50 ${
                  pedido.status === 'rascunho' ? 'cursor-pointer' : ''
                }`}
                onClick={() => pedido.status === 'rascunho' && abrirEdicao(pedido)}
                title={pedido.status === 'rascunho' ? 'Clique para editar' : ''}
              >
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    {pedido.numero_pedido}
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
                <td className="px-4 py-3 text-center" onClick={(event) => event.stopPropagation()}>
                  <div className="flex justify-center gap-2">
                    <ActionButton
                      icon={Eye}
                      intent="neutral"
                      onClick={() => verDetalhes(pedido)}
                      size="xs"
                      tone="soft"
                      title="Ver detalhes completos do pedido"
                    >
                      Ver
                    </ActionButton>

                    <ExportActionButton
                      type="pdf"
                      onClick={() => exportarPDF(pedido.id)}
                      title="Exportar PDF"
                    >
                      PDF
                    </ExportActionButton>
                    <ExportActionButton
                      type="excel"
                      onClick={() => exportarExcel(pedido.id)}
                      title="Exportar Excel"
                    >
                      Excel
                    </ExportActionButton>

                    {pedido.status === 'rascunho' && (
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
                    )}
                    {pedido.status === 'enviado' && (
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
                    )}
                    {(pedido.status === 'confirmado' || pedido.status === 'recebido_parcial') && (
                      <ActionButton
                        icon={Search}
                        intent="info"
                        onClick={() => abrirConfronto(pedido)}
                        size="xs"
                        tone="soft"
                        title="Confrontar pedido com NF fiscal"
                      >
                        Conferir NF
                      </ActionButton>
                    )}
                    {(pedido.status === 'confirmado' || pedido.status === 'recebido_parcial') && (
                      <ActionButton
                        icon={Package}
                        intent="neutral"
                        onClick={() => abrirRecebimento(pedido)}
                        size="xs"
                        tone="soft"
                        title="Registrar entrada de produtos no estoque"
                      >
                        Receber
                      </ActionButton>
                    )}
                    {pedido.status !== 'rascunho' && pedido.status !== 'recebido_total' && (
                      <ActionButton
                        icon={RotateCcw}
                        intent="warning"
                        onClick={() => reverterStatus(pedido.id)}
                        size="xs"
                        tone="soft"
                        title="Reverter para status anterior"
                      >
                        Reverter
                      </ActionButton>
                    )}
                    {pedido.status !== 'recebido_total' && pedido.status !== 'cancelado' && (
                      <ActionButton
                        icon={Trash2}
                        intent="delete"
                        onClick={() => cancelarPedido(pedido)}
                        size="xs"
                        tone="soft"
                        title={pedido.status === 'rascunho' ? 'Cancelar/Excluir pedido em rascunho' : 'Cancelar pedido'}
                      >
                        {pedido.status === 'rascunho' ? 'Excluir' : 'Cancelar'}
                      </ActionButton>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
