---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — estoque_fracionamento_conversoes

Ver [[estoque_fracionamento_vinculos]], [[Produto]], [[granel_conversoes]].

## Definição
Log imutável de cada fracionamento clínico executado, com snapshot de estoque antes/depois em origem e destino. Análogo a [[granel_conversoes]], mas com schema mais rico.

## Confirmado no código
- Modelo: `estoque_fracionamento_models.py:61-117` (`EstoqueFracionamentoConversao`).
- Colunas: `vinculo_id`, `produto_origem_id`/`produto_destino_id`, `quantidade_origem`, `fator_conversao`, `quantidade_destino`, `unidade_origem`/`unidade_destino`, snapshots de estoque antes/depois (origem e destino), `custo_origem_unitario`/`custo_destino_unitario`, `lotes_origem_consumidos`/`lotes_destino_criados` (coluna `JSON` nativa — diferente de `estoque_movimentacoes.lotes_consumidos`, que usa `Text` com JSON manual), `aberto_em`, `validade_apos_abertura_em`, `documento`, `status` (default `"confirmado"`), `user_id`.

## Relacionamentos
- FKs de saída: `vinculo_id → estoque_fracionamento_vinculos.id` (RESTRICT), `produto_origem_id`/`produto_destino_id → produtos.id` (RESTRICT), `user_id → users.id`.
- Sem referências reversas.

## Utilizado por
- `estoque/fracionamento_clinico.py` (`executar_fracionamento_clinico`, cria o registro na linha 470).
- `estoque_fracionamento_routes.py`.

## Não identificado
- Nada notável — implementação de JSON mais correta que [[estoque_movimentacoes]], vale usar como referência se essa última for corrigida.
