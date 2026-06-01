const PAYMENT_RETURN_MESSAGES = {
  success: {
    level: 'success',
    message: 'Pagamento aprovado. Seu pedido sera atualizado automaticamente.',
  },
  pending: {
    level: 'success',
    message: 'Pagamento em analise. Atualize seus pedidos em instantes para acompanhar.',
  },
  failure: {
    level: 'error',
    message: 'Pagamento recusado ou cancelado. Voce pode tentar novamente pelo pedido.',
  },
};

export function readMercadoPagoPaymentReturn(search = '') {
  const params = new URLSearchParams(search);
  const rawStatus = String(params.get('payment_status') || '').trim().toLowerCase();
  const status = rawStatus === 'approved' ? 'success' : rawStatus;
  const config = PAYMENT_RETURN_MESSAGES[status];

  if (!config) {
    return null;
  }

  return {
    status,
    level: config.level,
    message: config.message,
    pedidoId: params.get('pedido_id') || '',
  };
}

export function stripMercadoPagoPaymentReturnParams(search = '') {
  const params = new URLSearchParams(search);
  [
    'payment_status',
    'pedido_id',
    'collection_id',
    'payment_id',
    'status',
    'merchant_order_id',
    'preference_id',
    'site_id',
    'processing_mode',
    'merchant_account_id',
  ].forEach((key) => params.delete(key));
  params.set('view', 'pedidos');
  return params.toString();
}
