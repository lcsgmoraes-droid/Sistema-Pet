import json

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.scripts.dry_run_dre_detalhe_canais_periodo_id import (
    analisar_periodo_id_dre_detalhe_canais,
)


TENANT_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
TENANT_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


def _session():
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    _create_schema(db)
    _seed_data(db)
    db.commit()
    return db


def _create_schema(db):
    db.execute(
        text(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                tenant_id TEXT NULL,
                nome TEXT NULL,
                email TEXT NULL,
                documento TEXT NULL
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE dre_periodos (
                id INTEGER PRIMARY KEY,
                tenant_id TEXT NULL,
                usuario_id INTEGER NULL,
                data_inicio DATE NULL,
                data_fim DATE NULL,
                mes INTEGER NULL,
                ano INTEGER NULL,
                canal TEXT NULL
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE dre_detalhe_canais (
                id INTEGER PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                usuario_id INTEGER NULL,
                data_inicio DATE NULL,
                data_fim DATE NULL,
                mes INTEGER NULL,
                ano INTEGER NULL,
                canal TEXT NULL,
                receita_bruta NUMERIC NULL
            )
            """
        )
    )


def _seed_data(db):
    db.execute(
        text(
            """
            INSERT INTO users (id, tenant_id, nome, email, documento)
            VALUES
                (1, :tenant_a, 'SENSITIVE_NAME_A', 'SENSITIVE_EMAIL_A', 'SENSITIVE_DOC_A'),
                (2, :tenant_b, 'SENSITIVE_NAME_B', 'SENSITIVE_EMAIL_B', 'SENSITIVE_DOC_B')
            """
        ),
        {"tenant_a": TENANT_A, "tenant_b": TENANT_B},
    )
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
