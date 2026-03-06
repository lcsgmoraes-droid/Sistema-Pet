# Plano de Implementação — Sistema de Campanhas, Fase 1

> Atualizado: Março 2026  
> Status: Em andamento — Sprint 1 concluída

---

## Resumo do que foi criado nesta sessão (Sprint 1)

### Migration Alembic
**Arquivo:** `backend/alembic/versions/c1d2e3f4a5b6_create_campaign_engine_tables.py`  
Cria as 14 tabelas do motor + 12 ENUMs do PostgreSQL.

### Estrutura de pastas do Campaign Engine
```
backend/app/campaigns/
├── __init__.py         ✅ criado
├── models.py           ✅ criado — SQLAlchemy para as 14 tabelas
├── engine.py           ✅ criado — CampaignEngine (avaliar + executar)
├── worker.py           ✅ criado — CampaignWorker (SKIP LOCKED)
├── scheduler.py        ✅ criado — APScheduler jobs
├── routes.py           ✅ criado — FastAPI router (stub)
└── handlers/
    ├── __init__.py     ✅ criado — registry de handlers
    ├── birthday.py     ✅ stub (TODO Sprint 2)
    ├── welcome.py      ✅ stub (TODO Sprint 2)
    ├── inactivity.py   ✅ stub (TODO Sprint 3)
    ├── loyalty.py      ✅ stub (TODO Fase 2)
    ├── cashback.py     ✅ stub (TODO Fase 2)
    └── ranking.py      ✅ stub (TODO Fase 2)
```

---

## Plano completo — Fase 1

### Sprint 1 — Base do motor ✅ CONCLUÍDA

| # | Tarefa | Arquivo | Status |
|---|--------|---------|--------|
| 1.1 | Migration Alembic (14 tabelas) | `alembic/versions/c1d2e3f4...` | ✅ |
| 1.2 | Modelos SQLAlchemy | `campaigns/models.py` | ✅ |
| 1.3 | CampaignEngine (avaliar/executar) | `campaigns/engine.py` | ✅ |
| 1.4 | CampaignWorker (fila SKIP LOCKED) | `campaigns/worker.py` | ✅ |
| 1.5 | CampaignScheduler (APScheduler jobs) | `campaigns/scheduler.py` | ✅ |
| 1.6 | Stubs de handlers | `campaigns/handlers/` | ✅ |
| 1.7 | Router FastAPI (healthcheck) | `campaigns/routes.py` | ✅ |

**Próximo passo concreto antes de prosseguir:**
1. Rodar a migration no ambiente local (`alembic upgrade head`)
2. Registrar o scheduler e o router no `main.py`
3. Confirmar que os containers DEV sobem sem erros

---

### Sprint 2 — Primeiras campanhas funcionando

| # | Tarefa | Handler | Prioridade |
|---|--------|---------|-----------|
| 2.1 | Implementar `BirthdayHandler` | `handlers/birthday.py` | Alta |
| 2.2 | Implementar `WelcomeHandler` | `handlers/welcome.py` | Alta |
| 2.3 | Lógica de geração de cupom (serviço utilitário) | `campaigns/coupon_service.py` | Alta |
| 2.4 | Lógica de enfileiramento de notificação | `campaigns/notification_service.py` | Alta |
| 2.5 | Endpoint para listar cupons do cliente | `campaigns/routes.py` | Média |
| 2.6 | Testar fluxo ponta-a-ponta em DEV | — | Alta |

---

### Sprint 3 — Campanhas de retenção

| # | Tarefa | Handler | Prioridade |
|---|--------|---------|-----------|
| 3.1 | Implementar `InactivityHandler` | `handlers/inactivity.py` | Alta |
| 3.2 | Endpoint CRUD para campanhas (criar/pausar/editar) | `campaigns/routes.py` | Alta |
| 3.3 | Tela frontend — Campanhas (sidebar + layout) | `frontend/src/pages/Campanhas` | Alta |
| 3.4 | Tela frontend — Lista de cupons | frontend | Média |

---

### Sprint 4 — Interface completa (frontend)

| # | Tarefa |
|---|--------|
| 4.1 | Sidebar "Campanhas" no frontend |
| 4.2 | Tela Visão Geral (cupons emitidos/utilizados/expirados hoje) |
| 4.3 | Tela Campanhas Sazonais (aniversário cliente + pet) |
| 4.4 | Tela Boas-vindas (app + ecommerce) |
| 4.5 | Tela Retenção (lista dinâmica com botão +) |
| 4.6 | Dashboard básico: taxa de retorno de cupons |

---

## Decisões já tomadas (não reabrir)

- **Fila:** PostgreSQL SKIP LOCKED (sem Redis na Fase 1)
- **Scheduler:** APScheduler embutido no FastAPI
- **Idempotência:** UNIQUE(tenant_id, campaign_id, customer_id, reference_period)
- **Proteção storm:** event_depth > 1 descartado + allowlist CAMPAIGN_TRIGGER_EVENTS
- **Ledger cashback:** append-only, saldo = SUM(amount)
- **Todos os índices:** compostos com tenant_id na primeira posição

---

## Como rodar a migration localmente

```bash
# Na pasta backend:
alembic upgrade head
```

Ou via Docker (quando o ambiente DEV estiver rodando):
```bash
docker exec petshop-dev-backend alembic upgrade head
```

---

## Regras de operação

- **Nunca subir para produção sem autorização do Lucas.**
- Cada sprint deve ser testada em DEV antes de qualquer push.
- Mudanças de parâmetros de campanha → só editar a tabela `campaigns`, não o código.
