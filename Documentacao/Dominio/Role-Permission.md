---
tipo: dominio
atualizado: 2026-09-12
---

# Entidade — Role / Permission (RBAC)

Ver [[Autorizacao]], [[Usuario]], [[Tenant]].

## Confirmado no código
- Modelo: `backend/app/models_authz.py` — `Role`, `Permission`, `RolePermission`, `UserTenant`.
- `Role` é **por tenant** (cada empresa tem seus próprios papéis, mesmo que criados a partir do mesmo template inicial).
- `Permission` é **global** (catálogo único de permissões do sistema).
- `RolePermission` liga `Role → Permission`, também tenant-scoped.
- `UserTenant` é o vínculo N:N real: `User ↔ Tenant ↔ Role`.
- Verificação em runtime: `check_permission()` (`security/permissions_service.py`), aplicada via `require_permission`/`require_any_permission`.

## Perfis padrão de um tenant novo (confirmado, `docs/PERFIS_ACESSO_PADRAO.md`)
| Perfil | Acesso |
|---|---|
| Administrador | Total — única role que recebe automaticamente **todas** as permissões |
| Gerente | Operação e relatórios, sem administrar usuários/dados centrais |
| Financeiro | Bancos, contas, conciliação, DRE, fluxo de caixa |
| Estoque e Compras | Produtos, entrada de XML, pedidos de compra (sem excluir produtos) |
| Caixa | PDV, consulta de produtos, cadastro/edição de clientes (sem excluir vendas/clientes/produtos) |
| Cliente | Sem painel administrativo — reservado para contas do app/e-commerce |

Regra importante confirmada: uma **permissão nova** adicionada ao sistema **não** entra automaticamente nos perfis de tenants já existentes — só no template usado para tenants novos.

## Utilizado por
- Toda funcionalidade do menu administrativo — ver [[Funcionalidades]].
- Guard de rota e de menu no frontend (`ProtectedRoute.jsx`, `Layout.jsx`) — ver [[Autorizacao#Autorização no frontend vs. backend]].

## Não identificado
- ❓ Processo formal de auditoria periódica de quem tem qual permissão em cada tenant (fora do escopo desta análise de código).
