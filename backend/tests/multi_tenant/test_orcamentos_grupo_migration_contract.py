from pathlib import Path


MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "zzt20260915a1_orcamentos_grupo_piloto.py"
)


def test_migration_cria_tabelas_com_rls_e_piloto_demo():
    conteudo = MIGRATION.read_text(encoding="utf-8")

    assert 'revision = "zzt20260915a1"' in conteudo
    assert 'down_revision = "zzs20260915a1"' in conteudo
    for tabela in (
        "orcamento_grupo_configuracoes",
        "orcamento_grupo_empresas",
        "orcamentos_grupo",
        "orcamento_grupo_itens",
        "orcamento_grupo_cotacoes",
    ):
        assert tabela in conteudo
    assert "ENABLE ROW LEVEL SECURITY" in conteudo
    assert "FORCE ROW LEVEL SECURITY" in conteudo
    assert "current_setting('app.tenant_id'" in conteudo
    assert "corepeterp@gmail.com" in conteudo
    assert "ORCAMENTOS_GRUPO" in conteudo
