---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — locais_estoque

Ver [[Produto]], [[estoque_movimentacoes]], [[Tenant]].

## Definição
Local físico/canal de estoque (ex.: interno, marketplace, full). ⚠️ **Achado de risco confirmado: duplicação real de código-fonte, provavelmente feature planejada e nunca conectada ao fluxo vivo do sistema.**

## Confirmado no código
Dois arquivos diferentes definem `class LocalEstoque(BaseTenantModel)` com o mesmo `__tablename__ = "locais_estoque"`:
- `app/estoque_local_models.py:5-19` — campos `nome`, `tipo` (interno|marketplace), `ativo`. **Sem** `origem_padrao`.
- `app/local_estoque_models.py:5-21` — campos `nome`, `tipo` (interno|full), `origem_padrao` (bool), `ativo`.

### Investigação de uso real
- `app/estoque_transferencia_service.py:4` importa `from app.estoque_local_models import EstoqueLocal` — mas esse arquivo só define `LocalEstoque`, não `EstoqueLocal`. **Import quebrado** (ImportError garantido se o módulo for carregado). O service também referencia campos (`EstoqueLocal.sku`, `.local_estoque_id`) que não existem em nenhum dos dois modelos reais.
- Esse service só é importado por `app/estoque_importacao_csv_routes.py:7` e `app/estoque_importacao_pdf_routes.py:8`.
- Nenhum arquivo do app registra (`include_router`) essas duas rotas — elas não estão conectadas ao FastAPI ativo.
- As mesmas duas rotas, à parte do service quebrado, usam corretamente `from app.local_estoque_models import LocalEstoque` (o arquivo com `origem_padrao`).
- Único uso comprovado de "locais_estoque" em código vivo: infraestrutura genérica (RLS/auditoria) — `alembic/versions/ss20260613a1_rls_stock_locations.py:22`, `app/db/sql_audit_tables.py:27`, `app/utils/tenant_safe_sql.py:71`, `tests/multi_tenant/test_rls_stock_locations_migration.py:14`. Nenhum service/rota ativo popula a tabela com dados de negócio reais — o fluxo real de estoque usa os campos livres `estoque_origem`/`estoque_destino` (string) em [[estoque_movimentacoes]].

## Relacionamentos
- Sem FK de saída/entrada confirmada em uso vivo.

## Utilizado por
- Nada em produção, pelo confirmado nesta pesquisa — só infraestrutura de RLS/auditoria genérica.

## Não identificado
- 🔴 **Risco a levar ao time**: dois modelos duplicados para a mesma tabela, um import quebrado (`EstoqueLocal` inexistente) num service cujas únicas rotas consumidoras não estão registradas no app. Recomenda-se decidir: (a) qual dos dois arquivos consolidar, (b) se `estoque_transferencia_service.py`/as rotas de importação CSV/PDF são um recurso a terminar de implementar ou a remover.
