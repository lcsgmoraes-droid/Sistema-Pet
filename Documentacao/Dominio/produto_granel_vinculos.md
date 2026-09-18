---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — produto_granel_vinculos

Ver [[Produto]], [[granel_conversoes]], [[estoque_fracionamento_vinculos]].

## Definição
Liga um produto "fechado" (origem) a um produto "a granel" (kg), autorizando a conversão de um pacote fechado em quantidade vendável a granel. Conceito irmão de [[estoque_fracionamento_vinculos]] (que serve para fracionamento clínico, não venda a granel) — mesmo padrão estrutural, domínios deliberadamente separados.

## Confirmado no código
- Modelo: `produtos_estoque_models.py:120-147` (`ProdutoGranelVinculo`).
- Colunas: `produto_origem_id`, `produto_granel_id`, `ativo`, `observacao`, `user_id` (nullable).
- Unique `(tenant_id, produto_origem_id, produto_granel_id)`.

## Relacionamentos
- FKs de saída: `produto_origem_id → produtos.id`, `produto_granel_id → produtos.id`, `user_id → users.id` (nullable) — linhas 137, 138, 141.
- Referenciada por: nenhuma FK de outra tabela; [[granel_conversoes]] é o log de execução (não referencia esta tabela por FK direta).

## Utilizado por
- `estoque/granel.py` (`_obter_ou_criar_vinculo_granel`, `_resolver_origem_por_payload_granel`, `executar_conversao_granel`).
- `routes/app_mobile_funcionario_pdv/granel.py`, `services/produto_merge_service.py`.

## Não identificado
- Nada notável.
