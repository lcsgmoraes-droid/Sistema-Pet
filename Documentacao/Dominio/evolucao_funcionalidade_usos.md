---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — evolucao_funcionalidade_usos

## Definição
Tabela **global** (sem `tenant_id`) — conta uso de funcionalidades "em teste" no produto CorePet como um todo.

## Confirmado no código
- Modelo: `evolucao_models.py:15-21` (`EvolucaoFuncionalidadeUso`). PK é `item_id` (string), não `id` autoincrement.
- Acessada via SQLAlchemy Core (`__table__`, insert/update/select diretos), não via ORM session.

## Relacionamentos
- Sem FK.

## Utilizado por
- `evolucao_corepet.py::registrar_uso_funcionalidade`, chamada a partir de várias rotas de negócio (`empresa_grupo_routes.py`, `nao_venda_routes.py`, `pendencia_estoque_routes.py`, rotas do app mobile do funcionário, checkout do e-commerce).
- Exposta via `routes/evolucao_routes.py` (registrado em `main_routers.py:185`).

## Não identificado
- ⚠️ **Não está listada em `alembic/env.py` nem em `db/base.py`**, apesar de estar em uso ativo em produção — só entra no metadata do SQLAlchemy transitivamente quando `evolucao_routes` é importado no boot da app. Risco de drift para `alembic revision --autogenerate`.
