# 🧠 AI CORE - Núcleo de Inteligência Artificial

Sistema centralizado para todas as decisões inteligentes do sistema Pet Shop Pro.

## 🎯 O que é?

O AI Core é um **orquestrador de decisões** que:
- Recebe contexto (dados estruturados)
- Analisa usando múltiplos motores (regras, ML, LLM)
- Retorna decisão + explicação + confiança
- **Nunca executa** ações sozinho
- Aprende com feedback humano

## 📂 Estrutura

```
ai_core/
├── domain/          # DTOs (DecisionContext, DecisionResult)
├── engines/         # Motores de decisão (rule, statistical, llm)
├── analyzers/       # Fachadas especializadas (extrato, venda, whatsapp)
├── models/          # Persistência (DecisionLog, FeedbackLog)
└── services/        # Orquestradores (DecisionService, LearningService)
```

## 🚀 Quick Start

### 1. Instalar

```bash
python migrate_ai_core.py
```

### 2. Usar

```python
from app.ai_core.engines.rule_engine import RuleEngine
from app.ai_core.services.decision_service import DecisionService
from app.ai_core.analyzers.extrato_analyzer import ExtratoAnalyzer

# Setup
engines = [RuleEngine()]
decision_service = DecisionService(db=db, engines=engines)
analyzer = ExtratoAnalyzer(decision_service=decision_service, db=db)

# Categorizar extrato
result = await analyzer.categorizar_lancamento(
    user_id=123,
    descricao="PIX ENERGISA",
    valor=-150.00,
    data="2026-01-23"
)

print(f"Categoria: {result.decision['categoria_nome']}")
print(f"Confiança: {result.confidence:.1f}%")
print(f"Motivos: {result.reasons}")
```

### 3. Feedback

```python
from app.ai_core.services.learning_service import LearningService

learning_service = LearningService(db=db)

await learning_service.process_feedback(
    user_id=123,
    decision_id=result.request_id,
    feedback_type="aprovado"  # ou "corrigido", "rejeitado"
)
```

## 🎓 Conceitos

### DecisionContext (Input)
```python
DecisionContext(
    user_id=123,  # Multi-tenant obrigatório
    decision_type=DecisionType.CATEGORIZAR_LANCAMENTO,
    primary_data={"descricao": "...", "valor": -150},
    additional_data={"historico": [...]}  # Opcional
)
```

### DecisionResult (Output)
```python
{
    "decision": {"categoria_id": 15, "categoria_nome": "Energia"},
    "confidence": 92.5,  # 0-100
    "confidence_level": "alta",  # muito_baixa|baixa|media|alta|muito_alta
    "reasons": ["Keyword ENERGISA detectada", "Padrão usado 23x"],
    "evidence": [Evidence(source="keyword", value="energisa", ...)],
    "requires_human_review": False,  # Auto-aplicar ou não
    "engine_used": "rule_engine",
    "processing_time_ms": 5.2
}
```

## 🔧 Motores Disponíveis

| Motor | Tier | Velocidade | Explicabilidade | Use quando |
|-------|------|------------|-----------------|------------|
| **RuleEngine** | 1 | < 10ms | ★★★★★ | Regras determinísticas |
| **StatisticalEngine** | 2 | < 500ms | ★★★★☆ | ML/estatística local |
| **LLMEngine** | 3 | < 3s | ★★★☆☆ | Casos complexos/NLP |

## 📊 Logs & Auditoria

Toda decisão é registrada em `ai_decision_logs`:

```sql
SELECT 
    decision_type,
    confidence,
    requires_human_review,
    engine_used,
    created_at
FROM ai_decision_logs
WHERE user_id = 123
ORDER BY created_at DESC;
```

## 🎯 Aplicações Atuais

| Analyzer | Status | Descrição |
|----------|--------|-----------|
| **ExtratoAnalyzer** | ✅ Produção | Categoriza lançamentos bancários |
| **VendaAnalyzer** | 🔜 Planejado | Sugestões de produtos no PDV |
| **WhatsAppAnalyzer** | 🔜 Planejado | Detecta intenção em mensagens |
| **EntregaAnalyzer** | 🔜 Planejado | Calcula frete inteligente |

## 📝 Documentação Completa

- [AI_CORE_ARCHITECTURE.md](../../../AI_CORE_ARCHITECTURE.md) - Arquitetura detalhada
- [AI_CORE_MIGRATION_GUIDE.md](../../../AI_CORE_MIGRATION_GUIDE.md) - Guia de migração

## 🧪 Testes

```bash
python test_ai_core.py
```

---

**Versão:** 1.0.0  
**Data:** 23/01/2026  
**Autor:** Sistema Pet Shop Pro
