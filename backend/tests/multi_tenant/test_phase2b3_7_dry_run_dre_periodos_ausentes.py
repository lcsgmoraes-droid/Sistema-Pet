import json

from sqlalchemy import text

from app.scripts.dry_run_criar_dre_periodos_ausentes import (
    analisar_dre_periodos_ausentes_para_detalhes,
)
from tests.multi_tenant.dre_test_helpers import (
    TENANT_A,
    TENANT_B,
    make_dre_session,
    seed_sensitive_dre_users,
)


def _session():
    return make_dre_session(_seed_data)


def _seed_data(db):
    seed_sensitive_dre_users(db)
    db.execute(
        text(
            """
            INSERT INTO dre_periodos
                (id, tenant_id, usuario_id, data_inicio, data_fim, mes, ano, canal)
            VALUES
                (10, :tenant_a, 1, '2026-08-01', '2026-08-31', 8, 2026, 'loja')
            """
        ),
        {"tenant_a": TENANT_A},
    )
    db.execute(
        text(
            """
            INSERT INTO dre_detalhe_canais
                (id, tenant_id, usuario_id, data_inicio, data_fim, mes, ano, canal, receita_bruta)
            VALUES
                (100, :tenant_a, 1, '2026-05-01', '2026-05-31', 5, 2026, 'provisao', 1000),
                (101, :tenant_a, 1, '2026-05-01', '2026-05-31', 5, 2026, 'provisao_consumo', 1000),
                (102, :tenant_a, 1, '2026-06-01', '2026-06-30', 6, 2026, 'ajuste_ferias', 1000),
                (103, :tenant_a, 1, '2026-07-01', '2026-07-31', 7, 2026, 'canal_novo', 1000),
                (104, :tenant_a, 1, '2026-08-01', '2026-08-31', 8, 2026, 'loja', 1000)
            """
        ),
        {"tenant_a": TENANT_A},
    )


def test_canais_tecnicos_mapeiam_para_provisao_e_agrupam():
    db = _session()

    relatorio = analisar_dre_periodos_ausentes_para_detalhes(db)

    assert relatorio["resumo"]["dre_detalhe_canais_analisados"] == 5
    assert relatorio["resumo"]["dre_detalhe_canais_sem_vinculo"] == 4
    assert relatorio["resumo"]["grupos_unicos_periodos_ausentes"] == 3
    assert relatorio["resumo"]["detalhes_cobertos_por_grupos"] == 4
    assert relatorio["resumo"]["detalhes_para_canal_provisao"] == 3
    assert relatorio["resumo"]["grupos_poderiam_ser_criados_automaticamente"] == 2
    assert relatorio["resumo"]["dre_periodos_seriam_criados"] == 2

    canais = {row["canal"]: row["total"] for row in relatorio["distribuicao_canal_canonico"]}
    assert canais["provisao"] == 3


def test_canais_desconhecidos_ficam_nao_classificados():
    db = _session()

    relatorio = analisar_dre_periodos_ausentes_para_detalhes(db)

    assert relatorio["resumo"]["detalhes_canal_nao_classificado"] == 1
    assert relatorio["resumo"]["grupos_exigem_decisao_manual"] == 1
    assert relatorio["canais_nao_classificados"] == [
        {"canal": "canal_novo", "total": 1}
    ]


def test_multiplos_detalhes_do_mesmo_periodo_geram_um_grupo():
    db = _session()

    relatorio = analisar_dre_periodos_ausentes_para_detalhes(db)
    grupos_maio = [
        grupo
        for grupo in relatorio["amostras_agregadas_grupos"]
        if grupo["ano"] == 2026 and grupo["mes"] == 5
    ]

    assert len(grupos_maio) == 1
    assert grupos_maio[0]["canal_canonico"] == "provisao"
    assert grupos_maio[0]["detalhes_total"] == 2


def test_relatorio_nao_expoe_dados_sensiveis():
    db = _session()

    relatorio = analisar_dre_periodos_ausentes_para_detalhes(db)
    serializado = json.dumps(relatorio, ensure_ascii=False).lower()

    assert "sensitive_name" not in serializado
    assert "sensitive_email" not in serializado
    assert "sensitive_doc" not in serializado
    assert TENANT_A not in serializado
    assert TENANT_B not in serializado
    assert "1000" not in serializado


def test_funcao_nao_altera_dados():
    db = _session()
    antes_periodos = db.execute(text("SELECT COUNT(*) FROM dre_periodos")).scalar()
    antes_detalhes = db.execute(text("SELECT COUNT(*) FROM dre_detalhe_canais")).scalar()

    analisar_dre_periodos_ausentes_para_detalhes(db)

    depois_periodos = db.execute(text("SELECT COUNT(*) FROM dre_periodos")).scalar()
    depois_detalhes = db.execute(text("SELECT COUNT(*) FROM dre_detalhe_canais")).scalar()
    assert depois_periodos == antes_periodos
    assert depois_detalhes == antes_detalhes
