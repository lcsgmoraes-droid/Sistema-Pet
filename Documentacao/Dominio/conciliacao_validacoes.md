---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — conciliacao_validacoes

Ver [[conciliacao_importacoes]], [[conciliacao_logs]], [[conciliacao_recebimentos]].

## Definição
Resultado da validação em cascata de uma importação de conciliação de cartão (confiança ALTA/MEDIA/BAIXA, alertas).

## Confirmado no código
- Modelo: `conciliacao_models.py:470-598` (`ConciliacaoValidacao`).
- Colunas: `confianca`, `pode_processar` (comentário no código: "Sempre True — sistema nunca bloqueia"), `status_validacao`, `alertas` (JSONB).
- ⚠️ Relationship comentada: `# logs = relationship("ConciliacaoLog", ...) # Disabled - FK conciliacao_validacao_id não existe` — **esse comentário está incorreto**: esta própria tabela existe neste mesmo arquivo. É a raiz do achado de FK fantasma em [[conciliacao_logs]] e em [[conciliacao_recebimentos]] (ambos têm campo `*_id` apontando "informalmente" pra cá com o mesmo comentário equivocado).

## Relacionamentos
- FKs de saída: 3 FKs para a mesma tabela [[conciliacao_importacoes]] (`importacao_ofx_id`, `importacao_pagamentos_id`, `importacao_recebimentos_id`, todas CASCADE), `criado_por_id → users.id` (RESTRICT).
- Deveria ser referenciada por [[conciliacao_logs]] e [[conciliacao_recebimentos]], mas ambos os campos foram implementados como Integer solto por engano — ver achado ⚠️ acima.

## Utilizado por
- `conciliacao_routes.py`, `conciliacao_services_importacao.py`.

## Não identificado
- 🔴 **Achado mais concreto e replicável deste bloco**: o comentário "tabela não existe" foi copiado para pelo menos 2 arquivos diferentes ([[conciliacao_logs]], [[conciliacao_recebimentos]]) sem verificar que a tabela existe desde sempre neste mesmo arquivo. Recomenda-se ao time restaurar as duas FKs reais.
