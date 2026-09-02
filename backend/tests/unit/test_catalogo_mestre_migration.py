from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
MIGRATION = BACKEND_ROOT / "alembic/versions/zxn20260829a1_catalogo_mestre_produtos.py"
WORKER_MIGRATION = (
    BACKEND_ROOT
    / "alembic/versions/zxp20260829a1_fila_enriquecimento_catalogo_mestre.py"
)
CANDIDATE_MIGRATION = (
    BACKEND_ROOT / "alembic/versions/zys20260829a1_catalogo_mestre_candidatos_ean.py"
)


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


def test_catalog_worker_migration_adds_lease_and_execution_audit():
    source = WORKER_MIGRATION.read_text(encoding="utf-8")

    assert 'revision = "zxp20260829a1"' in source
    assert 'down_revision = "zxo20260829a1"' in source
    for field_name in (
        "reservada_por",
        "reserva_expira_em",
        "ultima_execucao_em",
    ):
        assert f'"{field_name}"' in source
    assert '"catalogo_mestre_enriquecimento_execucoes"' in source
    assert 'op.drop_table("catalogo_mestre_enriquecimento_execucoes")' in source
    assert '"produtos"' not in source


def test_catalog_candidate_migration_keeps_unverified_eans_outside_master():
    source = CANDIDATE_MIGRATION.read_text(encoding="utf-8")

    assert 'revision = "zys20260829a1"' in source
    assert 'down_revision = "zyr20260829a1"' in source
    assert '"catalogo_mestre_produto_candidatos"' in source
    assert '"catalogo_mestre_candidato_evidencias"' in source
    assert '"fonte_identidade_status"' in source
    assert '"direitos_uso_status"' in source
    assert '"staging_path"' in source
    assert '"preco_venda"' not in source
    assert '"estoque_atual"' not in source
