---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — conciliacao_lotes

Ver [[conciliacao_importacoes]], [[movimentacoes_bancarias]], [[ContaReceber]].

## Definição
Lote de recebimento de cartão (previsto → informado → creditado, ou divergente) — máquina de estados de conciliação de cartão.

## Confirmado no código
- Modelo: `conciliacao_models.py:380-462` (`ConciliacaoLote`). Herda `BaseTenantModel` diretamente (diferente das demais classes deste arquivo, que usam `TenantScoped`+`Base` cru).
- Colunas: `status_lote` (previsto/informado/creditado/divergente), `valor_bruto`/`valor_liquido`/`valor_descontos`, `bandeira`, `modalidade`, `quantidade_parcelas` (comentado como "ContaReceber vinculadas").
- ⚠️ Relationship comentada/desativada: `# parcelas = relationship("ContaReceber", ...) # TEMPORARIAMENTE COMENTADO - ContaReceber não tem back_populates` — vínculo lógico com [[ContaReceber]] pretendido mas nunca implementado; `quantidade_parcelas` é hoje só um contador manual, sem FK ou tabela de associação garantindo integridade.

## Relacionamentos
- FKs de saída: `importacao_pagamentos_id`/`importacao_ofx_id → conciliacao_importacoes.id` (SET NULL), `movimentacao_bancaria_id → movimentacoes_bancarias.id` (SET NULL).
- Sem referências de entrada confirmadas.

## Utilizado por
- ❓ Nenhuma rota/service que instancie a classe diretamente foi confirmada nesta pesquisa — possível subutilização a validar com o time.

## Não identificado
- ⚠️ Vínculo com [[ContaReceber]] existe só conceitualmente (campo contador), não como relação de banco garantida.
- ❓ Uso real (quem escreve nesta tabela) não confirmado.
