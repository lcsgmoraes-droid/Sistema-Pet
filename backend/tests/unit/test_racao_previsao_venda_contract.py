from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _source(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def test_sale_item_persists_and_serializes_feed_end_prediction():
    model = _source("app/vendas_models.py")
    creation = _source("app/vendas/criacao.py")
    update = _source("app/vendas/crud_routes.py")

    for field in ("racao_data_prevista_fim", "racao_prazo_estimado_dias"):
        assert f"{field} = Column" in model
        assert f'"{field}"' in model
        assert f"{field}=previsao_racao" in creation
        assert f"{field}=previsao_racao" in update


def test_recurrence_prioritizes_manual_prediction():
    recurrence = _source("app/services/product_recurrence.py")

    assert "resolver_previsao_fim_racao" in recurrence
    assert "if previsao_manual:" in recurrence
    assert "previsao_manual.data_prevista" in recurrence
    assert "previsao_manual.origem" in recurrence


def test_migration_is_linear_and_adds_both_fields():
    migration = _source(
        "alembic/versions/zxi20260827a1_add_racao_previsao_venda_item.py"
    )

    assert 'revision = "zxi20260827a1"' in migration
    assert 'down_revision = "zxh20260827a1"' in migration
    assert '"racao_data_prevista_fim"' in migration
    assert '"racao_prazo_estimado_dias"' in migration
