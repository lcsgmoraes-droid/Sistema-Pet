---
tipo: seguranca
atualizado: 2026-09-12
---

# Autorização

Parte do eixo [[Seguranca]]. Ver [[Autenticacao]], [[Banco-de-Dados#Multi-tenancy e isolamento]], [[Role-Permission]].

## Modelo RBAC por tenant (confirmado)

`Role`, `Permission`, `RolePermission`, `UserTenant` em `backend/app/models_authz.py`. `RolePermission` é **tenant-scoped** — cada empresa tem seu próprio conjunto de vínculos papel→permissão, não um catálogo global compartilhado. Perfis padrão de um tenant novo (`docs/PERFIS_ACESSO_PADRAO.md`, confirmado): `Administrador` (acesso total), `Gerente`, `Financeiro`, `Estoque e Compras`, `Caixa`, `Cliente` (sem painel administrativo). Apenas `Administrador` recebe automaticamente todas as permissões; uma permissão nova do sistema **não** entra automaticamente nos perfis existentes.

## Verificação por rota (confirmado)

`check_permission()` (`backend/app/security/permissions_service.py:27-58`) consulta `Permission JOIN RolePermission JOIN UserTenant` filtrando explicitamente por `tenant_id`. Aplicado via decorators `require_permission`/`require_any_permission` (`backend/app/security/permissions_decorator.py`). É checagem por **permissão explícita**, não apenas "usuário autenticado".

## Isolamento entre empresas — proteção contra BOLA/IDOR (confirmado, ponto mais forte do sistema)

1. `tenant_id` vem do **JWT**, validado contra `UserTenant` ativo no momento de `/auth/select-tenant` (`auth_multitenant_session_routes.py:133-160`) antes de ser emitido no token — um usuário não pode simplesmente enviar um `tenant_id` arbitrário.
2. Filtro global automático com **fail-fast**: `backend/app/tenancy/filters.py` injeta `WHERE tenant_id = ?` em toda query de modelo multiempresa e **lança erro** se não houver tenant no contexto — detalhado em [[Banco-de-Dados]].
3. Camada adicional de Row Level Security no Postgres, sincronizada em paralelo (defesa em profundidade, não apenas decorativa).
4. Casos de compartilhamento deliberado entre tenants parceiros (veterinário parceiro, grupos de empresas) usam subqueries explícitas e documentadas, não um bypass geral.

**Avaliação de risco:** 🔵 Este é o controle de segurança mais maduro identificado no sistema — duas camadas independentes, uma delas fail-closed por padrão. A ressalva (🟡) é que a proteção depende de todo código de rota usar corretamente `get_current_user_and_tenant`/`set_current_tenant`; nenhuma rota de negócio comum encontrada faz bypass deliberado, mas uma auditoria exaustiva de 100% das ~90 rotas está fora do escopo desta análise. ❓ Necessita amostragem adicional se houver auditoria formal futura.

## Autorização no frontend vs. backend (confirmado — ver [[Funcionalidades]])

- Frontend: `ProtectedRoute.jsx` (guard de rota) e filtro de itens de menu em `Layout.jsx`, ambos client-side, apenas para experiência de uso (esconder o que o usuário não pode acessar).
- Backend é a autoridade real: toda permissão é revalidada nas rotas via `require_permission`. O frontend nunca é a única barreira — confirmado pela arquitetura (`docs/ARQUITETURA.md`: "regra de negócio financeira, fiscal ou de estoque não deve existir apenas no frontend").

## Rotas administrativas globais (plataforma)

`/ops/*` (backoffice interno) usa um guard e contexto de autenticação **separado** do multiempresa (`PlatformAuthContext`, `platform_auth.py`) — não é um tenant, é staff da própria CorePet. Documentado como exceção explícita em `docs/ARQUITETURA.md`.

## Não identificado

- ⚠️ Não identificado no código analisado: se existe alguma rota que construa SQL bruto (`session.execute(text(...))`) fora do ORM, o que contornaria o filtro automático de tenant. Não foi feita varredura exaustiva desse padrão em todo o repositório. ❓ Necessita validação.
