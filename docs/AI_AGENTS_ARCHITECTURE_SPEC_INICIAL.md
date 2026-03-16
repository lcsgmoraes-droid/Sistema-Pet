# Sistema Pet - AI Agents Architecture (Spec Inicial)

Status: proposta inicial validada para implementacao incremental
Data: 2026-03-16
Escopo atual: Fase 1 - WhatsApp Sales Agent

---

## 1) Objetivo de Negocio

Transformar o Sistema Pet em um ERP com agentes de IA que:

- atendem clientes automaticamente
- ajudam a converter conversas em vendas
- melhoram cadastro de produtos
- reforcam consistencia financeira
- operam com seguranca e rastreabilidade

Regra estrutural: agentes nao acessam banco diretamente. Sempre usam APIs/tools internas.

---

## 2) Arquitetura Conceitual

Cliente (WhatsApp/App/Web)
-> AI Agent Layer
-> AI Tools (camada segura)
-> FastAPI (APIs internas)
-> Domain Events
-> ERP Core (DDD + multi-tenant)

Principios obrigatorios:

- multi-tenant por tenant_id em toda operacao
- autenticacao/autorizacao por JWT e permissoes
- logs e auditoria de decisoes de IA
- human-in-the-loop para acoes sensiveis
- fallback para operador humano

---

## 3) Estado Atual (Ja Existe no Projeto)

Base de WhatsApp e IA ja presente no backend:

- webhook WhatsApp: backend/app/whatsapp/webhook.py
- servico IA WhatsApp: backend/app/whatsapp/ai_service.py
- tools de conversa: backend/app/whatsapp/tools.py
- intencao, contexto, handoff, metricas: backend/app/whatsapp/*
- base de eventos/governanca IA: backend/app/ai_core/* e backend/app/ai/*

Observacao importante:

- ja existe estrutura madura para Fase 1
- parte das tools ainda esta com mock e precisa integrar no ERP real

---

## 4) Agentes Planejados

### 4.1 WhatsApp Sales Agent (Primeiro)

Responsabilidades:

- conversar com cliente
- entender texto
- interpretar audio e imagem (fases seguintes)
- buscar produto
- enviar foto do produto
- montar pedido e enviar para confirmacao operacional

Fluxo alvo:

1. Cliente envia mensagem
2. Webhook recebe evento
3. AI Service classifica intencao
4. Tool Executor consulta ERP
5. IA responde com opcoes
6. Cliente confirma
7. Tool cria pedido com origem whatsapp_ai
8. PDV mostra pedido pendente para operador confirmar

### 4.2 Catalog Health Agent

Responsabilidades:

- completar cadastro faltante
- sugerir categoria, descricao, imagem e NCM
- gerar score de saude do catalogo
- executar correcao por lotes com aprovacao humana

### 4.3 Financial Audit Agent

Responsabilidades:

- validar consistencia entre vendas, pagamentos, contas, caixa e DRE
- detectar divergencias
- sugerir ajustes com rastreio e auditoria

---

## 5) AI Tools (Contrato Minimo)

Todas as tools devem ser idempotentes quando aplicavel, auditaveis e tenant-safe.

Tools de leitura (fase 1):

- buscar_produto
- listar_produtos
- consultar_estoque
- buscar_cliente
- buscar_imagem_produto
- obter_info_loja

Tools de escrita (fase 1.5/2):

- criar_cliente
- criar_pedido
- adicionar_item_pedido
- registrar_intencao_compra

Regras de seguranca:

- tool nunca executa SQL direto no agente
- tool valida tenant_id, permissao e payload
- tool retorna erro sem stack sensivel

---

## 6) Modelo de Dados e Eventos

Campos recomendados para rastreio de IA em pedidos:

- origem = whatsapp_ai
- ai_session_id
- ai_confidence
- ai_summary
- status_operacional = pendente_confirmacao

Eventos de dominio recomendados:

- WhatsAppMessageReceived
- ProductSearchRequested
- CartIntentCaptured
- OrderDraftCreatedByAI
- OrderConfirmedByOperator
- AgentFallbackTriggered

---

## 7) Fase 1 - WhatsApp Agent (Escopo Executavel)

### 7.1 O que entra

- texto -> intencao -> resposta
- busca de produto real no ERP (sem mock)
- resposta com preco e disponibilidade
- handoff para humano quando necessario
- logs de conversa e metricas basicas

### 7.2 O que nao entra ainda

- fechamento automatico de pagamento
- acao financeira sem aprovacao
- alteracoes criticas sem operador

### 7.3 Critrios de aceite

- 95% das consultas de produto respondidas sem erro tecnico
- latencia media de resposta IA < 4s (sem audio/imagem)
- 0 incidente de vazamento cross-tenant
- handoff acionado em reclamacao/risco

---

## 8) Fases Futuras

### Fase 2

- audio (speech-to-text)
- imagem (vision)
- rascunho de pedido no PDV

### Fase 3

- envio de imagem automatica
- recomendacao de produto
- memoria de preferencia por cliente

### Fase 4

- Catalog Health Agent + painel de saude do catalogo

### Fase 5

- Financial Audit Agent + trilha de auditoria

---

## 9) Infra para Imagens

Recomendado: Cloudflare R2 (S3 compat)

Estrutura:

- /produtos/{produto_id}/principal.jpg
- /produtos/{produto_id}/galeria_*.jpg

Banco:

- produtos.imagem_url (principal)
- tabela auxiliar para galeria (opcional)

---

## 10) Backlog Tecnico Imediato (Proxima Sprint)

1. Remover mock das tools de produto e integrar com tabelas reais
2. Padronizar contrato de tool result (success/data/error_code)
3. Criar endpoint interno seguro para criar pedido rascunho por IA
4. Adicionar auditoria da decisao de IA por mensagem
5. Adicionar testes:
   - isolamento de tenant
   - permissao de tool
   - fallback/handoff
   - regressao de intents

---

## 11) Riscos e Mitigacao

Risco: IA responder com dado errado de produto
Mitigacao: tools com fonte unica no ERP e resposta com confirmacao explicita

Risco: acao indevida em tenant errado
Mitigacao: tenant_id obrigatorio em contexto e tools, testes de isolamento

Risco: custo de IA subir rapido
Mitigacao: limites por tenant, cache de consulta e fallback deterministico

Risco: automacao financeira indevida
Mitigacao: human-in-the-loop e bloqueio de acoes sensiveis

---

## 12) Definicao de Pronto (Fase 1)

- webhook recebendo e processando texto de forma estavel
- tools de produto reais (sem mock)
- resposta de IA com produtos e preco
- handoff funcional
- logs, metricas e testes minimos aprovados
- deploy seguindo fluxo unico DEV -> PROD
