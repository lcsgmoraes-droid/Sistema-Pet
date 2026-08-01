from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "alembic" / "versions" / "zwr20260801a1_backfill_codigos_pessoas.py"
IMPORTACAO = ROOT / "app" / "importacao_pessoas.py"


def test_migration_backfills_blank_person_codes_per_tenant():
    source = MIGRATION.read_text(encoding="utf-8")

    assert 'down_revision = "zwq20260731a1"' in source
    assert "ROW_NUMBER() OVER" in source
    assert "PARTITION BY tenant_id" in source
    assert "codigo IS NULL OR BTRIM(codigo) = ''" in source
    assert "tenant_max.maior_codigo + sem_codigo.sequencia" in source


def test_excel_import_generates_code_when_column_is_empty():
    source = IMPORTACAO.read_text(encoding="utf-8")

    assert (
        'codigo_pessoa = str(codigo or "").strip() or gerar_codigo_cliente(' in source
    )
    assert "codigo=codigo_pessoa" in source
