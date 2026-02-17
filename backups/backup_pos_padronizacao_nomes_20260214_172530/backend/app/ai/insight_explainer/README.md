```markdown
# Sistema de IA Explicadora de Insights

**Sprint 6 - Passo 2**

## 📋 Visão Geral

O **Sistema de IA Explicadora de Insights** transforma insights técnicos (Sprint 5) em explicações compreensíveis para humanos usando o AI Engine (Passo 1).

### Princípios Fundamentais

**A IA NÃO cria insights**
- Insights são gerados pelo InsightEngine (Sprint 5)
- A IA apenas interpreta e explica

**A IA NÃO altera severidade**
- Severidade é definida por regras determinísticas
- A IA respeita a classificação original

**A IA NÃO executa ações**
- A IA sugere abordagens
- Humanos decidem e executam

**A IA apenas explica e sugere**
- Transforma técnico em compreensível
- Contextualiza para audiência humana
- Sugere como abordar a situação

---

## 🏗️ Arquitetura

### Estrutura de Arquivos

```
backend/app/ai/insight_explainer/
├── __init__.py          # Exports principais
├── adapter.py           # InsightAIAdapter
├── prompts.py           # InsightPromptLibrary
├── service.py           # InsightExplanationService
├── examples.py          # Exemplos funcionais
└── README.md           # Esta documentação
```

### Fluxo de Dados

```
1. INSIGHT (Sprint 5)
   ↓
2. InsightAIAdapter
   ↓ Converte para AIContext
3. InsightPromptLibrary
   ↓ Aplica prompt especializado
4. AIEngine (Passo 1)
   ↓ Gera explicação
5. InsightExplanationService
   ↓ Formata resposta
6. INSIGHT EXPLANATION
   ↓
7. Usuário (PDV/WhatsApp/Dashboard)
```

---

## 🔧 Componentes

### 1. InsightAIAdapter

Converte Insights em AIContext para o AI Engine.

**Responsabilidades:**
- Extrair dados relevantes do Insight
- Formatar contexto estruturado
- Definir objetivo claro para a IA
- Preservar multi-tenancy

**Métodos principais:**
- `insight_to_ai_context()` - Converte Insight em AIContext
- `_get_default_objective()` - Define objetivo por tipo
- `_extract_structured_data()` - Extrai dados estruturados
- `validate_insight_for_explanation()` - Valida insight

**Exemplo:**
```python
from app.ai.insight_explainer import InsightAIAdapter

adapter = InsightAIAdapter()
ai_context = adapter.insight_to_ai_context(insight)
```

### 2. InsightPromptLibrary

Biblioteca de prompts especializados por tipo de insight.

**Tipos suportados:**
- `CLIENTE_RECORRENTE_ATRASADO` - Reengajamento empático
- `CLIENTE_INATIVO` - Reconquista estratégica
- `PRODUTOS_COMPRADOS_JUNTOS` - Cross-sell natural
- `KIT_MAIS_VANTAJOSO` - Comunicação de valor
- `CLIENTE_VIP` - Tratamento diferenciado
- `CLIENTE_EM_RISCO_CHURN` - Ação preventiva urgente
- `PRODUTO_TOP_VENDAS` - Maximização de oportunidade

**Métodos principais:**
- `get_prompt_for_tipo()` - Retorna prompt especializado

**Exemplo:**
```python
from app.ai.insight_explainer import InsightPromptLibrary

library = InsightPromptLibrary()
prompt = library.get_prompt_for_tipo(
    tipo=TipoInsight.CLIENTE_RECORRENTE_ATRASADO,
    dados_insight=dados
)
```

### 3. InsightExplanationService

Serviço principal que orquestra a explicação.

**Responsabilidades:**
- Orquestração do fluxo completo
- Validações de entrada
- Logging e auditoria
- Formatação de saída
- Multi-tenancy obrigatório

**Métodos principais:**
- `explicar_insight()` - Explica um insight
- `explicar_multiplos_insights()` - Explica em lote
- `get_statistics()` - Estatísticas do serviço

**Exemplo:**
```python
from app.ai.insight_explainer import InsightExplanationService

service = InsightExplanationService(use_mock=True)
explicacao = await service.explicar_insight(insight, tenant_id=1)

print(explicacao.titulo)
print(explicacao.explicacao)
print(explicacao.sugestao)
```

### 4. InsightExplanation

Estrutura de dados da explicação gerada.

**Campos:**
- `insight_id` - ID do insight original
- `tipo_insight` - Tipo do insight
- `titulo` - Título do insight
- `explicacao` - Explicação compreensível
- `sugestao` - Sugestão de ação
- `confianca` - Nível de confiança (0-1)
- `fonte_dados` - Fontes utilizadas
- `tenant_id` - Multi-tenant
- `timestamp` - Quando foi gerado
- `metadata` - Dados de auditoria

---

## 📖 Guia de Uso

### Uso Básico

```python
import asyncio
from app.insights.models import Insight, TipoInsight
from app.ai.insight_explainer import InsightExplanationService

async def exemplo_basico():
    # 1. Criar ou obter insight (normalmente vem do InsightEngine)
    insight = Insight(
        id="INS-001",
        tipo=TipoInsight.CLIENTE_RECORRENTE_ATRASADO,
        titulo="Maria Silva está atrasada",
        descricao="Cliente atrasado em 10 dias",
        # ... demais campos
        user_id=1
    )
    
    # 2. Criar serviço
    service = InsightExplanationService(use_mock=True)
    
    # 3. Gerar explicação
    explicacao = await service.explicar_insight(insight, tenant_id=1)
    
    # 4. Usar explicação
    print(f"Título: {explicacao.titulo}")
    print(f"Explicação: {explicacao.explicacao}")
    print(f"Sugestão: {explicacao.sugestao}")
    print(f"Confiança: {explicacao.confianca * 100:.1f}%")
    
    return explicacao

asyncio.run(exemplo_basico())
```

### Explicação em Lote

```python
async def exemplo_lote():
    insights = [insight1, insight2, insight3]
    
    service = InsightExplanationService(use_mock=True)
    explicacoes = await service.explicar_multiplos_insights(
        insights,
        tenant_id=1
    )
    
    for exp in explicacoes:
        print(f"{exp.titulo}: {exp.confianca * 100:.1f}%")
```

### Conversão de Insight para Dict

```python
explicacao = await service.explicar_insight(insight, tenant_id=1)
explicacao_dict = explicacao.to_dict()

# Enviar via API, salvar em banco, etc.
```

---

## 🧪 Executar Exemplos

```bash
cd backend
python -m app.ai.insight_explainer.examples
```

**Saída esperada:**
- Exemplo 1: Cliente Recorrente Atrasado
- Exemplo 2: Cliente Inativo
- Exemplo 3: Produtos Comprados Juntos
- Exemplo 4: Kit Mais Vantajoso
- Exemplo 5: Explicação em Lote

---

## 🔒 Segurança e Auditoria

### Multi-Tenant Obrigatório

```python
# ✅ CORRETO
explicacao = await service.explicar_insight(insight, tenant_id=1)

# ❌ ERRADO - Falhará se insight.user_id for None
explicacao = await service.explicar_insight(insight)
```

### Auditoria Completa

```python
explicacao.metadata = {
    "insight_severidade": "ATENCAO",
    "insight_entidade": "CLIENTE",
    "insight_entidade_id": 123,
    "ai_explicacao_original": "...",
    "ai_metadata": {...},
    "modo": "mock"
}
```

### Validação de Insights

```python
adapter = InsightAIAdapter()
valido, erro = adapter.validate_insight_for_explanation(insight)

if not valido:
    print(f"Insight inválido: {erro}")
```

---

## 🎯 Casos de Uso

### 1. PDV (Ponto de Venda)

```python
# No PDV, ao abrir ficha do cliente
cliente_insights = insightengine.get_insights_cliente(cliente_id)

for insight in cliente_insights:
    explicacao = await service.explicar_insight(insight, tenant_id)
    
    # Mostrar explicação ao atendente
    mostrar_alerta_pdv(
        titulo=explicacao.titulo,
        mensagem=explicacao.explicacao,
        sugestao=explicacao.sugestao
    )
```

### 2. WhatsApp Bot (Futuro)

```python
# Ao receber mensagem do cliente
if cliente_tem_insights(cliente_id):
    insights = get_insights_prioritarios(cliente_id)
    explicacao = await service.explicar_insight(insights[0], tenant_id)
    
    # Enviar mensagem personalizada
    enviar_whatsapp(
        telefone=cliente.telefone,
        mensagem=gerar_mensagem_whatsapp(explicacao)
    )
```

### 3. Dashboard de Insights

```python
# Dashboard mostrando insights do dia
insights_hoje = get_insights_hoje(tenant_id)
explicacoes = await service.explicar_multiplos_insights(
    insights_hoje,
    tenant_id
)

# Renderizar cards com explicações
for exp in explicacoes:
    renderizar_card(
        titulo=exp.titulo,
        explicacao=exp.explicacao,
        confianca=exp.confianca
    )
```

---

## 📊 Estatísticas

### Métricas do Serviço

```python
service = InsightExplanationService(use_mock=True)
stats = service.get_statistics()

print(stats)
# {
#     "modo": "mock",
#     "ai_engine": "AIEngine",
#     "prompt_library": "InsightPromptLibrary"
# }
```

---

## 🚀 Próximos Passos

### Passo 3: Integração com OpenAI

- [ ] Substituir mock por OpenAI GPT-4
- [ ] Configurar API keys
- [ ] Implementar cache de respostas
- [ ] Rate limiting por tenant

### Passo 4: Endpoints REST

- [ ] POST `/api/ai/insights/{id}/explicar`
- [ ] POST `/api/ai/insights/explicar-lote`
- [ ] GET `/api/ai/insights/{id}/explicacao`
- [ ] Documentação OpenAPI

### Passo 5: Integração PDV

- [ ] Componente React de Explicação
- [ ] Modal de insights explicados
- [ ] Alertas contextuais

### Passo 6: Integração WhatsApp

- [ ] Bot de insights proativos
- [ ] Mensagens personalizadas
- [ ] Agendamento de envios

---

## 🔗 Dependências

Este módulo depende de:

- **Sprint 5**: Insights (models.py, engine.py)
- **Passo 1**: AI Engine (engine.py, contracts.py, prompt_builder.py)

Não requer:
- ❌ Banco de dados
- ❌ Endpoints REST
- ❌ OpenAI API (usa mock por enquanto)

---

## 📝 Notas Importantes

- ⚠️ **Modo MOCK ativo** - Sem chamadas OpenAI ainda
- ⚠️ **Sem persistência** - Explicações não são salvas
- ⚠️ **Sem endpoints** - Apenas biblioteca Python
- ✅ **Multi-tenant obrigatório** - Validado em todas operações
- ✅ **Completamente auditável** - Logs e metadata completos
- ✅ **Pronto para produção** - Arquitetura extensível

---

## 🐛 Troubleshooting

### Erro: "Insight inválido: Insight sem user_id"

**Causa:** Insight sem tenant_id

**Solução:**
```python
insight = Insight(..., user_id=1)  # Multi-tenant obrigatório
```

### Erro: "Insight inválido: Insight sem título"

**Causa:** Insight malformado

**Solução:** Validar insight antes de explicar
```python
valido, erro = adapter.validate_insight_for_explanation(insight)
if not valido:
    raise ValueError(erro)
```

### Explicação genérica demais

**Causa:** Tipo de insight sem prompt especializado

**Solução:** Adicionar prompt especializado em `InsightPromptLibrary`

---

**Status**: Passo 2 Completo ✅ | Modo: Mock | Próximo: Integração OpenAI
```
