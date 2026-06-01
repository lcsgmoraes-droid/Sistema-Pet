export function readMercadoPagoOAuthReturn(search = '') {
  const params = new URLSearchParams(search);
  const status = params.get('mercadopago_oauth');

  if (status === 'connected') {
    return {
      status: 'success',
      message: 'Mercado Pago conectado com sucesso.',
    };
  }

  if (status === 'error') {
    return {
      status: 'error',
      message: params.get('mercadopago_message') || 'Nao foi possivel concluir a conexao com o Mercado Pago.',
    };
  }

  return null;
}
