# Contrato Multitenant e Onboarding

Este documento define a regra de engenharia para manter o SaaS seguro daqui para frente.
Ele nao exige backfill de tenants existentes. O foco e proteger novos tenants e impedir
regressao de isolamento.

## Estado Atual

- O filtro global ORM por tenant esta ativo.
- O guard de insert com `tenant_id` esta ativo.
- SQL bruto tenant-scoped deve usar `execute_tenant_safe`.
- `app.db.core` e o modulo canonico de banco.
- O cadastro de nova empresa usa onboarding em modo estrito.
- Novos tenants recebem copias proprias dos templates globais.
- Templates globais nao sao editados pelo usuario.
- Dados copiados pertencem ao tenant e podem ser editados sem afetar outros tenants.
- Produtos de referencia continuam opcionais; nao sao copiados automaticamente no cadastro padrao.

## Regra-Mae

Template global pertence ao sistema.
Dado do tenant pertence a empresa.
Usuario nunca edita o template global diretamente.

## Fluxo Obrigatorio Para Novo Tenant

Ao cadastrar uma nova empresa:

1. Criar tenant.
2. Criar usuario admin.
3. Criar role/permissoes do tenant.
4. Rodar `onboard_tenant_defaults(..., strict_required=True)`.
5. Copiar dados obrigatorios:
   - formas de pagamento;
   - categorias DRE;
   - subcategorias DRE;
   - categorias financeiras;
   - tipos de despesa;
   - departamentos de produto;
   - categorias de produto.
6. Registrar auditoria em `tenant_template_installs`.
7. Registrar mapeamento item-a-item em `tenant_template_item_installs`.
8. Se qualquer etapa obrigatoria falhar, fazer rollback do cadastro.

## Checks Obrigatorios Antes de Liberar Cadastro Novo

Rodar:

```powershell
python backend/app/scripts/run_tenant_onboarding.py --signup-readiness-check --include-products
```

Resultado esperado:

- `ok = true`
- `blockers = []`
- `migration.ok = true`
- `template_contract.ok = true`
- `future_tenant_simulation.ok = true`
- `missing_template_tables = []`
- `missing_operational_tables = {}`

Se falhar, nao liberar cadastro novo ate corrigir o bloqueio.

## Smoke Test Controlado

Para validar sem sujar banco:

1. Abrir transacao.
2. Criar dois tenants descartaveis.
3. Rodar onboarding nos dois com `strict_required=True`.
4. Confirmar contagens:
   - `formas_pagamento = 4`
   - `dre_categorias = 3`
   - `dre_subcategorias = 4`
   - `categorias_financeiras = 2`
   - `tipo_despesas = 2`
   - `departamentos = 1`
   - `categorias = 2`
   - `produtos = 0`
   - `tenant_template_installs = 1`
   - `tenant_template_item_installs = 18`
5. Editar uma copia do tenant A.
6. Confirmar que tenant B e template global nao mudam.
7. Reexecutar onboarding no tenant A e confirmar que nao duplica.
8. Fazer rollback.
9. Confirmar que os tenants descartaveis nao persistiram.

## Regras Para Codigo Novo

- Toda tabela tenant-scoped precisa de `tenant_id`.
- Toda rota multi-tenant precisa obter tenant pelo contexto/autenticacao.
- Nenhuma funcao de negocio deve depender apenas de `user_id` para isolamento.
- `db.execute`, `session.execute` e `text(...)` em tabela tenant-scoped devem usar `execute_tenant_safe`.
- SQL tenant-scoped deve conter marcador `{tenant_filter}` em `SELECT`, `UPDATE` e `DELETE`.
- `INSERT` tenant-scoped deve gravar `tenant_id` explicitamente.
- Nao usar string interpolation com valores de usuario em SQL.
- Nao converter UUID para string em comparacao ORM quando a coluna usa `UUID(as_uuid=True)`.
- Nao desativar `app.tenancy.filters`.
- Nao desativar `app.database.orm_guards`.
- Nao criar endpoints que leem dados de tenant sem contexto.
- Nao aplicar templates em tenants existentes por padrao.

## Templates Globais

Templates globais ficam em:

- `template_bundles`
- `template_items`

Copias e auditoria por tenant ficam em:

- tabelas operacionais do tenant;
- `tenant_template_installs`;
- `tenant_template_item_installs`.

O mapeamento item-a-item e obrigatorio para idempotencia. Ele impede que uma copia editada
por um tenant seja recriada como duplicata em uma nova execucao do onboarding.

## Produtos

Produtos de referencia sao opcionais.

Padrao atual:

- cadastro normal nao copia produtos;
- importacao/copia de produtos deve ser acao explicita;
- produtos importados pertencem ao tenant;
- editar produto importado nao altera template nem outro tenant.

## Catalogo Base Administrativo

O catalogo base da loja `admin@mlprohub.com.br` pode ser importado por acao administrativa
para novos tenants que quiserem iniciar com uma lista pronta de produtos.

Regras obrigatorias:

- a importacao e opcional e deve ter `dry-run` antes de `apply`;
- a fonte padrao e a loja do Lucas, mas o destino recebe copias proprias;
- copiar departamentos/grupos, categorias, marcas, cadastros auxiliares de racao,
  produtos e imagens;
- nao copiar Bling, filas, IDs externos, fornecedores, lotes, historico de preco,
  movimentacoes, estoque, custo, margem, preco de venda, preco app ou preco ecommerce;
- todo produto importado deve entrar com estoque e precos zerados;
- uma nova execucao nao deve sobrescrever produtos ja importados nem duplicar registros;
- a idempotencia deve usar `tenant_template_installs` e `tenant_template_item_installs`
  com `bundle_code = catalogo-base-loja-lucas`.

## Migracoes

Antes de aplicar migration em ambiente real:

1. Confirmar ambiente.
2. Fazer backup se houver dados reais.
3. Rodar `alembic current`.
4. Rodar `alembic heads`.
5. Aplicar apenas a revision auditada.
6. Nao rodar `alembic upgrade head` cegamente se houver migration nova nao auditada.
7. Rodar `--signup-readiness-check`.
8. Rodar smoke tests.

## Producao

Em producao:

- nao criar tenant descartavel sem confirmacao explicita;
- nao rodar migrations sem backup e janela adequada;
- checks publicos devem ser somente leitura;
- qualquer erro no onboarding de novo tenant deve falhar fechado e fazer rollback.

## Considerado Fechado Nesta Fase

Podemos considerar a base de novos tenants estruturada quando:

- `--signup-readiness-check --include-products` estiver verde;
- suite `backend/tests/multi_tenant` estiver verde;
- `import app.main` estiver ok;
- smoke transacional confirmar copia, isolamento, idempotencia e rollback;
- producao estiver saudavel nos endpoints read-only.

## Pontos Que Continuam Para Fases Futuras

- Auditar e reduzir SQL bruto legado fora do escopo ja endurecido.
- Revisar modulos administrativos que manipulam tabelas globais.
- Evoluir versionamento de templates para upgrade assistido por tenant.
- Criar UI/fluxo controlado para importacao opcional de produtos.
- Resolver warnings de encoding no Windows.
