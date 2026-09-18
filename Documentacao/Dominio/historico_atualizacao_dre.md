---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — historico_atualizacao_dre

Ver [[dre_periodos]], [[Usuario]].

## Definição
Log de auditoria de atualizações a um período de DRE (alteração, aprovação).

## Confirmado no código
- Modelo: `ia/aba7_extrato_models.py:219-246` (`HistoricoAtualizacaoDRE`).
- 3 FKs para `users.id`: `usuario_alteracao_id`, `aprovado_por`, `usuario_id`.
- Relationship `dre_periodo` (`back_populates="historico_atualizacoes"`), par com `DREPeriodo.historico_atualizacoes`.

## Relacionamentos
- FKs de saída: `dre_periodo_id → dre_periodos.id`, `usuario_alteracao_id`/`aprovado_por`/`usuario_id → users.id`.

## Utilizado por
- Módulo DRE Inteligente.

## Não identificado
- Nada notável.
