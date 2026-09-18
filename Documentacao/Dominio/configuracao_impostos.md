---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — configuracao_impostos

Ver [[formas_pagamento_taxas]].

## Definição
Configuração de percentual de imposto (por tenant), usada para calcular margem líquida na análise de venda do PDV.

## Confirmado no código
- Modelo: `formas_pagamento_models.py:58-85` (`ConfiguracaoImposto`).
- Colunas: `nome`, `percentual` (Numeric 5,2), `ativo`, `padrao` (flag de config padrão), `descricao`.

## Relacionamentos
- Sem FK de saída nem de entrada.

## Utilizado por
- `formas_pagamento_routes_parts/impostos_routes.py:75` (CRUD de configurações de imposto).
- `formas_pagamento_routes_parts/analise_routes.py:13,208-212` — busca config padrão (`ativo=True, padrao=True`) para calcular margem líquida na análise de venda.

## Não identificado
- Nada notável.
