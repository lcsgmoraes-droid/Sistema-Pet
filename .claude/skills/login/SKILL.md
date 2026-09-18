---
name: login
description: Use ao mexer na tela de login (/login), no fluxo de seleção de empresa (multiempresa) que acontece durante o login, ou nos links de recuperação de senha/criar conta que partem dela.
---

# Tela de Login

Fonte de verdade simplificada sobre `/login`. Complementa [[Autenticacao]] (segurança do fluxo) e [[RefatoracaoV2]] (histórico da migração visual desta tela para `components/v2/`).

## Identificação

- Menu: nenhum (rota pública, fora do layout autenticado)
- Rota frontend: `/login`
- Arquivo: `frontend/src/pages/v2/Login.jsx`
- Módulo de rota: `frontend/src/app/routes/PublicRoutes.jsx`
- Import lazy: `frontend/src/app/lazyPages.jsx`

## Objetivo

Autenticar um usuário (e-mail/senha ou usuário+loja/senha) e, se a conta tiver acesso a mais de uma empresa, deixá-lo escolher em qual empresa entrar — tudo numa única tela, sem navegação.

## Usuários

Qualquer visitante não autenticado. Não há verificação de permissão nesta tela (é o ponto de entrada). Depois de logado, o próprio backend decide a quais empresas o usuário tem acesso.

## Fluxo

```text
Usuário digita identificador + senha
  → submit → login() (AuthContext) → POST /auth/login-multitenant {identifier, password, tenant}
  → backend retorna access_token temporário + lista de tenants do usuário
     ├─ 1 empresa só → completeTenantSelection() automático (sem UI extra):
     │    POST /auth/select-tenant → GET /auth/me-multitenant → grava user/token → redireciona
     └─ mais de 1 empresa → tela troca para a lista "Escolha a empresa"
          → clique numa empresa → completeTenantSelection() → mesmo caminho acima
          → ou "Entrar com outra conta" → POST /auth/logout-multitenant → volta ao formulário
```

## Frontend

- Página: `frontend/src/pages/v2/Login.jsx`
- Lógica de sessão: `frontend/src/contexts/AuthContext.jsx` (`login`, `prepareTenantSelection`, `completeTenantSelection`, `selectTenant`, `cancelTenantSelection`)
- Redirecionamento pós-login: `getDefaultAuthenticatedRoute()` em `frontend/src/auth/userRole.js` — `caixa` → `/pdv`, admin/`gerente` → `/dashboard`, qualquer outro → `/lembretes`. Se não houver `user` salvo no `localStorage` por algum motivo, cai direto em `/lembretes`.
- Campos: `InputTexto` (identificador), `InputTexto` condicional (loja — só aparece se o identificador digitado **não** contém `@`, ver `loginComUsuario`), `InputSenha` (senha, mostrar/ocultar já embutido no componente). Botão de submit: `BotaoInteracao` (tamanho grande, ícone `PawPrint`) — não é `BotaoSalva` porque "Entrar" não grava nada, é ação.
- Validação client-side: só `required` nativo dos campos (sem regra de formato de e-mail no frontend — quem valida é o backend).

## Backend

- `POST /auth/login-multitenant` — `backend/app/auth/auth_multitenant_account_routes.py:297`. Recebe `identifier`, `password`, `tenant` (opcional). Retorna `access_token` temporário + lista de `tenants` do usuário.
- `POST /auth/select-tenant` — troca o token temporário por um token final vinculado à empresa escolhida.
- `GET /auth/me-multitenant` — busca os dados do usuário já autenticado na empresa selecionada.
- `POST /auth/logout-multitenant` — `backend/app/auth/auth_multitenant_session_routes.py:278`. Usado pelo "Entrar com outra conta" para encerrar a seleção de empresa em andamento.
- Rate limiting dedicado em `/auth/login-multitenant` — ver `backend/app/middlewares/rate_limit.py`. Ver [[Matriz-de-Riscos]] R02 (rate limiting in-memory, não escalável em múltiplos processos).

## Banco de dados

Ver [[Usuario]] e [[Tenant]] em [[Dominio]]. Esta tela não grava nada diretamente — só autentica e lê `usuário` + as empresas às quais ele está vinculado.

## APIs

Schemas em `backend/app/auth/auth_multitenant_schemas.py`.

| Endpoint | Quando é chamado | Payload | Resposta |
|---|---|---|---|
| `POST /auth/login-multitenant` | Ao submeter o formulário | `{identifier, password, tenant?}` (`LoginRequest`; `email` também aceito por compatibilidade, mas o frontend só envia `identifier`) | `{access_token, refresh_token, token_type, expires_in, user, tenants[], requires_email_verification, email_verification_sent}` (`LoginResponse`) — token aqui **não** tem `tenant_id` ainda |
| `POST /auth/select-tenant` | Ao escolher uma empresa (automático se só houver uma) — precisa do `access_token` temporário no header `Authorization` | `{tenant_id}` (`SelectTenantRequest`) | `{access_token, refresh_token, token_type, expires_in, tenant}` (`SelectTenantResponse`) — agora sim com `tenant_id` embutido |
| `GET /auth/me-multitenant` | Logo após `select-tenant`, para carregar os dados do usuário | — | Dados do usuário no contexto da empresa selecionada |
| `POST /auth/logout-multitenant` | Ao clicar "Entrar com outra conta" | `{}` (corpo vazio, token temporário no header) | — |

## Segurança

- Rota pública, sem `ProtectedRoute`.
- Rate limiting **por IP** no backend (ver acima) — ⚠️ ver [[Matriz-de-Riscos]] R02, não é confiável ainda com múltiplos processos.
- Bloqueio **por conta** já existe, independente do rate limiting por IP: `backend/app/services/auth_security.py` — após `AUTH_MAX_FAILED_LOGIN_ATTEMPTS` tentativas erradas (padrão **5**, configurável por env var), a conta fica bloqueada por `AUTH_LOGIN_LOCK_MINUTES` (padrão **15 minutos**, também configurável). A tela mostra a mensagem exata do backend ("Muitas tentativas de login. Aguarde N minuto(s)...") como `error`, sem tratamento especial — já funciona por já cair no fluxo genérico de erro.
- MFA não é verificado neste fluxo (ver [[Autenticacao]], R01) — se implementado no futuro, entra aqui.
- Token temporário (`getTempToken`/`setTempToken`/`clearTempToken`) existe só durante a janela entre login e seleção de empresa — não tem `tenant_id`, não é o token de sessão final (esse só sai de `/auth/select-tenant`).

## O que esta tela NÃO faz

- Não decide para onde o usuário vai depois de logado além do que `getDefaultAuthenticatedRoute()` calcula — não tem lógica de redirecionamento própria.
- Não valida força de senha nem formato de e-mail no frontend.
- Não lembra credenciais entre sessões (sem "lembrar-me").
- Não mostra a lista de empresas quando o usuário só tem uma — isso é decidido pelo `AuthContext`, não pela tela.

## Dependências

- [[Autenticacao]] — segurança do fluxo de auth como um todo.
- `frontend/src/pages/PlatformLogin.jsx` (`/ops/login`) — login **separado** da equipe CorePet, não relacionado a esta tela, não compartilha código.
- Telas vizinhas por link: `ForgotPassword.jsx` (`/recuperar-senha`), `Register.jsx` (`/register`), `EmailVerification.jsx` (`/verificar-email`, só quando o erro do login menciona confirmação de e-mail).

## Observações (comportamento não óbvio)

- O card de "Escolha a empresa" só aparece quando a conta tem **mais de uma** empresa — a maioria dos logins passa direto por ele sem o usuário perceber (seleção automática de tenant único).
- O campo "Loja" só aparece quando o identificador digitado não tem `@` (login por usuário, não e-mail) — é a pista de que o backend precisa saber em qual loja procurar esse nome de usuário, já que nomes de usuário não são globalmente únicos entre lojas.
- O link "Confirmar e-mail ou reenviar link" só aparece quando a mensagem de erro contém as palavras "email" **e** "confirm" ao mesmo tempo — é checagem de texto da mensagem de erro, não um código de erro estruturado.

## Pontos de atenção

- Ver [[RefatoracaoV2]] para o que foi mudado visualmente em 2026-09-12 (troca de inputs nativos por `InputTexto`/`InputSenha`/`BotaoSalva`) — nenhuma mudança de comportamento, só de componente.
- Cartões de seleção de empresa e o botão "Entrar com outra conta" ainda são JSX específico da tela (não viraram componente v2) — ver [[RefatoracaoV2]] para o raciocínio.

