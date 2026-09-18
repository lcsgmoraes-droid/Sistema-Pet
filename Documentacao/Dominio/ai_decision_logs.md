---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — ai_decision_logs

Ver [[Usuario]], [[ai_feedback_logs]], [[ai_review_queue]].

## Definição
🔴 **Parte de um módulo inteiro órfão.** Log de decisão de IA (framework de decisão automatizada), com confiança e flag de revisão humana necessária.

## Confirmado no código
- Modelo: `ai_core/models/decision_log.py:34-65` (`DecisionLog`).
- Colunas: `request_id` (unique), `input_data`/`output_data` (JSON), `confidence`, `requires_human_review`.
- Relationship 1:1 com `feedback` ([[ai_feedback_logs]]).

## Relacionamentos
- FK de saída: `user_id → users.id`.
- Referenciada por: [[ai_feedback_logs]]`.decision_id` (unique), `ai_review_queue.decision_log_id`.

## Utilizado por
- 🔴 **Só internamente ao pacote `ai_core/`** (`ai_core/services/decision_service.py`). Nenhuma rota, worker ou outro módulo do backend importa `ai_core` — confirmado por busca exaustiva. Não está em `db/base.py` nem em `alembic/env.py`.

## Não identificado
- 🔴 **Maior achado de módulo órfão do mapeamento inteiro**: todo o framework `ai_core/` (7 tabelas, engines, services) é código morto do ponto de vista do resto do sistema. Recomenda-se ao time decidir: remover, ou conectar (é um framework bem desenhado — decisão de IA, feedback, fila de revisão, circuit breaker — mas nunca chamado).
