---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — fiscal_catalogo_produtos

## Definição
Catálogo de sugestão fiscal por palavra-chave: matching textual simples entre descrição do produto e categoria fiscal/NCM/CST sugeridos.

## Confirmado no código
🔴 **Duplicação com risco real de crash confirmado** (mais grave que os achados anteriores de dead code inofensivo): duas classes ORM mapeiam a mesma tabela —
- `fiscal_catalogo_produtos_models.py:6` (top-level, **canônica em runtime**).
- `fiscal_models/fiscal_catalogo_produtos.py:6` (cópia idêntica).

Ambas usam o **mesmo objeto `Base`/registry** (`app.db.base_class.Base`, reexportado por `db/core.py`). Foi reproduzido isoladamente que registrar as duas na mesma `MetaData` gera `sqlalchemy.exc.InvalidRequestError: Table already defined for this MetaData instance`. Hoje isso não quebra porque o runtime do FastAPI (`main.py`/`main_routers.py`) nunca importa `app.db.base`/`app.fiscal_models` (só o Alembic e 2 scripts de seed importam) — mas é uma armadilha latente para qualquer refactor, teste de integração completo ou script que junte os dois grafos de import.

- Colunas: `palavras_chave` (Text, matching por keyword), `categoria_fiscal`, `ncm`, `cest`, `cst_icms`, `icms_st` (bool), `pis_cst`, `cofins_cst`, `observacao`, `ativo` (default True).

## Relacionamentos
- Sem FK de saída nem de entrada.

## Utilizado por
- `services/fiscal_sugestao_service.py` (SELECT com `ativo=true`, compara palavras-chave com a descrição do produto).
- `api/v1/fiscal_sugestao.py`, roteado e registrado em `main_routers.py:121,540` (`fiscal_sugestao_router`) — rota ativa.

## Não identificado
- 🔴 **Risco a levar ao time com prioridade**: remover a cópia órfã (`fiscal_models/fiscal_catalogo_produtos.py`) antes que algum teste/script una os dois grafos de import e derrube o processo.
