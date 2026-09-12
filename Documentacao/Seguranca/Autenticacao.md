---
tipo: seguranca
atualizado: 2026-09-12
---

# Autenticação

Parte do eixo [[Seguranca]]. Ver também [[Autorizacao]], [[Vulnerabilidades]]. A tela de login do frontend (`/login`) tem sua própria skill (`.claude/skills/login/SKILL.md`), piloto da ideia de [[Fase-2-Funcionalidades-e-Skills]] item 2.3 — fonte de verdade sobre a tela em si (o que cada botão faz, fluxo, dependências), enquanto este documento cobre a segurança do fluxo de auth como um todo.

## Fluxo ativo (confirmado)

Rota real usada em produção: `auth_routes_multitenant.py` (registrada em `main_routers.py:263`) → delega para `backend/app/auth/auth_multitenant_account_routes.py` (registro/login), `auth_multitenant_session_routes.py` (seleção de tenant), `auth_multitenant_recovery_routes.py` (recuperação de senha).

Existe um segundo módulo, `backend/app/auth_routes.py` (single-tenant, legado), que **não está registrado em nenhum router ativo** — ver seção MFA abaixo.

## JWT (confirmado, `backend/app/auth/core.py`)

- Algoritmo: **HS256**.
- Access token: expira em **15 minutos** (`ACCESS_TOKEN_EXPIRE_MINUTES`, default 15, configurável por env).
- Refresh token: expira em **7 dias** (`REFRESH_TOKEN_EXPIRE_DAYS`, default 7).
- Cada token carrega um `jti` atrelado a uma linha em `UserSession` (`backend/app/session_manager.py:14-54`) — a sessão é validada a cada requisição (`validate_session()`, linhas 81-107), checando `revoked` e `expires_at` no banco, não apenas a assinatura/expiração do JWT.
- Revogação server-side real: `revoke_session` (logout) e `revoke_all_sessions` (troca de senha, reset de senha) — confirmado uso em `auth_multitenant_recovery_routes.py:205`. 🔵 Isso é mais seguro que JWT stateless puro, porque um token roubado pode ser invalidado antes de expirar.

## Bloqueio de conta por tentativas falhas (confirmado, ativo)

`backend/app/services/auth_security.py`:
- `MAX_FAILED_LOGIN_ATTEMPTS = 5` (env `AUTH_MAX_FAILED_LOGIN_ATTEMPTS`)
- `LOGIN_LOCK_MINUTES = 15`
- `register_failed_login` incrementa contador e trava a conta (`locked_until`) ao atingir o limite.
- `is_user_locked` é checado no login (`auth_multitenant_account_routes.py:340-345`) e retorna HTTP 429.

## MFA / 2FA — 🟠 existe no schema, não está ativo em nenhuma conta real

- Existe implementação TOTP (`pyotp`) com colunas `two_factor_enabled`/`two_factor_secret` em `models.py:115-117`.
- **Porém** essa verificação só existe no fluxo legado `backend/app/auth_routes.py:152-164`, que **não está registrado** em `main_routers.py` (confirmado por grep — apenas `auth_routes_multitenant` está incluído).
- O fluxo real (`login_multitenant`, usado por todo login do sistema) **não verifica 2FA**.
- Mesmo no código legado, os endpoints `/enable-2fa` e `/disable-2fa` nunca foram implementados — são apenas comentários `PLACEHOLDER` (`auth_routes.py:255-262`).

**🟠 Risco (Alto):** nenhuma conta do sistema tem 2FA funcional hoje, mesmo administradores. O campo no banco de dados pode passar falsa sensação de que a proteção existe.
**Recomendação:** implementar a verificação de 2FA no fluxo `auth_multitenant_account_routes.py` real, ou remover as colunas/expectativa até que seja implementado, para não haver ambiguidade no schema.

## Sign-up local sem verificação de e-mail (confirmado, comportamento intencional)

`_is_local_signup_request` (`backend/app/auth/auth_multitenant_support.py:41-47`) pula a exigência de verificação de e-mail (`EMAIL_VERIFICATION_REQUIRED`) quando o `Host` da requisição é `localhost`/`127.0.0.1`/`::1`/`0.0.0.0` — usado para permitir cadastro e teste local sem SMTP configurado. Isso está corretamente restrito a hosts locais e não altera o comportamento em produção (domínio real não bate com a whitelist).

## Não identificado

- ❓ Necessita validação: existe algum plano para reativar/implementar MFA de fato?
- ⚠️ Não identificado no código analisado: rate limit específico por conta (o bloqueio atual é por relação usuário+tentativas, não por IP — ver [[API-Security]] para o rate limit por IP, que é um mecanismo separado).
