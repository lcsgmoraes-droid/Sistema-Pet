---
tipo: dominio
atualizado: 2026-09-13
---

# Entidade — Módulo (licenciamento por módulo)

Ver [[Plano]], [[Tenant]], [[Arquitetura]].

## Definição
Um "módulo" é uma área funcional premium (ex.: financeiro avançado, WhatsApp, e-commerce) que pode estar ativa ou não para um tenant, de forma independente do resto do sistema. É a unidade real de gate tanto no backend (rota) quanto no frontend (menu).

## Confirmado no código
- Lista canônica: `MODULOS_PREMIUM` (frozenset de 16 itens, `backend/app/routes/modulos_routes.py:34-53`): `app_mobile, banho_tosa, bling, campanhas, comissoes, compras, ecommerce, entregas, financeiro_erp, fiscal, ia_avancada, integracoes, marketplaces, rh, veterinario, whatsapp`. Espelhada no frontend em `frontend/src/contexts/ModulosContext.jsx:18` (mesma lista) e `:42` (`MODULOS_INFO`, com preços/descrições para a vitrine).
- `MODULOS_FORA_DA_OFERTA_PUBLICA = {"bling"}` (`modulos_routes.py:57`) — Bling é uso interno/parceiro, não vendido. `MODULOS_TRIAL_COMPLETO = MODULOS_PREMIUM - {"bling"}` (linha 59) — é o conjunto liberado durante o trial gratuito.
- Tabela dedicada de módulo contratado avulso, fora do plano base: `AssinaturaModulo` (`backend/app/models.py:705-727`, tabela `assinaturas_modulos`, herda `TenantScoped`) — `modulo`, `status` (`ativo|cancelado|expirado`), `valor_mensal`, `data_inicio`/`data_fim`, `payment_id`, `gateway` (`mercadopago|pagarme|manual`). Permite comprar um módulo avulso mesmo fora do que o [[Plano]] contratado normalmente entrega.
- Resolução de "quais módulos estão ativos agora" — `_resolver_modulos_ativos()` (`modulos_routes.py:198-228`), combina em ordem: (1) `tenant.modulos_ativos` (JSON legado/liberação manual direta no Tenant), (2) `AssinaturaModulo` com `status="ativo"` e `data_fim` válida, (3) todos os `MODULOS_PREMIUM` se `plan` for um plano legado/enterprise (`PLANOS_LEGADO_LIBERADOS`/`PLANOS_TODOS_MODULOS`), (4) módulos do `PlanDefinition.modules` do catálogo, só se a assinatura estiver `active`/`trial`, (5) `MODULOS_TRIAL_COMPLETO` inteiro se o trial gratuito ainda está ativo, **independente do plano escolhido**.
- Endpoint consumido pelo frontend: `GET /modulos/status` (`modulos_routes.py:231-340`, chamado em `ModulosContext.jsx:253`) — retorna módulos ativos, plano, resumo de assinatura, entitlements e limites de uso.
- Gate real de rota no backend (não é só cosmético no frontend): `backend/app/security/module_access.py`. `require_active_module(modulo)` (linhas 110-164) é a dependency FastAPI usada de verdade; dá bypass só a `is_superadmin`/`is_system_admin` — comentário explícito no código (linha 139-140): admin comum do tenant **não** tem bypass, o plano manda. Sem o módulo ativo → `403 module_not_enabled`. `require_active_entitlement(entitlement)` (linhas 167-208) é o gate mais fino, por feature específica do catálogo.
- Aplicado via `_module_dependencies(modulo)` (`backend/app/main_routers.py:239-246`), injetado em dezenas de `app.include_router(...)`: `financeiro_erp`, `entregas`, `whatsapp`, `ecommerce`, `campanhas`, `veterinario`, `banho_tosa`, `bling`, `rh`, `compras`, `comissoes`, `integracoes`, `fiscal` — ver [[Arquitetura#Módulos ligáveis por tenant]].
- Ativação manual de módulo avulso: `POST /modulos/admin/ativar` (`modulos_routes.py:343-433`, só superadmin/system_admin) — grava tanto em `tenant.modulos_ativos` quanto cria linha `AssinaturaModulo` (`gateway="manual"`).

## Utilizado por
- Menu e rotas do frontend (`ModulosContext.jsx`) — esconde itens de menu de módulos não contratados.
- Toda rota backend das áreas listadas acima, via `require_active_module`/`require_active_entitlement`.
- [[Plano]] — o plano contratado é uma das 5 fontes que alimentam a resolução de módulos ativos.

## Não identificado
- ❓ Não encontrado endpoint de cancelamento self-service de módulo avulso (`AssinaturaModulo.status="cancelado"`) — só ativação manual por superadmin foi confirmada nas rotas lidas.
