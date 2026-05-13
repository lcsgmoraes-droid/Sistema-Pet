import json

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.scripts.dry_run_dre_periodos_tenant_backfill import (
    analisar_dre_periodos_backfill,
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
                (2, NULL, 'SENSITIVE_NAME_B', 'SENSITIVE_EMAIL_B', 'SENSITIVE_DOC_B'),
                (3, :tenant_b, 'SENSITIVE_NAME_C', 'SENSITIVE_EMAIL_C', 'SENSITIVE_DOC_C')
            """
        ),
        {"tenant_a": TENANT_A, "tenant_b": TENANT_B},
    )
    db.execute(
        text(
            """
            INSERT INTO dre_periodos
                (id, usuario_id, data_inicio, data_fim, mes, ano, canal)
            VALUES
                (10, 1, '2026-05-01', '2026-05-31', 5, 2026, 'loja_fisica'),
                (11, 1, '2026-05-01', '2026-05-31', 5, 2026, 'loja_fisica'),
                (12, 2, '2026-05-01', '2026-05-31', 5, 2026, 'loja_fisica'),
                (13, 999, '2026-06-01', '2026-06-30', 6, 2026, 'marketplace'),
                (14, NULL, '2026-07-01', '2026-07-31', 7, 2026, 'loja_fisica'),
                (15, 3, '2026-05-01', '2026-05-31', 5, 2026, 'loja_fisica')
            """
        )
    )
    db.execute(
        text(
            """
            INSERT INTO dre_detalhe_canais
                (id, tenant_id, usuario_id, data_inicio, data_fim, mes, ano, canal, receita_bruta)
            VALUES
                (100, :tenant_a, 1, '2026-05-01', '2026-05-31', 5, 2026, 'loja_fisica', 1000),
                (101, :tenant_b, 3, '2026-05-01', '2026-05-31', 5, 2026, 'loja_fisica', 2000),
                (102, :tenant_a, 1, '2026-06-01', '2026-06-30', 6, 2026, 'loja_fisica', 3000)
            """
        ),
        {"tenant_a": TENANT_A, "tenant_b": TENANT_B},
    )


def test_dry_run_identifica_periodos_mapeaveis_e_orfaos():
    db = _session()

    relatorio = analisar_dre_periodos_backfill(db)

    assert relatorio["dre_periodos"]["total"] == 6
    assert relatorio["dre_periodos"]["usuario_id_preenchido"] == 5
    assert relatorio["dre_periodos"]["usuario_id_nulo"] == 1
    assert relatorio["usuarios"]["referenciados_distintos"] == 4
    assert relatorio["usuarios"]["referenciados_encontrados"] == 3
    assert relatorio["usuarios"]["referenciados_nao_encontrados"] == 1
    assert relatorio["usuarios"]["referenciados_com_tenant_id"] == 2
    assert relatorio["usuarios"]["referenciados_sem_tenant_id"] == 1
    assert relatorio["backfill"]["mapeaveis_via_usuario"] == 3
    assert relatorio["backfill"]["orfaos_ou_sem_tenant"] == 3


def test_dry_run_identifica_duplicidade_por_tenant_mes_ano_canal():
    db = _session()

    relatorio = analisar_dre_periodos_backfill(db)

    assert relatorio["backfill"]["duplicidades_potenciais_grupos"] == 1
    assert relatorio["backfill"]["duplicidades_potenciais_registros"] == 2
    grupo = relatorio["duplicidades_potenciais"][0]
    assert grupo["tenant_ref"]
    assert grupo["tenant_ref"] != TENANT_A
    assert grupo["ano"] == 2026
    assert grupo["mes"] == 5
    assert grupo["canal"] == "loja_fisica"
    assert grupo["total"] == 2


def test_dry_run_identifica_periodos_sobrepostos():
    db = _session()

    relatorio = analisar_dre_periodos_backfill(db)

    assert relatorio["periodos_sobrepostos"]["pares"] == 1
    assert relatorio["periodos_sobrepostos"]["usuarios_afetados"] == 1


def test_dry_run_classifica_vinculo_com_dre_detalhe_canais():
    db = _session()

    relatorio = analisar_dre_periodos_backfill(db)

    assert relatorio["dre_detalhe_canais"]["total"] == 3
    assert relatorio["dre_detalhe_canais"]["vinculaveis_por_chave_completa"] == 2
    assert relatorio["dre_detalhe_canais"]["sem_vinculo_por_chave_completa"] == 1
    assert relatorio["dre_detalhe_canais"]["vinculos_ambiguos"] == 1
    assert relatorio["dre_detalhe_canais"]["classificacao"] == "ligacao_ambigua"


def test_dry_run_nao_expoe_dados_sensiveis_no_relatorio():
    db = _session()

    relatorio = analisar_dre_periodos_backfill(db)
    serializado = json.dumps(relatorio, ensure_ascii=False).lower()

    assert "sensitive_name" not in serializado
    assert "sensitive_email" not in serializado
    assert "sensitive_doc" not in serializado
    assert TENANT_A not in serializado
    assert TENANT_B not in serializado


def test_dry_run_nao_altera_dados():
    db = _session()
    antes = db.execute(text("SELECT COUNT(*) FROM dre_periodos")).scalar()

    analisar_dre_periodos_backfill(db)

    depois = db.execute(text("SELECT COUNT(*) FROM dre_periodos")).scalar()
    assert depois == antes
