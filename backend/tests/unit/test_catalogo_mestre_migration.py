from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
MIGRATION = BACKEND_ROOT / "alembic/versions/zxn20260829a1_catalogo_mestre_produtos.py"


def test_catalogo_mestre_migration_is_linear_and_reversible():
    source = MIGRATION.read_text(encoding="utf-8")

    assert 'revision = "zxn20260829a1"' in source
    assert 'down_revision = "zxm20260829a1"' in source
    for table_name in (
        "catalogo_mestre_produtos",
        "catalogo_mestre_imagens",
        "catalogo_mestre_pendencias",
        "catalogo_mestre_sincronizacoes",
    ):
        assert f'"{table_name}"' in source
    assert "op.drop_table(table_name)" in source


def test_catalogo_mestre_schema_separates_source_and_operational_data():
    source = MIGRATION.read_text(encoding="utf-8")

    assert '"origem_tenant_id"' in source
    assert '"origem_produto_id"' in source
    assert '"proveniencia"' in source
    assert '"snapshot_origem_hash"' in source
    assert '"imagem_meta_quantidade"' in source
    assert '"direitos_uso_status"' in source
    assert '"gerada_por_ia"' in source
    assert '"posologia"' in source
    assert '"bula_conteudo"' in source
    assert '"preco_venda"' not in source
    assert '"estoque_atual"' not in source
