# Motor de IA (AI Engine)

## 📋 Visão Geral

O **Motor de IA** é a base para interpretação inteligente de dados estruturados no ERP Pet Shop. Ele **NÃO** acessa banco de dados, **NÃO** cria regras de negócio e **NÃO** executa comandos. Apenas interpreta dados já processados e fornece insights acionáveis.

### ✅ O que a IA PODE fazer:
- Interpretar dados já processados (Read Models)
- Analisar Insights gerados pelo sistema
- Fornecer explicações contextualizadas
- Sugerir ações (mas não executá-las)
- Responder perguntas sobre o estado do negócio
- Gerar relatórios narrativos

### ❌ O que a IA NÃO PODE fazer:
- Acessar banco de dados diretamente
- Criar ou modificar regras de negócio
- Executar comandos (Commands) no sistema
- Modificar estado da aplicação
- Acessar APIs externas sem controle
- Processar dados não estruturados sem validação

## 🏗️ Arquitetura

```
app/ai/
├── __init__.py              # Exports principais
├── contracts.py             # Interfaces e contratos
├── prompt_builder.py        # Construtor de prompts
├── engine.py                # Motor de IA (mock por enquanto)
└── examples/                # Exemplos de uso
    ├── __init__.py
    └── exemplo_insights.py  # Exemplos práticos
```

## 🔧 Componentes

### 1. Contratos (contracts.py)

Define claramente o que a IA pode e não pode fazer:

```python
from app.ai.contracts import AIResponse, AIContext, AIContracts

# Verificar contratos
print(AIContracts.PROHIBITED)  # O que NÃO pode fazer
print(AIContracts.ALLOWED)     # O que PODE fazer
print(AIContracts.REQUIREMENTS) # Requisitos obrigatórios
```

**AIResponse**: Resposta estruturada e auditável
```python
@dataclass
class AIResponse:
    resposta: str           # Resposta em linguagem natural
    explicacao: str         # Como a IA chegou a essa conclusão
    fonte_dados: List[str]  # Origem dos dados (tabelas, insights)
    confianca: float        # Nível de confiança (0.0 a 1.0)
    timestamp: datetime     # Quando foi gerado
    tenant_id: int          # Multi-tenant obrigatório
    metadata: Dict[str, Any] # Dados adicionais para auditoria
```

**AIContext**: Contexto estruturado para a IA
```python
@dataclass
class AIContext:
    tenant_id: int
    objetivo: str
    dados_estruturados: Dict[str, Any]
    metadados: Dict[str, Any] = None
```

### 2. Prompt Builder (prompt_builder.py)

Constrói prompts controlados e explicáveis:

```python
from app.ai.prompt_builder import AIPromptBuilder

builder = AIPromptBuilder()

# Construir prompt genérico
context = {
    "vendas_mes": 50000,
    "clientes_ativos": 120
}
prompt = builder.build_prompt(context, "Como estão as vendas?")

# Construir prompt para insight específico
prompt = builder.build_insight_prompt(
    insight_type="ClienteRecorrenteAtrasado",
    insight_data={"cliente": "Maria", "valor": 450.00},
    objetivo="Como abordar este cliente?"
)

# Construir prompt para múltiplos insights
prompt = builder.build_multi_insight_prompt(
    insights=[insight1, insight2, insight3],
    objetivo="Qual a prioridade de ação?"
)
```

### 3. AI Engine (engine.py)

Motor de IA com implementação mock (extensível para OpenAI/Anthropic):

```python
from app.ai.engine import AIEngine, AIEngineFactory

# Criar engine em modo mock
engine = AIEngineFactory.create_mock_engine()

# Gerar resposta
response = await engine.generate_response(
    context={
        "tipo_insight": "ClienteRecorrenteAtrasado",
        "dados_insight": {"cliente": "Maria", "valor": 450.00}
    },
    objetivo="Como abordar este cliente?",
    tenant_id=1  # Multi-tenant obrigatório
)

# Acessar resposta
print(response.resposta)      # Resposta em linguagem natural
print(response.explicacao)    # Como chegou a essa conclusão
print(response.fonte_dados)   # Fontes utilizadas
print(response.confianca)     # Nível de confiança (0-1)
```

## 📚 Exemplos de Uso

### Exemplo 1: Análise de Cliente Atrasado

```python
import asyncio
from app.ai.engine import AIEngineFactory

async def analisar_cliente_atrasado():
    # Dados estruturados do insight
    insight_data = {
        "cliente_nome": "Maria Silva",
        "valor_devido": 450.00,
        "dias_atraso": 15,
        "total_compras_historico": 12
    }
    
    context = {
        "tipo_insight": "ClienteRecorrenteAtrasado",
        "dados_insight": insight_data
    }
    
    # Criar engine e gerar resposta
    engine = AIEngineFactory.create_mock_engine()
    response = await engine.generate_response(
        context=context,
        objetivo="Como abordar este cliente?",
        tenant_id=1
    )
    
    print(f"Resposta: {response.resposta}")
    print(f"Confiança: {response.confianca * 100:.1f}%")

# Executar
asyncio.run(analisar_cliente_atrasado())
```

### Exemplo 2: Uso com AIContext

```python
from app.ai.contracts import AIContext
from app.ai.engine import AIEngineFactory

async def usar_ai_context():
    # Forma recomendada: usar AIContext
    ai_context = AIContext(
        tenant_id=1,
        objetivo="Quais ações tomar com clientes atrasados?",
        dados_estruturados={
            "total_clientes_atrasados": 15,
            "valor_total_devido": 6750.00
        }
    )
    
    engine = AIEngineFactory.create_mock_engine()
    response = await engine.generate_response_from_ai_context(ai_context)
    
    return response
```

### Exemplo 3: Executar Exemplos Completos

```bash
# Executar todos os exemplos
cd backend
python -m app.ai.examples.exemplo_insights
```

Saída esperada:
```
🚀 EXEMPLOS DE USO DO MOTOR DE IA

============================================================
EXEMPLO 1: Cliente Recorrente Atrasado
============================================================

📊 CONTEXTO FORNECIDO:
   Cliente: Maria Silva
   Valor devido: R$ 450.00
   Dias de atraso: 15
   Histórico: 12 compras

❓ OBJETIVO:
   Como devo abordar este cliente para aumentar as chances de regularização?

🤖 RESPOSTA DA IA:
   Identifiquei que o cliente Maria Silva é um cliente recorrente...

💡 EXPLICAÇÃO:
   Esta análise foi baseada em 2 fonte(s) de dados...

📋 FONTE DOS DADOS:
   - Insight:ClienteRecorrenteAtrasado
   - ReadModel:Insights

📊 CONFIANÇA: 75.0%
⏰ TIMESTAMP: 2026-01-25T...
🏢 TENANT: 1
```

## 🔒 Segurança e Auditoria

### Multi-Tenant Obrigatório

Todas as operações exigem `tenant_id`:

```python
# ✅ CORRETO
response = await engine.generate_response(
    context=context,
    objetivo=objetivo,
    tenant_id=1  # Obrigatório
)

# ❌ ERRADO - Falhará
response = await engine.generate_response(
    context=context,
    objetivo=objetivo
    # Sem tenant_id
)
```

### Auditoria Completa

Todas as respostas são auditáveis:

```python
response = await engine.generate_response(...)

# Dados de auditoria
print(f"Tenant: {response.tenant_id}")
print(f"Timestamp: {response.timestamp}")
print(f"Fontes: {response.fonte_dados}")
print(f"Confiança: {response.confianca}")
print(f"Metadata: {response.metadata}")
```

### Rastreabilidade

```python
# Metadata inclui informações de rastreamento
response.metadata = {
    "prompt_length": 1234,
    "context_keys": ["tipo_insight", "dados_insight"],
    "mode": "mock",
    "objetivo": "..."
}
```

## 🚀 Próximos Passos

### Fase 1 (Atual): Base Funcional ✅
- [x] Estrutura de pastas
- [x] Contratos e interfaces
- [x] Prompt Builder
- [x] AI Engine (mock)
- [x] Exemplos de uso
- [x] Documentação

### Fase 2: Integração Real
- [ ] Integração com OpenAI GPT-4
- [ ] Integração com Anthropic Claude
- [ ] Sistema de cache de respostas
- [ ] Rate limiting
- [ ] Fallback entre provedores

### Fase 3: Endpoints
- [ ] Endpoint POST /api/ai/query
- [ ] Endpoint POST /api/ai/analyze-insight
- [ ] Endpoint POST /api/ai/batch-analysis
- [ ] Documentação OpenAPI

### Fase 4: Produtização
- [ ] Dashboard de uso de IA
- [ ] Métricas de confiança
- [ ] A/B testing de prompts
- [ ] Feedback loop de usuários

## 🧪 Testes

### Testar Manualmente

```bash
# Executar exemplos
python -m app.ai.examples.exemplo_insights
```

### Integrar em Testes Unitários

```python
import pytest
from app.ai.engine import AIEngineFactory

@pytest.mark.asyncio
async def test_ai_response():
    engine = AIEngineFactory.create_mock_engine()
    response = await engine.generate_response(
        context={"teste": "dados"},
        objetivo="Testar IA",
        tenant_id=1
    )
    
    assert response.tenant_id == 1
    assert 0.0 <= response.confianca <= 1.0
    assert len(response.fonte_dados) > 0
```

## 📖 Referências

- **Contratos**: [contracts.py](contracts.py)
- **Prompt Builder**: [prompt_builder.py](prompt_builder.py)
- **AI Engine**: [engine.py](engine.py)
- **Exemplos**: [examples/](examples/)

## 🤝 Contribuindo

Ao estender o Motor de IA:

1. **Sempre respeite os contratos** definidos em `contracts.py`
2. **Multi-tenant é obrigatório** em todas as operações
3. **Documente suas mudanças** com clareza
4. **Mantenha auditabilidade** em todas as respostas
5. **Teste com exemplos** antes de integrar

## 📝 Notas Importantes

- ⚠️ **Por enquanto o motor está em modo MOCK**
- ⚠️ **NÃO integre com OpenAI ainda**
- ⚠️ **NÃO crie endpoints ainda**
- ✅ **Foque em ter a base sólida e extensível**
- ✅ **Priorize segurança e auditabilidade**
- ✅ **Multi-tenant em tudo**

---

**Status**: Base implementada ✅ | Modo: Mock | Integração: Pendente
