---
tipo: funcionalidade
atualizado: 2026-09-12
---

# Entregas

Ver [[Funcionalidades]]. Fonte pré-existente: `docs/GUIA_RASTREAMENTO_ENTREGADOR_LOJAS.md`.

## Identificação

- **Menu:** Vendas e relacionamento → Entregas (submenu: Abertas, Rotas, Rastreamento, Histórico, Dashboard Financeiro)
- **Rota frontend:** `/entregas`, e rota pública `/rastreio/:token` (link de rastreamento enviado ao cliente final, sem login)
- **Módulo de rota:** `frontend/src/app/routes/SalesMarketingRoutes.jsx`
- **Módulo de plano (SaaS):** flag `entregas`

## Objetivo

Gestão de rotas de entrega, rastreamento (inclusive público via token), acerto financeiro com entregadores e configuração de custo por moto/km.

## Backend (confirmado)

`api/endpoints/rotas_entrega.py` (+ versão pública), `api/endpoints/acertos_entrega.py`, `api/endpoints/configuracoes_entrega.py`, `api/endpoints/configuracao_custo_moto.py`, `api/endpoints/dashboard_entregas.py`. Modelo: `rotas_entrega_models.py`.

## Integrações

Google Maps (geocodificação e cálculo de rota/distância) — ver [[Integracoes]], sem doc próprio dedicado.

## Segurança

Rota pública `/rastreio/:token` — acesso por token opaco, sem login; validação de segurança desse token específico não foi auditada a fundo nesta rodada. ❓ Necessita validação.

## Dependências

[[PDV-Vendas]] (origem do pedido a entregar), [[Cliente]] (papel de entregador, ver [[Cliente#Confirmado no código]]).

## Não identificado

- ❓ Validação de segurança do token de rastreamento público (força/entropia, expiração).
