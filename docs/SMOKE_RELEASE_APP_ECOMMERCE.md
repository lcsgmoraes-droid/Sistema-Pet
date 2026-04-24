# Smoke de release - App, ecommerce, PDV e entregas

Objetivo: validar rapidamente se o sistema esta seguro para uso diario antes de liberar para clientes piloto.

## 1. Checks tecnicos

Execute antes de publicar qualquer pacote:

```bash
cd backend
DEBUG=false python -m pytest tests/unit/test_entrega_status_contract.py tests/unit/test_ecommerce_checkout_idempotency.py tests/unit/test_ecommerce_cart_contract.py tests/unit/test_ecommerce_webhook_payment_contract.py
```

```bash
cd frontend
npm run build
```

```bash
cd app-mobile
npm run check
```

## 2. Contrato de pagamento temporario

Enquanto a intermediadora nao estiver integrada:

- Carrinho no app/ecommerce nao e pedido comercial.
- Carrinho nao deve aparecer no caixa/PDV.
- Carrinho nao deve reservar estoque.
- Checkout deve aceitar apenas PIX, debito e credito.
- Finalizacao deve ficar bloqueada com mensagem de pagamento online nao configurado.
- Nenhum pedido/venda deve ser liberado para separacao, caixa ou entrega sem pagamento aprovado.

## 3. Fluxo ecommerce/app

1. Abrir vitrine publica e app.
2. Adicionar produto ao carrinho.
3. Alterar quantidade e remover item.
4. Validar que estoque exibido nao foi reservado pelo carrinho.
5. Abrir aba Beneficios pelo menu inferior.
6. Confirmar que ranking, carimbos, cashback e cupons aparecem sem erro para cliente novo.
7. Tocar em Cashback e validar que o extrato abre mesmo sem movimentacoes.
8. Tocar em Ver todos os cupons e validar lista vazia ou cupons existentes.
9. Copiar um cupom ativo, quando existir.
10. Selecionar PIX, debito e credito em testes separados.
11. Tentar finalizar.
12. Confirmar que a UI fala em pagamento pendente/analise, nunca em pedido pago.
13. Confirmar que o backend bloqueia a finalizacao enquanto nao houver gateway.
14. Conferir no PDV/caixa que o carrinho nao apareceu como venda/pedido.

## 4. Fluxo entrega

1. Criar venda finalizada com entrega no PDV.
2. Conferir que aparece em Entregas Abertas.
3. Criar rota com essa venda.
4. Confirmar que a venda saiu de Entregas Abertas.
5. Iniciar rota no painel ou app do entregador.
6. Marcar parada como entregue.
7. Repetir o clique/envio de "marcar entregue" para simular retry de internet.
8. Fechar rota.
9. Repetir fechamento de rota para simular retry.
10. Confirmar que a rota nao volta para abertas.
11. Confirmar que a venda nao volta para entregas pendentes.
12. Confirmar no PDV que a venda mostra a tag "Entregue".

## 5. Criterio de bloqueio

Bloqueie release se acontecer qualquer um destes pontos:

- carrinho aparecer no PDV/caixa;
- checkout aceitar dinheiro, boleto, transferencia ou voucher;
- venda entregue voltar para `pendente`;
- rota concluida aparecer como aberta;
- tag "Entregue" nao aparecer no PDV apos entrega;
- aba Beneficios quebrar, ficar em loading infinito ou nao abrir cashback/cupons;
- app mobile apontar para ambiente errado;
- build/typecheck/teste obrigatorio falhar.
