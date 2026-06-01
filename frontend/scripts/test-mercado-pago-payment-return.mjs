import assert from 'node:assert/strict';
import {
  readMercadoPagoPaymentReturn,
  stripMercadoPagoPaymentReturnParams,
} from '../src/utils/mercadoPagoPaymentReturn.js';

assert.deepEqual(
  readMercadoPagoPaymentReturn('?payment_status=success&pedido_id=PED-123'),
  {
    status: 'success',
    level: 'success',
    message: 'Pagamento aprovado. Seu pedido sera atualizado automaticamente.',
    pedidoId: 'PED-123',
  },
  'retorno aprovado deve virar mensagem positiva com pedido',
);

assert.deepEqual(
  readMercadoPagoPaymentReturn('?payment_status=pending&pedido_id=PED-123'),
  {
    status: 'pending',
    level: 'success',
    message: 'Pagamento em analise. Atualize seus pedidos em instantes para acompanhar.',
    pedidoId: 'PED-123',
  },
  'retorno pendente deve orientar acompanhamento do pedido',
);

assert.equal(
  readMercadoPagoPaymentReturn('?foo=bar'),
  null,
  'URL sem retorno de pagamento nao deve gerar alerta',
);

assert.equal(
  stripMercadoPagoPaymentReturnParams('?payment_status=success&pedido_id=PED-123&foo=bar'),
  'foo=bar&view=pedidos',
  'limpeza da URL deve preservar outros parametros e manter a aba pedidos',
);

console.log('Mercado Pago payment return checks passed.');
