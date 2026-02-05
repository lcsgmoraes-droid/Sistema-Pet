# 🤝 SPRINT 4: HUMAN HANDOFF

**Objetivo:** Implementar transferência inteligente de conversas para atendentes humanos

---

## 📋 Escopo

### 1. **Sistema de Handoff**
- Detecção automática de situações que precisam humano
- Transferência manual (cliente solicita)
- Fila de atendimento
- Status de atendimento (aguardando, em atendimento, resolvido)

### 2. **Análise de Sentimento**
- Detectar frustração/raiva
- Detectar urgência
- Score de satisfação
- Trigger automático para handoff

### 3. **Interface de Atendimento**
- Dashboard de conversas ativas
- Chat em tempo real
- Histórico completo
- Notas internas

### 4. **Bot Assist**
- Sugestões de resposta para atendente
- Busca rápida de informações
- Atalhos para ações comuns
- Templates de resposta

### 5. **Métricas de Handoff**
- Taxa de transferência
- Tempo médio de espera
- Taxa de resolução
- Satisfação pós-atendimento

---

## 🗂️ Estrutura de Implementação

### **Passo 1: Database Schema**
```sql
-- Tabela de atendentes
CREATE TABLE whatsapp_agents (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    user_id UUID REFERENCES users(id),
    name VARCHAR(200),
    status VARCHAR(50), -- online, offline, busy
    max_concurrent_chats INT DEFAULT 5,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Tabela de handoffs
CREATE TABLE whatsapp_handoffs (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    session_id UUID REFERENCES whatsapp_sessions(id),
    phone_number VARCHAR(20),
    reason VARCHAR(50), -- auto_sentiment, manual_request, auto_repeat, auto_timeout
    sentiment_score DECIMAL(3,2), -- -1.0 a 1.0
    priority VARCHAR(20), -- low, medium, high, urgent
    status VARCHAR(50), -- pending, assigned, in_progress, resolved, cancelled
    assigned_to UUID REFERENCES whatsapp_agents(id),
    assigned_at TIMESTAMP,
    resolved_at TIMESTAMP,
    resolution_notes TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Tabela de notas internas
CREATE TABLE whatsapp_internal_notes (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    session_id UUID REFERENCES whatsapp_sessions(id),
    agent_id UUID REFERENCES whatsapp_agents(id),
    note TEXT,
    created_at TIMESTAMP
);

-- Tabela de avaliações
CREATE TABLE whatsapp_ratings (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    session_id UUID REFERENCES whatsapp_sessions(id),
    rating INT, -- 1 a 5
    feedback TEXT,
    created_at TIMESTAMP
);
```

### **Passo 2: Sentiment Analysis**
```python
# app/whatsapp/sentiment.py
class SentimentAnalyzer:
    def analyze(self, message: str) -> Dict:
        """
        Retorna:
        {
            "score": -1.0 a 1.0,  # negativo a positivo
            "label": "positive" | "neutral" | "negative",
            "confidence": 0.0 a 1.0,
            "emotions": {
                "anger": 0.8,
                "frustration": 0.6,
                ...
            }
        }
        """
```

### **Passo 3: Handoff Manager**
```python
# app/whatsapp/handoff_manager.py
class HandoffManager:
    def should_handoff(self, context, sentiment) -> tuple[bool, str]:
        """Decide se deve transferir para humano"""
        
    def create_handoff(self, session_id, reason, priority) -> Handoff:
        """Cria solicitação de handoff"""
        
    def assign_to_agent(self, handoff_id, agent_id):
        """Atribui para atendente"""
        
    def resolve_handoff(self, handoff_id, notes):
        """Marca como resolvido"""
```

### **Passo 4: Agent Dashboard API**
```python
# app/api/endpoints/agent_dashboard.py
@router.get("/conversations/pending")
def get_pending_conversations():
    """Lista conversas aguardando atendimento"""

@router.post("/conversations/{session_id}/take")
def take_conversation(session_id: str):
    """Atendente pega a conversa"""

@router.post("/conversations/{session_id}/message")
def send_agent_message(session_id: str, message: str):
    """Atendente envia mensagem"""

@router.get("/conversations/{session_id}/history")
def get_conversation_history(session_id: str):
    """Busca histórico completo"""

@router.post("/conversations/{session_id}/notes")
def add_internal_note(session_id: str, note: str):
    """Adiciona nota interna"""
```

### **Passo 5: Bot Assist**
```python
# app/whatsapp/bot_assist.py
class BotAssist:
    def suggest_responses(self, context) -> List[str]:
        """Sugere respostas prontas"""
        
    def quick_search(self, query) -> Dict:
        """Busca rápida de informações"""
        
    def get_customer_summary(self, phone_number) -> Dict:
        """Resumo do cliente para atendente"""
```

---

## 🎯 Implementação por Etapas

### **Etapa 1: Database + Models (30 min)**
- Criar migrations
- Criar SQLAlchemy models
- Criar Pydantic schemas

### **Etapa 2: Sentiment Analysis (45 min)**
- Implementar análise básica (keywords)
- Integrar com OpenAI (opcional)
- Testes de detecção

### **Etapa 3: Handoff Manager (1h)**
- Lógica de decisão
- Fila de atendimento
- Atribuição de prioridade

### **Etapa 4: API Endpoints (1h)**
- CRUD de atendentes
- Endpoints de dashboard
- Endpoints de chat

### **Etapa 5: Integração com AI Service (30 min)**
- Detectar quando transferir
- Pausar bot quando em handoff
- Retomar bot quando resolver

### **Etapa 6: Frontend Dashboard (2h)**
- Lista de conversas pendentes
- Interface de chat
- Histórico e notas
- Bot assist sidebar

---

## 📊 Métricas de Sucesso

- Taxa de handoff < 15%
- Tempo médio de espera < 2 min
- Taxa de resolução > 90%
- Satisfação > 4.5/5

---

## 🚀 Começar Agora

**Passo 1:** Criar migrations e models para handoff
**Tempo estimado:** 30 minutos

Vamos começar?
