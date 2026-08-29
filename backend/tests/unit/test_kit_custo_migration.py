from pathlib import Path
import runpy
from types import SimpleNamespace


MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "zxn20260829a1_backfill_custos_kits.py"
)


def test_backfill_custos_kits_encadeia_head_e_preserva_tenant(monkeypatch):
    migration = runpy.run_path(str(MIGRATION))
    comandos = []
    bind = SimpleNamespace(execute=lambda statement: comandos.append(str(statement)))
    inspector = SimpleNamespace(
        get_table_names=lambda: ["produtos", "produto_kit_componentes"]
    )

    monkeypatch.setattr(migration["op"], "get_bind", lambda: bind)
    monkeypatch.setattr(migration["sa"], "inspect", lambda _bind: inspector)

    migration["upgrade"]()

    assert migration["revision"] == "zxn20260829a1"
    assert migration["down_revision"] == "zxm20260829a1"
    assert len(comandos) == 1
    sql = comandos[0]
    assert "componente.tenant_id = rel.tenant_id" in sql
    assert "kit.tenant_id = custos.tenant_id" in sql
    assert "COALESCE(componente.preco_custo, 0)" in sql
    assert "COALESCE(rel.quantidade, 0)" in sql
