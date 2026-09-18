---
tipo: funcionalidade
atualizado: 2026-09-12
---

# Campanhas

Ver [[Funcionalidades]], [[Cliente]]. Fonte pré-existente: `docs/CAMPANHAS_IDEIAS.md`, `docs/CAMPANHAS_ROADMAP.md`, `docs/PLANO_CAMPANHAS_FASE1.md`.

## Identificação

- **Menu:** Vendas e relacionamento → Campanhas (submenu: Estúdio de Ofertas)
- **Rota frontend:** `/campanhas`
- **Módulo de rota:** `frontend/src/app/routes/SalesMarketingRoutes.jsx`
- **Módulo de plano (SaaS):** flag `campanhas`

## Objetivo

Motor de campanhas de marketing/fidelidade: cupons, sorteios, ranking de clientes, fidelidade por pontos/carimbos.

## Backend (confirmado — ~28 arquivos em `campaigns/`)

`campaigns/routes.py`, `campaigns/engine.py` (motor de regras), cupons, sorteios, ranking; `campaigns/scheduler.py` (`CampaignScheduler`, APScheduler); fila própria (`campaign_event_queue`, tabela Postgres com `SELECT FOR UPDATE SKIP LOCKED` — ver [[Arquitetura]]).

## Testes de risco já mapeados pelo projeto

`backend/tests/domain/test_coupon_service.py`, `test_loyalty_service.py`, `test_campaign_coupon_rules.py`, `test_campaigns_routes_cupom_anulacao.py` (`docs/auditorias/testes-ci-cobertura-critica.md`) — risco principal identificado pelo próprio time: "cupom/carimbo duplicado, não consumido ou não revertido".

## Dependências

[[Cliente]] (destinatário), [[PDV-Vendas]] (aplicação de cupom/consumo de fidelidade), [[WhatsApp-WAHA]] (potencial canal de disparo).

## Não identificado

- ⚠️ Contrato detalhado do "Estúdio de Ofertas" (`ofertas_estudio_routes.py`) não foi aprofundado nesta rodada.
