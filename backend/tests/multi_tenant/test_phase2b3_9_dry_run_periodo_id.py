import json

from sqlalchemy import text

from app.scripts.dry_run_dre_detalhe_canais_periodo_id import (
    analisar_periodo_id_dre_detalhe_canais,
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
                (10, :tenant_a, 1, '2026-05-01', '2026-05-31', 5, 2026, 'provisao'),
                (11, :tenant_a, 1, '2026-06-01', '2026-06-30', 6, 2026, 'provisao'),
                (12, :tenant_a, 1, '2026-06-01', '2026-06-30', 6, 2026, 'provisao'),
                (13, :tenant_b, 2, '2026-08-01', '2026-08-31', 8, 2026, 'loja_fisica')
            """
        ),
        {"tenant_a": TENANT_A, "tenant_b": TENANT_B},
    )
    db.execute(
        text(
            """
            INSERT INTO dre_detalhe_canais
                (id, tenant_id, usuario_id, data_inicio, data_fim, mes, ano, canal, receita_bruta)
            VALUES
                (100, :tenant_a, 1, '2026-05-01', '2026-05-31', 5, 2026, 'provisao_consumo', 1000),
                (101, :tenant_a, 1, '2026-06-01', '2026-06-30', 6, 2026, 'ajuste_ferias', 2000),
                (102, :tenant_a, 1, '2026-07-01', '2026-07-31', 7, 2026, 'provisao', 3000),
                (103, :tenant_a, 1, '2026-05-01', '2026-05-31', 5, 2026, 'canal_novo', 4000),
                (104, :tenant_b, 2, '2026-08-01', '2026-08-31', 8, 2026, 'loja_fisica', 5000)
            """
        ),
        {"tenant_a": TENANT_A, "tenant_b": TENANT_B},
    )


def test_vinculo_univoco_gera_candidato_a_periodo_id():
    db = _session()

    relatorio = analisar_periodo_id_dre_detalhe_canais(db)

    assert relatorio["resumo"]["dre_detalhe_canais_total"] == 5
    assert relatorio["resumo"]["vinculo_completo_univoco"] == 2
    assert relatorio["resumo"]["seriam_atualizados_com_periodo_id"] == 2


def test_vinculo_ambiguo_sem_vinculo_e_canal_desconhecido_bloqueiam():
    db = _session()

    relatorio = analisar_periodo_id_dre_detalhe_canais(db)

    assert relatorio["resumo"]["vinculo_completo_ambiguo"] == 1
    assert relatorio["resumo"]["sem_vinculo_completo"] == 1
    assert relatorio["resumo"]["canais_nao_classificados_total"] == 1
    assert relatorio["resumo"]["exigiriam_revisao_manual"] == 3
    assert relatorio["seguranca"]["pode_criar_migration_periodo_id"] is False
    assert "ha_vinculos_ambiguos" in relatorio["seguranca"]["motivos_bloqueio"]
    assert "ha_detalhes_sem_vinculo" in relatorio["seguranca"]["motivos_bloqueio"]
    assert "ha_canais_nao_classificados" in relatorio["seguranca"]["motivos_bloqueio"]


def test_canal_tecnico_mapeia_para_provisao_e_canal_conhecido_fica_igual():
    db = _session()

    relatorio = analisar_periodo_id_dre_detalhe_canais(db)
    canonical = {row["canal"]: row["total"] for row in relatorio["distribuicao_canal_canonico"]}

    assert canonical["provisao"] == 3
    assert canonical["loja_fisica"] == 1
    assert canonical["nao_classificado"] == 1


def test_relatorio_nao_expoe_dados_sensiveis():
    db = _session()

    relatorio = analisar_periodo_id_dre_detalhe_canais(db)
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

    analisar_periodo_id_dre_detalhe_canais(db)

    depois_periodos = db.execute(text("SELECT COUNT(*) FROM dre_periodos")).scalar()
    depois_detalhes = db.execute(text("SELECT COUNT(*) FROM dre_detalhe_canais")).scalar()
    assert depois_periodos == antes_periodos
    assert depois_detalhes == antes_detalhes
