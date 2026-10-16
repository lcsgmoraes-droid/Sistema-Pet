---
tipo: dominio-tabela
atualizado: 2026-10-07
---

# kit_composicao — removida (código órfão, nunca existiu no banco)

Ver [[produto_kit_componentes]], [[Produto]].

## Status

🟢 **Removida.** `app/kit_composicao_models.py` foi apagado, e a reexportação em
`app/fiscal_models/__init__.py` / `app/db/base.py` também. A lógica real de
composição de kits usa [[produto_kit_componentes]] — nada muda para quem já usa
kits no sistema.

## Por que foi removida

Era uma classe ORM (`class KitComposicao`, `__tablename__ = "kit_composicao"`)
sem nenhum uso em rota ou serviço — confirmado por `grep` em todo o `app/` antes
da remoção. A tabela **nunca existiu em nenhum banco real** (nem produção, nem
dev, nem um banco migrado do zero com a cadeia completa de Alembic): nenhuma
migração jamais criou `kit_composicao`. Por isso a remoção não precisou de
migração nenhuma — não havia nada para dropar no banco, só a classe Python.

Ela também não herdava `BaseTenantModel`/`TenantScoped`, então não entrava no
filtro automático de loja. Como não existe nenhuma consulta real a essa classe,
isso nunca foi um risco em produção — só uma armadilha para o futuro (se alguém
reaproveitasse essa classe parada como base de uma feature nova, sem repor o
filtro de tenant). Removida a classe, o risco deixa de existir.

Uma segunda versão divergente, `app/fiscal_models/kit_composicao.py` (com FKs
desabilitadas), mencionada numa revisão anterior deste documento, já tinha sido
consolidada/removida numa limpeza anterior — só restava a reexportação em
`app/fiscal_models/__init__.py` apontando para `app/kit_composicao_models.py`,
também removida agora.

## Confirmação

- `grep -rn "KitComposicao" app/ tests/` não retorna nenhum uso real (só o
  comentário deste histórico, se procurado em `fiscal_models/__init__.py`).
- `tests/multi_tenant/test_tenant_model_registry.py::test_nenhum_modelo_novo_com_tenant_id_herda_base_direto`
  deixou de listar `kit_composicao` entre os modelos expostos sem filtro de
  tenant.
- A aplicação importa normalmente (`import app.main`) sem a classe.
