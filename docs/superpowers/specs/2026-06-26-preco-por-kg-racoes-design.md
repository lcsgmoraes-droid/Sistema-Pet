# Preco por kg de racoes - design

## Objetivo

Facilitar a comparacao de racoes com pesos diferentes, mostrando o preco de venda por kg no PDV e no cadastro, e oferecendo uma comparacao rapida entre racoes no carrinho.

## Escopo

- Calcular `preco / peso_embalagem` apenas quando o produto tiver peso em kg maior que zero e preco maior que zero.
- Usar o preco efetivo do PDV quando existir: `preco_venda_pdv`, depois `preco_venda_efetivo`, depois `preco_venda` ou `preco_unitario`.
- Mostrar `R$/kg` nas sugestoes de produto do PDV e nos itens do carrinho.
- Mostrar `R$/kg` no cadastro/listagem de produtos e no preview da aba Racao do cadastro.
- No modal da calculadora de racao do PDV, listar as racoes do carrinho ordenadas pelo menor `R$/kg`, com peso, preco e diferenca em relacao a melhor opcao.

## Fora do escopo

- Nao alterar banco de dados.
- Nao mudar nome salvo do produto.
- Nao fazer recomendacao nutricional automatica; a comparacao desta tarefa e somente por preco por kg.

## Testes

- Testar o utilitario de calculo e formatacao de `R$/kg`.
- Testar ordenacao e diferenca da comparacao.
- Rodar os testes focados do frontend e o build, pois ha mudancas em `frontend/src`.
