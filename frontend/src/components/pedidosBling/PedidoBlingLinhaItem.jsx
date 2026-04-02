import { formatarMoeda } from './pedidoBlingUtils';

export default function PedidoBlingLinhaItem({ item }) {
  const reservado = !item.liberado_em && !item.vendido_em;
  const confirmado = !!item.vendido_em;
  const liberado = !!item.liberado_em;

  return (
    <div className="rounded-lg border border-gray-200 bg-white px-3 py-2">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono text-xs text-gray-500">{item.sku || 'SEM-SKU'}</span>
            {item.produto_bling_id && (
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                Produto Bling #{item.produto_bling_id}
              </span>
            )}
          </div>
          <p className="text-sm font-medium text-gray-900 mt-1">{item.descricao || '-'}</p>
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500 mt-1">
            <span>Qtd: {item.quantidade}</span>
            <span>Unitario: {formatarMoeda(item.valor_unitario)}</span>
            <span>Total: {formatarMoeda(item.total)}</span>
            {item.desconto != null && <span>Desconto: {formatarMoeda(item.desconto)}</span>}
          </div>
        </div>
        <span
          className={`text-xs px-2 py-0.5 rounded-full font-medium ${
            confirmado
              ? 'bg-green-50 text-green-700'
              : liberado
                ? 'bg-gray-100 text-gray-500'
                : reservado
                  ? 'bg-blue-50 text-blue-700'
                  : 'bg-gray-100 text-gray-500'
          }`}
        >
          {confirmado ? 'Baixado' : liberado ? 'Liberado' : 'Reservado'}
        </span>
      </div>
    </div>
  );
}
