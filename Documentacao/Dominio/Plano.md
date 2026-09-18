---
tipo: dominio
atualizado: 2026-09-13
---

# Entidade — Plano / Assinatura

Ver [[Tenant]], [[Modulo]], [[Asaas]].

## Definição
Não existe um modelo `Subscription`/`Assinatura` central: o "plano contratado" e o "estado da assinatura" são campos do próprio [[Tenant]], mais um catálogo estático de planos públicos. O estado efetivo (ex.: se o trial já venceu) é **calculado sob demanda**, não persistido automaticamente.

## Confirmado no código
- Campos em `Tenant` (`backend/app/models.py:569-702`): `plan` (default `"free"`), `billing_status` (default `"active"`; valores válidos: `trial, pending, active, past_due, expired, blocked, refunded, canceled` — `backend/app/routes/modulos_routes.py:67-78`), `trial_started_at`/`trial_ends_at`, `subscription_activated_at`, `subscription_source` (`manual` ou `asaas`), mais os campos de billing do Asaas (`billing_provider_customer_id`, `billing_payment_status`, `billing_next_due_date`, `billing_checkout_url`, etc. — `models.py:616-623`).
- Catálogo de planos: `backend/app/services/plan_catalog.py`. `PlanDefinition` (dataclass congelada, linhas 13-37) com `code, name, segment, price_cents, organization_types, modules, entitlements, monthly_sales_limit, simultaneous_sessions_limit`. `PLAN_CATALOG` (linhas 44-223) define 10 planos em 3 segmentos: `pet` (petshop — `pet-start`, `pet-basico`, `pet-gestao`, `pet-venda-ativa`), `vet` (`vet-start`, `vet-gestao`, `vet-completo`), `grooming` (`grooming-start`, `grooming-gestao`, `grooming-completo`).
- `resolve_signup_selection(plan_code, organization_type)` (`plan_catalog.py:263-277`) valida no cadastro que o plano escolhido pertence ao tipo de organização informado.
- Estado efetivo calculado sob demanda: `_assinatura_resumo_tenant(tenant, agora)` (`backend/app/routes/modulos_routes.py:115-166`) deriva `status_efetivo` (rebaixa `trial` → `expired` quando `trial_ends_at` já passou), `dias_restantes_trial` e `acesso_completo_durante_trial`. Chamado em `GET /modulos/status` e nos dois gates de `security/module_access.py` — ver [[Modulo]].
- ⚠️ O rebaixamento de `billing_status` de `"trial"` para `"expired"` **nunca é persistido automaticamente no banco** — só é calculado em memória por `_assinatura_resumo_tenant()`. Qualquer código que leia `tenant.billing_status` diretamente, sem passar por essa função, pode achar que o tenant ainda está em `"trial"` dias depois do vencimento. A verdade sobre "o trial ainda vale?" está no cálculo, não na coluna.
- Trial concedido no signup (`backend/app/auth/auth_multitenant_account_routes.py:108-145`): cria `Tenant` com `billing_status="trial"`, `trial_started_at=agora`, `trial_ends_at=agora+30 dias` (`DEFAULT_TRIAL_DAYS=30`, `backend/app/auth/auth_multitenant_support.py:30`; duplicado como `TRIAL_DIAS_PADRAO` em `modulos_routes.py:66` — mesmo valor hoje, mas são duas constantes separadas).
- Durante o trial, o acesso é total e não gradual: comentário explícito no código (`modulos_routes.py:140`) — "Os 30 dias completos continuam mesmo se o cliente pagar antes do fim." Ver detalhes de liberação de módulos em [[Modulo]].
- Sem job/cron de expiração: nenhum scheduler do sistema (`catalogo_mestre_scheduler.py`, `bling_sync_scheduler.py`, `acerto_scheduler.py`, `campaigns/scheduler.py`) trata trial/billing. A escrita física de `billing_status` só acontece via (a) webhook do Asaas (`asaas_billing_service.py:456-471`) ou (b) ativação manual por superadmin.
- Bloqueio real de operação (não é bloqueio de login): `backend/app/services/plan_limits.py`. `enforce_monthly_sales_limit()` (linhas 52-106, chamado em `vendas/service.py:54`) recusa nova venda com `402 subscription_inactive` se o trial já venceu e a assinatura não está ativa; se passar, aplica o `monthly_sales_limit` numérico do plano. `enforce_simultaneous_session_limit()` (linhas 122-161, chamado em `auth_multitenant_session_routes.py:186`) derruba a sessão mais antiga quando o plano limita sessões simultâneas — ver [[UserTenant]].
- Regra notável do webhook Asaas: falha de pagamento só rebaixa `billing_status` se o trial **não** estiver mais ativo (`asaas_billing_service.py:462-469`) — atraso de pagamento não corta acesso durante o trial.
- Endpoints administrativos de ativação manual (bypassam Asaas): `POST /modulos/admin/plano/ativar` e `/modulos/admin/plano-basico/ativar` (`modulos_routes.py:436-533`), restritos a `is_superadmin`/`is_system_admin`.
- `BillingOffer` (`backend/app/billing_models.py:99`) — ofertas de billing customizadas fora do catálogo público, com `provider_subscription_id`, `status`, `revoked`. Ver [[Asaas]] para o fluxo completo de billing/webhook.

## Utilizado por
- [[Modulo]] — o `plan` define o conjunto padrão de módulos/entitlements liberados.
- [[Asaas]] — gateway que ativa/rebaixa `billing_status` via webhook.
- Registro de nova conta (`auth_multitenant_account_routes.py`) — concessão do trial inicial.

## Não identificado
- ❓ Não há tabela de histórico de mudança de plano (upgrade/downgrade) — só o log de auditoria genérico (`business_audit_service.py`), não uma tabela dedicada de histórico de assinatura.
- ❓ `TRIAL_DIAS_PADRAO`/`DEFAULT_TRIAL_DAYS` duplicados em dois arquivos em vez de uma única fonte — risco de divergência futura caso só um seja alterado.
- ❓ Não encontrado aviso automático (e-mail/notificação) de trial perto do fim — só o campo calculado `dias_restantes_trial` exposto pela API.
