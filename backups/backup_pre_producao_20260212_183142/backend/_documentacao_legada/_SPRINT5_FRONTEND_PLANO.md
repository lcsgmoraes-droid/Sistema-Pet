# 🎨 SPRINT 5 - FRONTEND HUMAN HANDOFF

**Objetivo:** Interface completa de atendimento humano via WhatsApp com chat em tempo real

---

## 📋 Escopo

### 1. Dashboard de Atendimento (8h)
**Rota:** `/whatsapp/atendimento`

**Layout:**
```
┌─────────────────────────────────────────────────────┐
│ Header: Pet Shop Pro - Atendimento WhatsApp         │
├──────────────┬──────────────────────────────────────┤
│              │                                       │
│  Sidebar     │  Main Content                        │
│  (Stats +    │  (Fila de Conversas ou Chat)        │
│   Agents)    │                                       │
│              │                                       │
├──────────────┴──────────────────────────────────────┤
│ Footer: Status do Agent + Configurações             │
└─────────────────────────────────────────────────────┘
```

**Componentes:**

**1.1 Header**
- Título + Logo
- Notificações (badge com total de pendentes)
- Status do usuário (Online/Offline/Busy)
- Sair

**1.2 Sidebar Esquerda**
```typescript
// Stats em tempo real
interface DashboardStats {
  pending_handoffs: number;
  active_conversations: number;
  agents_online: number;
  my_active_chats: number;
  avg_wait_time: number;
}

// Lista de agents
interface AgentStatus {
  id: string;
  name: string;
  status: 'online' | 'offline' | 'busy' | 'away';
  current_chats: number;
  max_chats: number;
}
```

**Cards:**
- Total pendentes (vermelho)
- Minhas conversas ativas (azul)
- Tempo médio de espera (amarelo)
- Agents online (verde)

**1.3 Fila de Conversas (Main)**
```typescript
interface ConversationItem {
  session_id: string;
  phone_number: string;
  customer_name?: string;
  last_message: string;
  last_message_at: Date;
  unread_count: number;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  sentiment_label?: string;
  sentiment_score?: number;
  handoff_reason?: string;
}
```

**Lista:**
- Card por conversa
- Badge de prioridade (cor por nível)
- Emoji de sentimento 😊😐😠
- Botão "Assumir"
- Filtros: Todas / Pendentes / Minhas
- Ordenação: Prioridade / Tempo

---

### 2. Chat Interface (12h)

**Rota:** `/whatsapp/atendimento/chat/:session_id`

**Layout:**
```
┌─────────────────────────────────────────────────────┐
│ Chat Header: Cliente Info + Actions                 │
├──────────────┬──────────────────────────────────────┤
│              │  Messages                             │
│  Cliente     │  ┌─────────────────┐                 │
│  Info        │  │ Cliente: Oi     │                 │
│  Sidebar     │  └─────────────────┘                 │
│              │  ┌─────────────────┐                 │
│  - Nome      │  │ Bot: Olá!       │                 │
│  - Telefone  │  └─────────────────┘                 │
│  - Pets      │  ┌─────────────────┐                 │
│  - Histórico │  │ Você: Como pos..│                 │
│  - Notas     │  └─────────────────┘                 │
│              │                                       │
├──────────────┴──────────────────────────────────────┤
│ Input: [Mensagem...] [Enviar] [Bot Assist] [+]     │
└─────────────────────────────────────────────────────┘
```

**Componentes:**

**2.1 Chat Header**
- Nome do cliente + telefone
- Status (ativo/resolvido)
- Tempo de conversa
- Actions:
  - 🔔 Notificar outro agent
  - ✅ Resolver conversa
  - 🤖 Reativar bot
  - ⚙️ Configurações

**2.2 Sidebar Direita - Cliente Info**
```typescript
interface CustomerInfo {
  name: string;
  phone: string;
  email?: string;
  pets: Pet[];
  last_purchase?: Purchase;
  total_spent: number;
  sentiment_history: SentimentPoint[];
}
```

**Abas:**
- 📋 Info: Dados básicos
- 🐕 Pets: Lista de pets
- 📦 Pedidos: Histórico
- 📝 Notas: Notas internas

**2.3 Messages Area**
- Scroll infinito (load more)
- Bubbles diferenciadas:
  - Cliente (esquerda, cinza)
  - Bot (esquerda, azul claro)
  - Atendente (direita, azul)
  - Sistema (centro, amarelo)
- Timestamp
- Status de leitura (✓ ✓✓)
- Typing indicator "..." quando cliente está digitando

**2.4 Input Area**
- Textarea com auto-resize
- Botões:
  - 📎 Anexar arquivo
  - 😊 Emojis
  - 🤖 Bot Assist (sugestões)
  - ⚡ Quick Replies
- Shortcut: Enter para enviar, Shift+Enter para quebra de linha

**2.5 Bot Assist Panel (collapsible)**
```typescript
interface BotSuggestion {
  type: 'quick_reply' | 'customer_info' | 'product_info';
  title: string;
  content: string;
  action?: string;
}
```

**Sugestões:**
- Respostas rápidas baseadas no contexto
- Dados do cliente (última compra, pets)
- Produtos relacionados
- FAQs

---

### 3. WebSocket Integration (8h)

**Protocolo:** Socket.IO

**Events:**

**Client → Server:**
```typescript
// Conexão
socket.emit('agent:connect', { agent_id, token });

// Assumir conversa
socket.emit('conversation:take', { session_id });

// Enviar mensagem
socket.emit('message:send', { session_id, message });

// Typing
socket.emit('typing:start', { session_id });
socket.emit('typing:stop', { session_id });

// Resolver
socket.emit('conversation:resolve', { session_id, notes });
```

**Server → Client:**
```typescript
// Nova conversa na fila
socket.on('handoff:new', (data: Handoff));

// Nova mensagem do cliente
socket.on('message:new', (data: Message));

// Cliente digitando
socket.on('customer:typing', (data: { session_id }));

// Conversa assumida por outro
socket.on('conversation:taken', (data: { session_id, agent_name }));

// Conversa resolvida
socket.on('conversation:resolved', (data: { session_id }));

// Agent status change
socket.on('agent:status', (data: { agent_id, status }));
```

---

### 4. Estado Global (Zustand) (4h)

```typescript
// stores/whatsappStore.ts
interface WhatsAppStore {
  // Stats
  stats: DashboardStats;
  
  // Agents
  agents: AgentStatus[];
  currentAgent: AgentStatus | null;
  
  // Conversas
  conversations: ConversationItem[];
  activeConversation: ConversationItem | null;
  
  // Messages
  messages: Record<string, Message[]>;
  
  // UI State
  isConnected: boolean;
  isSidebarOpen: boolean;
  isBotAssistOpen: boolean;
  
  // Actions
  fetchStats: () => Promise<void>;
  fetchAgents: () => Promise<void>;
  fetchConversations: () => Promise<void>;
  takeConversation: (session_id: string) => Promise<void>;
  sendMessage: (session_id: string, message: string) => Promise<void>;
  resolveConversation: (session_id: string, notes: string) => Promise<void>;
  updateAgentStatus: (status: string) => Promise<void>;
}
```

---

### 5. Components Structure

```
frontend/src/pages/WhatsApp/
├── Atendimento/
│   ├── index.tsx                 # Main dashboard
│   ├── components/
│   │   ├── Header.tsx
│   │   ├── Sidebar.tsx
│   │   │   ├── StatsCard.tsx
│   │   │   └── AgentsList.tsx
│   │   ├── ConversationsList.tsx
│   │   │   └── ConversationCard.tsx
│   │   └── Filters.tsx
│   └── hooks/
│       ├── useWebSocket.ts
│       └── useNotifications.ts
│
├── Chat/
│   ├── index.tsx                 # Chat interface
│   ├── components/
│   │   ├── ChatHeader.tsx
│   │   ├── MessagesArea.tsx
│   │   │   ├── MessageBubble.tsx
│   │   │   ├── TypingIndicator.tsx
│   │   │   └── SystemMessage.tsx
│   │   ├── InputArea.tsx
│   │   │   ├── MessageInput.tsx
│   │   │   ├── AttachButton.tsx
│   │   │   └── EmojiPicker.tsx
│   │   ├── CustomerSidebar.tsx
│   │   │   ├── InfoTab.tsx
│   │   │   ├── PetsTab.tsx
│   │   │   ├── OrdersTab.tsx
│   │   │   └── NotesTab.tsx
│   │   └── BotAssist.tsx
│   │       ├── SuggestionCard.tsx
│   │       └── QuickReplies.tsx
│   └── hooks/
│       ├── useMessages.ts
│       ├── useCustomerInfo.ts
│       └── useBotAssist.ts
│
└── shared/
    ├── components/
    │   ├── PriorityBadge.tsx
    │   ├── SentimentEmoji.tsx
    │   └── StatusIndicator.tsx
    └── utils/
        ├── formatters.ts
        └── constants.ts
```

---

### 6. API Integration (4h)

**Services:**

```typescript
// services/whatsappService.ts
class WhatsAppService {
  // Agents
  getAgents(): Promise<AgentResponse[]>
  createAgent(data: AgentCreate): Promise<AgentResponse>
  updateAgent(id: string, data: AgentUpdate): Promise<AgentResponse>
  
  // Handoffs
  getHandoffs(filters?: HandoffFilters): Promise<HandoffResponse[]>
  assignHandoff(id: string, agent_id: string): Promise<HandoffResponse>
  resolveHandoff(id: string, notes: string): Promise<HandoffResponse>
  
  // Messages
  getMessages(session_id: string): Promise<Message[]>
  sendMessage(session_id: string, message: string): Promise<Message>
  
  // Notes
  getNotes(handoff_id: string): Promise<Note[]>
  createNote(handoff_id: string, content: string): Promise<Note>
  
  // Stats
  getStats(): Promise<DashboardStats>
  
  // Sentiment
  testSentiment(message: string): Promise<SentimentResult>
}
```

---

### 7. Notifications (2h)

**Browser Notifications:**
```typescript
// Nova conversa
notify({
  title: "Nova conversa",
  body: "Cliente aguardando atendimento",
  icon: "/logo.png",
  tag: session_id,
  onClick: () => navigate(`/whatsapp/chat/${session_id}`)
});

// Mensagem urgente
notify({
  title: "🔥 URGENTE",
  body: "Cliente muito insatisfeito",
  urgency: 'high'
});
```

**Sound Alerts:**
- Nova conversa: ding.mp3
- Nova mensagem: pop.mp3
- Urgente: alarm.mp3

---

### 8. Responsividade (2h)

**Breakpoints:**
- Desktop: >= 1024px (layout completo)
- Tablet: 768px - 1023px (sidebar collapsible)
- Mobile: < 768px (chat fullscreen, sidebar overlay)

---

## 🎨 Design System

### Cores
```css
--priority-low: #10b981;      /* Verde */
--priority-medium: #f59e0b;   /* Amarelo */
--priority-high: #f97316;     /* Laranja */
--priority-urgent: #ef4444;   /* Vermelho */

--sentiment-positive: #10b981;
--sentiment-neutral: #6b7280;
--sentiment-negative: #ef4444;

--agent-online: #10b981;
--agent-busy: #f59e0b;
--agent-away: #f97316;
--agent-offline: #6b7280;
```

### Icons (Lucide React)
- MessageSquare, Send, User, Phone
- Clock, AlertCircle, CheckCircle
- Bot, Users, Bell, Settings

---

## 📦 Dependências Novas

```json
{
  "socket.io-client": "^4.7.0",
  "@emoji-mart/react": "^1.1.0",
  "react-window": "^1.8.10",
  "date-fns": "^3.0.0",
  "zustand": "^4.5.0"
}
```

---

## 🧪 Testes

### Unit Tests
- [ ] Component rendering
- [ ] WebSocket events
- [ ] State management
- [ ] API service calls

### Integration Tests
- [ ] Fluxo completo: assumir → enviar → resolver
- [ ] WebSocket reconnection
- [ ] Notificações

---

## 📊 Estimativa de Tempo

| Tarefa | Horas |
|--------|-------|
| Dashboard layout | 8h |
| Chat interface | 12h |
| WebSocket integration | 8h |
| Estado global | 4h |
| API services | 4h |
| Notifications | 2h |
| Responsividade | 2h |
| **TOTAL** | **40h** |

**Duração:** ~1 semana (5 dias úteis)

---

## 🚀 Ordem de Implementação

### Dia 1-2: Base
1. Estado global (Zustand)
2. API services
3. Dashboard layout básico

### Dia 3: Chat
4. Chat interface
5. Messages area
6. Input area

### Dia 4: Real-time
7. WebSocket integration
8. Notifications
9. Typing indicators

### Dia 5: Polish
10. Bot Assist
11. Customer sidebar
12. Responsividade
13. Testes

---

## ✅ Critérios de Aceitação

- [ ] Dashboard mostra conversas em tempo real
- [ ] Agent pode assumir conversa
- [ ] Chat funciona bidirecional
- [ ] WebSocket notifica novas mensagens
- [ ] Bot Assist sugere respostas
- [ ] Customer info carrega dados reais
- [ ] Resolve conversa com notas
- [ ] Notificações browser funcionam
- [ ] Responsivo em mobile
- [ ] Performance < 1s para ações

---

**Pronto para começar!** 🚀

Quer que eu comece implementando o Dashboard ou prefere começar por outro componente?
