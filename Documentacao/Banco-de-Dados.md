---
tipo: base
atualizado: 2026-09-12
---

# Banco de Dados

Fonte: leitura direta de `backend/app/*_models.py` e `backend/alembic/versions/` por agente de exploração dedicado. Ver [[Arquitetura]], [[Autorizacao]], [[Dominio]].

## Tecnologia (confirmado)

- PostgreSQL (16 em DEV, `docker-compose.local-dev.yml`)
- SQLAlchemy 2.0 como ORM
- Alembic para migrations — **317 arquivos** em `backend/alembic/versions/`
  - Migration raiz: `bda1c213cae2_base_inicial_completa.py` (Create Date 2026-02-18)
  - Mais recente: `zzo20260911a1_tenant_codigo_municipio.py` (2026-09-11)
  - Um outlier com data `2025-01-01` (`n2o3p4q5r6s7_create_canal_descontos.py`) parece erro de digitação na migration, não a raiz real da cadeia — ❓ necessita validação.

## Multi-tenancy e isolamento (confirmado — o controle mais forte do sistema)

Isolamento é feito em **duas camadas independentes e simultâneas** (defesa em profundidade), não apenas uma:

### 1. Row Level Security real no PostgreSQL
Confirmado em `backend/alembic/versions/ps20260611a1_rls_core_onboarding_tables.py` e ~28 outras migrations com o padrão:
```sql
ALTER TABLE x ENABLE ROW LEVEL SECURITY;
ALTER TABLE x FORCE ROW LEVEL SECURITY;
CREATE POLICY x_tenant_isolation ON x
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true),'')::uuid)
  WITH CHECK (...);
```
O contexto é propagado por `set_config('app.tenant_id', ..., true)` (`backend/app/tenancy/rls.py:47-58`), acoplado a um hook `before_flush` do SQLAlchemy.

### 2. Filtro automático por query no ORM, com fail-fast
`backend/app/tenancy/filters.py` registra um hook `do_orm_execute` (linha 336) que injeta `WHERE tenant_id = ?` em **todo** SELECT sobre modelos `BaseTenantModel`/`TenantScoped` (linhas 236-267). Se não houver `tenant_id` no contexto da requisição e a tabela não estiver na whitelist explícita (linhas 32-66, tabelas cross-tenant documentadas linha a linha), o código **levanta `RuntimeError`** (linhas 269-318) em vez de silenciosamente devolver dados de todos os tenants.

Isso significa: mesmo que um desenvolvedor esqueça de filtrar por tenant numa rota nova, o sistema falha explicitamente (fail-closed) em vez de vazar dados entre empresas — proteção estrutural contra BOLA/IDOR entre tenants. Ver [[Autorizacao]] e [[Vulnerabilidades]].

Casos de compartilhamento deliberado entre tenants parceiros (veterinário parceiro, grupos de empresas com estoque compartilhado) usam subqueries explícitas, não bypass genérico (`filters.py:77-157`).

**Não é isolamento por schema separado** — é `tenant_id` (coluna) + RLS, confirmado; não há schema-per-tenant.

## Modelos por domínio (confirmado, arquivo de origem)

| Domínio | Arquivo(s) principal(is) | Entidades chave |
|---|---|---|
| Core/Tenant/Auth | `base_models.py`, `models.py`, `models_authz.py` | `Tenant`, `User`, `UserSession`, `Role`, `Permission`, `RolePermission`, `UserTenant` — ver [[Tenant]], [[Usuario]], [[Role-Permission]] |
| Cadastros | `models_cadastros.py` | `Cliente`, `Pet`, `Especie`, `Raca`, `FornecedorGrupo` — ver [[Cliente]], [[Pet]] |
| Produtos/Estoque | `produtos_catalogo_models.py`, `produtos_estoque_models.py`, `estoque_*_models.py` | `Produto`, `Categoria`, `Marca`, `EstoqueMovimentacao`, `ProdutoLote` — ver [[Produto]] |
| Vendas | `vendas_models.py`, `pedido_models.py` | `Venda`, `VendaItem`, `VendaPagamento`, `Pedido` (DDD aggregate, e-commerce) — ver [[Venda]] |
| Financeiro | `financeiro/models_contas.py`, `models_caixa.py`, `models_conciliacao.py` | `ContaPagar`, `ContaReceber`, `ContaBancaria`, `ExtratoBancario` — ver [[ContaPagar]], [[ContaReceber]] |
| Banho e Tosa | `banho_tosa_model_parts/*` | `BanhoTosaAgendamento`, `Atendimento`, `Pacote`, `Recorrencia` |
| Veterinário | `veterinario_models.py`, `evolucao_models.py` | consultas, exames, internações |
| Integrações/Fiscal | `bling_connection_models.py`, `ifood_integration_models.py`, `fiscal_models/*` | conexões OAuth, cache de NF-e |
| Billing/Comissões | `billing_models.py`, `comissoes_models.py` | `BillingWebhookEvent`, comissões de vendedor |

Lista completa de ~50 arquivos de modelo é conhecida mas não replicada aqui integralmente para evitar redundância com o código-fonte; consultar `backend/app/*_models.py`.

## Relacionamentos estruturais das entidades centrais (confirmado)

- **Tenant** → raiz; praticamente toda tabela de negócio tem `tenant_id` (via mixin, não FK física na maioria dos casos).
- **User** → pertence a `Tenant`; `UserTenant` faz o vínculo N:N `User ↔ Tenant ↔ Role`.
- **Role/Permission** → `Role` é por tenant; `Permission` é global; `RolePermission` liga os dois por tenant.
- **Cliente** → `user_id`, `auth_user_id` → `users.id`; `merged_into_id` → auto-FK para merge de duplicados; tem muitos `Pet` (cascade delete-orphan).
- **Pet** → `cliente_id` → `clientes.id`.
- **Produto** → `categoria_id`, `marca_id`, `departamento_id`; `produto_pai_id` → auto-FK (variações/kits).
- **Venda** → `cliente_id`, `vendedor_id` (`users.id`), `caixa_id`; tem muitos `VendaItem`, `VendaPagamento`.
- **VendaItem** → `venda_id` (CASCADE), `produto_id`, `lote_id`, `pet_id`, e um `tenant_id` explícito adicional (RESTRICT) — camada extra de proteção.
- **ContaPagar/ContaReceber** → `fornecedor_id` (`clientes.id`), `categoria_id`; `ContaPagar` tem auto-FK para parcelamento (`conta_principal_id`) e recorrência (`conta_recorrencia_origem_id`).
- **Caixa** → tem muitas `MovimentacaoCaixa`.

## Cache e fila (confirmado)

- **Redis**: opcional, ativado apenas se `REDIS_URL` estiver definida (`backend/app/cache/cache_manager.py`); usado em só 2 pontos (cache genérico e `ai/context_builder.py`) — não é infraestrutura crítica.
- **Celery/Kombu**: no `requirements.txt`, **sem uso real confirmado** no código (só comentários/TODO).
- **Filas reais**: tabelas Postgres com `SELECT FOR UPDATE SKIP LOCKED` (ex.: `campaign_event_queue`, fila de webhook de pedido Bling).

## Não identificado

- Detalhamento completo de `fiscal_models/` e `read_models/` (existência confirmada, conteúdo não auditado em profundidade).
- ❓ Necessita validação: RPO/RTO formal de backup (existe rotina de backup/restore documentada em `docs/PRODUCAO_BACKUP_RESTORE_TESTE.md`, mas metas de tempo de recuperação não foram encontradas no código).
