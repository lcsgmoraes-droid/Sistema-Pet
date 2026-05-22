# App mobile vendedor/funcionario

Backlog combinado para depois da tela de Ponto de Equilibrio.

## MVP do vendedor

- Perfil de login para funcionario/vendedor, separado dos fluxos de cliente, veterinario e entregador.
- Consulta de preco por camera: bipar codigo de barras e mostrar produto, preco, estoque e avisos relevantes.
- Pesquisa manual por nome, codigo, SKU ou codigo de barras.
- PDV simplificado no app: bipar produtos para formar carrinho, ajustar quantidade e remover itens.
- Selecionar ou pesquisar cliente durante a venda.
- Mostrar dados do cliente, beneficios, saldo/historico de compras e alertas que ja existem no PDV web.
- Registrar venda com formas simples: PIX estatico, cartao passado fora do app e dinheiro com calculo de troco.
- Gerar comprovante/recibo e manter a venda integrada ao ERP, estoque, financeiro e comissoes.

## Fora do MVP inicial

- Desconto com autorizacao.
- Sangria, suprimento e demais rotinas completas de caixa.
- NFC-e dentro do app mobile na primeira etapa.

## Ajuste de escopo

- A antiga ideia de conferencia de prateleira vira lancamento/balanco de produto.
- Reaproveitar a tela e regras de Balanco de Produto do ERP sempre que possivel, com leitura por camera para acelerar a contagem.

## Observacoes tecnicas

- O scanner do app ja existe no fluxo de cliente e deve ser reaproveitado.
- O carrinho precisa usar a mesma validacao de estoque/preco/beneficio do PDV web para evitar divergencia.
- Qualquer baixa de estoque deve acontecer apenas quando a venda for finalizada.
