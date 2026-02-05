# AI CORE - Human-in-the-Loop Framework

## 🎯 Quick Start

### Instalar dependências
```bash
pip install sqlalchemy pydantic fastapi
```

### Executar migration
```bash
cd backend
alembic upgrade head
```

### Uso básico

```python
from app.ai_core import (
    DecisionService,
    ReviewService,
    LearningService
)
from app.db import get_db

db = next(get_db())

# Instanciar serviços
decision_service = DecisionService(db, engines=[...])
review_service = ReviewService(db)
learning_service = LearningService(db)

# 1. IA decide
result = await decision_service.decide(context)

if result.requires_human_review:
    # 2. Listar pendentes
    pendentes = review_service.get_pending_reviews(tenant_id=1)
    
    # 3. Humano revisa
    from app.ai_core.domain.review import HumanReviewFeedback, DecisionReviewStatus
    
    feedback = HumanReviewFeedback(
        request_id=result.request_id,
        reviewer_id=10,
        action=DecisionReviewStatus.CORRECTED,
        corrected_decision={"categoria_id": 18}
    )
    
    event = review_service.submit_review(feedback)
    
    # 4. Learning aprende
    await learning_service.process_review_event(event)
```

## 📁 Estrutura

```
ai_core/
├── domain/
│   ├── review.py          # ReviewQueueEntry, DecisionReviewStatus
│   ├── events.py          # DecisionReviewedEvent
│   └── decision.py        # DecisionResult
│
├── services/
│   ├── review_service.py      # Fila de revisão
│   ├── learning_service.py    # Aprendizado
│   └── decision_service.py    # Decisões
│
├── models/
│   └── decision_log.py    # ReviewQueueModel, DecisionLog
│
└── examples/
    └── extrato_review_flow.py  # Exemplo completo
```

## 🔄 Fluxo

```
┌──────────────┐
│ DecisionService │ → Confiança MEDIUM/LOW
└────────┬─────────┘
         │
         ▼
┌──────────────┐
│ ReviewQueue  │ → Fila de revisão
└────────┬─────────┘
         │
         ▼
┌──────────────┐
│ Humano revisa│ → APPROVED/CORRECTED/REJECTED
└────────┬─────────┘
         │
         ▼
┌──────────────┐
│ ReviewService│ → Publica DecisionReviewedEvent
└────────┬─────────┘
         │
         ▼
┌──────────────┐
│LearningService│ → Ajusta padrões
└──────────────┘
```

## 📊 Política de Confiança

| Score | Nível      | Ação                     |
|-------|------------|--------------------------|
| 0-39  | VERY_LOW   | Review Queue (URGENT)    |
| 40-59 | LOW        | Review Queue (HIGH)      |
| 60-79 | MEDIUM     | Review Queue (LOW/MED)   |
| 80-89 | HIGH       | Executar + audit         |
| 90-100| VERY_HIGH  | Executar automaticamente |

## 🎓 Aprendizado

### APPROVED
- +3 confidence_boost
- +100% success_rate
- Reforça padrão

### CORRECTED
- Atualiza output_preference
- -5 confidence_boost
- Ajusta success_rate

### REJECTED
- -10 confidence_boost
- Pode desativar padrão

## 📝 Eventos

### DecisionReviewedEvent

```python
{
    "event_id": "evt_20260123_abc123",
    "decision_id": "req_abc123",
    "tenant_id": 1,
    "reviewer_id": 10,
    "action_taken": "corrected",
    "original_decision": {"categoria_id": 15},
    "corrected_data": {"categoria_id": 18},
    "comment": "Era água, não energia"
}
```

## 🔧 Configuração

### DecisionService

```python
decision_service = DecisionService(
    db=db,
    engines=[rule_engine, ml_engine],
    confidence_calculator=ConfidenceCalculator(),
    decision_policy=DecisionPolicy(),
    review_service=ReviewService(db)  # Opcional
)
```

### ReviewService

```python
review_service = ReviewService(db)

# Listar pendentes
pendentes = review_service.get_pending_reviews(
    tenant_id=1,
    decision_type="categorizar_lancamento",
    priority=ReviewPriority.HIGH,
    limit=50
)

# Estatísticas
stats = review_service.get_review_stats(tenant_id=1)
# {"pending": 15, "approved": 45, "corrected": 12, ...}
```

## 🧪 Testes

```python
# Testar fluxo completo
from app.ai_core.examples.extrato_review_flow import exemplo_fluxo_completo

await exemplo_fluxo_completo()
```

## 📚 Documentação Completa

Ver [HUMAN_IN_THE_LOOP_FRAMEWORK.md](../../HUMAN_IN_THE_LOOP_FRAMEWORK.md)

## 🚀 Próximos Passos

1. ✅ Framework HITL implementado
2. ⏳ Criar endpoints REST
3. ⏳ UI de revisão
4. ⏳ Event Bus (RabbitMQ/Kafka)
5. ⏳ Métricas avançadas
6. ⏳ Webhooks de notificação

## 📞 Suporte

Ver documentação completa ou exemplo em `examples/extrato_review_flow.py`.
