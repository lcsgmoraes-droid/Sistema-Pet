---
tipo: dominio-tabela
atualizado: 2026-09-13
---

# Tabela — kit_composicao

Ver [[produto_kit_componentes]], [[Produto]].

## Definição
⚠️ **Tabela existente no banco (via migration Alembic) mas sem nenhum uso confirmado em código de aplicação vivo.** A lógica real de composição de kits usa [[produto_kit_componentes]].

## Confirmado no código
Dois arquivos diferentes definem `class KitComposicao` com o mesmo `__tablename__ = "kit_composicao"`:
- `app/kit_composicao_models.py:6-33` — herda `.db.Base` diretamente (**não** `BaseTenantModel`), `tenant_id` é `Integer` simples (não UUID — foge do padrão multi-tenant do resto do sistema), FKs reais `produto_kit_id`/`produto_item_id`/`variacao_item_id → produtos.id`.
- `app/fiscal_models/kit_composicao.py:1-32` — mesma estrutura, mas com FKs **desabilitadas** (comentário literal na linha 12: `"TEMPORÁRIO: FKs desabilitadas - tabelas não existem ainda"`); os mesmos três campos são `Integer` soltos, sem `ForeignKey`.

### Investigação de uso real
- `grep` por import de `app.kit_composicao_models` em todo `app/`: zero resultados — nunca importado.
- `app/fiscal_models/__init__.py:14` importa a segunda versão, e `app/db/base.py:16` a importa por sua vez — mas só para o Alembic enxergar a tabela no metadata (comentário no arquivo confirma essa intenção).
- `grep` por uso real da classe (query/insert/update) em qualquer service/rota: zero resultados.
- A lógica de kit realmente ativa é [[produto_kit_componentes]] (`kit_custo_service.py`, `kit_estoque_service.py`, `kit_preco_venda_service.py`), que não tem suporte a "variação" (`variacao_item_id`) como esta tabela morta tinha.

## Relacionamentos
- Nenhum uso vivo confirmado.

## Utilizado por
- Nada em produção.

## Não identificado
- 🔴 **Risco latente**: se algum dia alguém importar `app/kit_composicao_models.py` junto com `app/fiscal_models/kit_composicao.py`, ambos declaram o mesmo `__tablename__` na mesma `Base.metadata` — colisão que quebraria o boot da aplicação. Recomenda-se remover o arquivo órfão (`app/kit_composicao_models.py`) e decidir se a tabela `kit_composicao` deve ser dropada ou se o suporte a "variação de kit" deveria ser migrado para [[produto_kit_componentes]].
