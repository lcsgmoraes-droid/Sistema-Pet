import PedidoBlingCard from '../components/pedidosBling/PedidoBlingCard';
import { STATUS_CONFIG } from '../components/pedidosBling/pedidoBlingUtils';
import usePedidosBlingListagem from '../hooks/usePedidosBlingListagem';

export default function PedidosBling() {
  const {
    abas,
    buscaPedido,
    carregando,
    carregar,
    consolidarDuplicidade,
    mudarStatus,
    pagina,
    paginas,
    pedidos,
    reconciliarFluxo,
    setPagina,
    statusFiltro,
    total,
  } = usePedidosBlingListagem();

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Pedidos Bling</h1>
        <p className="text-sm text-gray-500 mt-1">
          Pedidos recebidos via Bling com canal, referencias, cliente, financeiro, itens e vinculo com NF quando disponivel.
        </p>
      </div>

      <div className="flex gap-1 bg-gray-100 rounded-xl p-1 mb-6 w-fit flex-wrap">
        {abas.map((aba) => (
          <button
            key={aba.valor}
            onClick={() => mudarStatus(aba.valor)}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium transition ${
              statusFiltro === aba.valor ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {aba.label}
          </button>
        ))}
      </div>

      {buscaPedido && (
        <div className="mb-4 rounded-xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-800">
          Filtrado pelo pedido <span className="font-semibold">#{buscaPedido}</span>.
        </div>
      )}

      <div className="flex items-center justify-between mb-3">
        <p className="text-sm text-gray-500">
          {carregando ? 'Carregando...' : `${total} pedido${total !== 1 ? 's' : ''} encontrado${total !== 1 ? 's' : ''}`}
        </p>
        <button
          onClick={carregar}
          disabled={carregando}
          className="text-xs text-blue-600 hover:underline disabled:opacity-50"
        >
          Atualizar
        </button>
      </div>

      {carregando ? (
        <div className="text-center py-16 text-gray-400">Carregando pedidos...</div>
      ) : pedidos.length === 0 ? (
        <div className="text-center py-16">
          <div className="text-5xl mb-3">PED</div>
          <p className="text-gray-500 font-medium">Nenhum pedido encontrado</p>
          <p className="text-sm text-gray-400 mt-1">
            {statusFiltro
              ? `Sem pedidos com status "${STATUS_CONFIG[statusFiltro]?.label || statusFiltro}"`
              : 'Os pedidos aparecem aqui quando o Bling envia via webhook'}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {pedidos.map((pedido) => (
            <PedidoBlingCard
              key={pedido.id}
              pedido={pedido}
              onConfirmar={carregar}
              onCancelar={carregar}
              onConsolidarDuplicidade={consolidarDuplicidade}
              onReconciliarFluxo={reconciliarFluxo}
            />
          ))}
        </div>
      )}

      {paginas > 1 && (
        <div className="flex items-center justify-center gap-2 mt-6">
          <button
            onClick={() => setPagina((value) => Math.max(1, value - 1))}
            disabled={pagina === 1}
            className="px-3 py-1.5 rounded-lg border text-sm disabled:opacity-40 hover:bg-gray-50 transition"
          >
            Anterior
          </button>
          <span className="text-sm text-gray-600">
            Pagina {pagina} de {paginas}
          </span>
          <button
            onClick={() => setPagina((value) => Math.min(paginas, value + 1))}
            disabled={pagina === paginas}
            className="px-3 py-1.5 rounded-lg border text-sm disabled:opacity-40 hover:bg-gray-50 transition"
          >
            Proxima
          </button>
        </div>
      )}
    </div>
  );
}
