import { formatCurrency, formatDateTime } from './ecommerceMvpUtils';

const ORDER_STATUS_COLORS = {
  pendente: '#f59e0b',
  confirmado: '#3b82f6',
  enviado: '#8b5cf6',
  entregue: '#10b981',
  cancelado: '#ef4444',
};

function OrderPickupPassword({ password }) {
  if (!password) return null;

  return (
    <div style={{ background: '#fff7ed', border: '2px solid #f97316', borderRadius: 10, padding: 10, textAlign: 'center', marginTop: 8 }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: '#7c2d12', marginBottom: 2 }}>🔑 SENHA DE RETIRADA</div>
      <div style={{ fontSize: 20, fontWeight: 800, letterSpacing: 3, color: '#ea580c' }}>{password}</div>
      <div style={{ fontSize: 10, color: '#92400e', marginTop: 2 }}>Apresente na loja para retirar</div>
    </div>
  );
}

function OrderDriveStatus({ order, onDriveArrived }) {
  if (!order.is_drive || order.tipo_retirada !== 'proprio') return null;

  return (
    <div style={{ background: order.drive_entregue_at ? '#f0fdf4' : order.drive_chegou_at ? '#fef9c3' : '#f0f9ff', border: `2px solid ${order.drive_entregue_at ? '#22c55e' : order.drive_chegou_at ? '#eab308' : '#3b82f6'}`, borderRadius: 10, padding: 12, marginTop: 8, display: 'flex', flexDirection: 'column', gap: 6, alignItems: 'center' }}>
      {order.drive_entregue_at ? (
        <div style={{ color: '#15803d', fontWeight: 700, fontSize: 14 }}>✅ Entregue no Drive!</div>
      ) : order.drive_chegou_at ? (
        <>
          <div style={{ color: '#854d0e', fontWeight: 700, fontSize: 13 }}>🚗 Chegada registrada — aguarde a equipe!</div>
          <div style={{ color: '#78716c', fontSize: 11 }}>Registrado às {new Date(order.drive_chegou_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}</div>
        </>
      ) : (
        <>
          <div style={{ color: '#1d4ed8', fontWeight: 700, fontSize: 13 }}>🚗 Pedido com Drive</div>
          <div style={{ color: '#6b7280', fontSize: 11, textAlign: 'center' }}>Quando chegar no estacionamento, clique no botão abaixo.</div>
          <button
            onClick={() => onDriveArrived(order.pedido_id)}
            style={{ background: '#2563eb', color: '#fff', border: 'none', borderRadius: 10, padding: '10px 24px', fontWeight: 700, fontSize: 14, cursor: 'pointer', marginTop: 2 }}
          >
            🚗 Cheguei! Estou no estacionamento
          </button>
        </>
      )}
    </div>
  );
}

function OrderItems({ order }) {
  if (!Array.isArray(order.itens) || order.itens.length === 0) return null;

  return (
    <div style={{ marginTop: 10, borderTop: '1px solid #f1f5f9', paddingTop: 10, display: 'grid', gap: 6 }}>
      {order.itens.map((item, index) => (
        <div key={`${order.pedido_id}-${item.produto_id || index}`} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: '#6b7280' }}>
          <span>{item.nome || 'Produto'} × {item.quantidade}</span>
          <span>{formatCurrency(item.subtotal)}</span>
        </div>
      ))}
    </div>
  );
}

function OrderCard({ order, styles: S, onDriveArrived }) {
  const statusColor = ORDER_STATUS_COLORS[(order.status || '').toLowerCase()] || '#6b7280';

  return (
    <div style={S.orderCard}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, flexWrap: 'wrap' }}>
        <div>
          <div style={{ fontWeight: 700, fontSize: 14, color: '#1a1a2e', marginBottom: 2 }}>Pedido {order.pedido_id}</div>
          <div style={{ fontSize: 12, color: '#9ca3af' }}>{order.created_at ? new Date(order.created_at).toLocaleString('pt-BR') : '-'}</div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
          <span style={{ ...S.statusBadge(order.status), background: statusColor + '20', color: statusColor, border: `1px solid ${statusColor}40` }}>{order.status || 'Pendente'}</span>
          <div style={{ fontWeight: 800, fontSize: 16, color: '#1a1a2e' }}>{formatCurrency(order.total)}</div>
        </div>
      </div>

      <OrderPickupPassword password={order.palavra_chave_retirada} />
      <OrderDriveStatus order={order} onDriveArrived={onDriveArrived} />
      <OrderItems order={order} />

      {order.data_pagamento && (
        <div style={{ fontSize: 12, color: '#6b7280', marginTop: 6 }}>Pago em: {formatDateTime(order.data_pagamento)}</div>
      )}
    </div>
  );
}

export default function EcommerceOrdersPage({
  orders,
  ordersLoading,
  styles: S,
  onContinueShopping,
  onDriveArrived,
  onReload,
}) {
  const orderList = Array.isArray(orders) ? orders : [];

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: '28px 16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20, flexWrap: 'wrap', gap: 10 }}>
        <h2 style={{ margin: 0, fontSize: 26, fontWeight: 800, color: '#1c1917' }}>Meus Pedidos</h2>
        <button onClick={onReload} disabled={ordersLoading} style={{ background: '#f1f5f9', border: '1.5px solid #e5e7eb', color: '#374151', borderRadius: 10, padding: '8px 16px', fontWeight: 600, fontSize: 13, cursor: 'pointer' }}>
          {ordersLoading ? 'Atualizando...' : '↻ Atualizar'}
        </button>
      </div>

      {ordersLoading ? (
        <div style={{ textAlign: 'center', color: '#64748b', padding: 40 }}>Carregando pedidos...</div>
      ) : orderList.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '48px 0', display: 'grid', gap: 10, justifyItems: 'center' }}>
          <span style={{ fontSize: 48 }}>📋</span>
          <div style={{ fontSize: 16, fontWeight: 700, color: '#1a1a2e' }}>Nenhum pedido ainda</div>
          <div style={{ fontSize: 13, color: '#9ca3af' }}>Seus pedidos aparecerão aqui após a compra.</div>
          <button onClick={onContinueShopping} style={{ ...S.checkoutBig, width: 'auto', padding: '10px 24px' }}>Ir às compras</button>
        </div>
      ) : (
        <div style={{ display: 'grid', gap: 14 }}>
          {orderList.map((order) => (
            <OrderCard key={order.pedido_id} order={order} styles={S} onDriveArrived={onDriveArrived} />
          ))}
        </div>
      )}
    </div>
  );
}
