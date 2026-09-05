# Estoque mínimo e máximo

Acesso: **Produtos / Estoque → Estoque mínimo e máximo**.

O relatório compara o saldo atual com os limites cadastrados em cada produto.
Mostra código, categoria, marca, fornecedor principal, unidade, saldo, mínimo,
máximo, situação, falta até o mínimo e excesso sobre o máximo.

## Regras

- **Abaixo do mínimo:** saldo menor que o mínimo positivo cadastrado.
- **No mínimo:** saldo igual ao mínimo positivo cadastrado.
- **Acima do máximo:** saldo maior que o máximo positivo cadastrado.
- **Dentro dos limites:** respeita os limites definidos; inclui saldo igual ao máximo.
- **Sem limites:** mínimo e máximo vazios ou zero. Um limite isolado é suficiente
  para comparar o estoque; o limite ausente não gera falta ou excesso.
- **Revisar limites:** algum limite é negativo ou o máximo positivo é menor que
  o mínimo. As quantidades de falta e excesso ficam em branco até corrigir o cadastro.

A falta é a quantidade necessária para atingir o mínimo, não uma sugestão para
comprar até o máximo. Um saldo negativo aumenta essa falta. Não se somam unidades
de produtos diferentes no resumo (por exemplo, quilos e unidades).

O saldo usado é o atual, antes de descontar reservas. Variações e kits físicos
entram individualmente; serviços, produtos pai e kits virtuais ficam de fora.
O relatório exige a permissão `produtos.visualizar` e respeita o escopo de empresa.

## Consulta e exportação

Há filtros por nome/código/EAN, categoria, marca, fornecedor principal ou alternativo,
situação, cadastro ativo/inativo e saldo zerado/negativo. Clicar nos indicadores
seleciona uma situação. O resumo considera os demais filtros antes da paginação.

**Exportar Excel** gera um `.xlsx` com todos os resultados do filtro atual, em todas
as páginas. Quantidades continuam numéricas e códigos preservam zeros à esquerda.
O nome do produto abre suas movimentações para conferência.

## Validação

- Backend: `python -m pytest tests/unit/test_relatorio_limites_estoque.py tests/unit/test_produtos_relatorios_routes_contract.py -q`.
- Frontend: `node --test src/pages/estoque-limites/estoqueLimitesUtils.test.mjs`.
- Compilação: `npm run build` na pasta `frontend`.
- Conferência visual e exportação em navegador com dados fictícios.

Endpoint: `GET /produtos/relatorio/limites-estoque`. A implementação não requer
migração nem alteração nos aplicativos mobile.
