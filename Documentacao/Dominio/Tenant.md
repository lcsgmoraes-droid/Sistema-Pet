---
tipo: dominio
atualizado: 2026-09-12
---

# Entidade — Tenant (Empresa)

Ver [[Banco-de-Dados]], [[Autorizacao]].

## Definição
Raiz de todo o isolamento multiempresa do sistema. Também chamado de "empresa" na interface e documentação de negócio.

## Confirmado no código
- Modelo: `backend/app/models.py` (`Tenant`).
- `id`: `String(36)` (UUID como string).
- Praticamente toda tabela de negócio carrega uma coluna `tenant_id` referenciando esta entidade, via mixin `BaseTenantModel`/`TenantScoped` (`base_models.py`), não necessariamente por FK física em todos os casos.
- Isolado por Row Level Security no Postgres + filtro automático fail-closed no ORM — ver [[Banco-de-Dados#Multi-tenancy e isolamento]].
- Ao ser criado, recebe 6 perfis padrão de acesso automaticamente (`docs/PERFIS_ACESSO_PADRAO.md`): Administrador, Gerente, Financeiro, Estoque e Compras, Caixa, Cliente.
- Pode pertencer a um `EmpresaGrupo` (grupo de empresas) com estoque seletivamente compartilhado — `empresa_grupo_models.py`.
- Módulos contratados por tenant controlam quais rotas/menus ficam ativos (`ModulosContext` no frontend, `_module_dependencies` no backend) — ver [[Arquitetura#Módulos ligáveis por tenant]].

## Utilizado por
- Praticamente todas as funcionalidades — [[Funcionalidades]].
- [[Autorizacao]], [[Autenticacao]] (seleção de tenant no login).
- [[Asaas]] (billing da assinatura do tenant).

## Não identificado
- ❓ Regras de RPO/RTO por tenant (backup é do banco inteiro, não por tenant individual, pelo que foi confirmado em `docs/PRODUCAO_BACKUP_RESTORE_TESTE.md`).
