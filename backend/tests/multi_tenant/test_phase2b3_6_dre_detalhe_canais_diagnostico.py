import json

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.scripts.diagnostico_dre_detalhe_canais_vinculo import (
    analisar_dre_detalhe_canais_vinculo,
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
                (2, :tenant_b, 'SENSITIVE_NAME_B', 'SENSITIVE_EMAIL_B', 'SENSITIVE_DOC_B'),
                (3, :tenant_a, 'SENSITIVE_NAME_C', 'SENSITIVE_EMAIL_C', 'SENSITIVE_DOC_C')
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
                (10, :tenant_a, 1, '2026-05-01', '2026-05-31', 5, 2026, 'loja'),
                (11, :tenant_a, 1, '2026-05-01', '2026-05-31', 5, 2026, 'loja'),
                (12, :tenant_a, 1, '2026-05-01', '2026-05-31', 5, 2026, 'online'),
                (13, :tenant_a, 1, '2026-06-01', '2026-06-30', 6, 2026, 'loja'),
                (14, :tenant_b, 2, '2026-05-01', '2026-05-31', 5, 2026, 'loja')
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
                (100, :tenant_a, 1, '2026-05-01', '2026-05-31', 5, 2026, 'loja', 1000),
                (101, :tenant_a, 1, '2026-05-01', '2026-05-31', 5, 2026, 'marketplace', 1000),
                (102, :tenant_a, 3, '2026-05-01', '2026-05-31', 5, 2026, 'loja', 1000),
                (103, :tenant_b, 1, '2026-05-01', '2026-05-31', 5, 2026, 'loja', 1000),
                (104, :tenant_a, 1, '2026-06-15', '2026-06-30', 6, 2026, 'loja', 1000),
                (105, :tenant_a, 1, '2026-07-01', '2026-07-31', 7, 2026, 'loja', 1000),
                (106, :tenant_a, 999, '2026-08-01', '2026-08-31', 8, 2026, 'loja', 1000),
                (107, :tenant_b, 2, '2026-05-01', '2026-05-31', 5, 2026, 'loja', 1000)
            """
        ),
        {"tenant_a": TENANT_A, "tenant_b": TENANT_B},
    )


def test_diagnostico_classifica_vinculos_e_causas():
    db = _session()

    relatorio = analisar_dre_detalhe_canais_vinculo(db)

    assert relatorio["resumo"]["dre_detalhe_canais_total"] == 8
    assert relatorio["resumo"]["dre_periodos_total"] == 5
    assert relatorio["resumo"]["vinculo_completo_univoco"] == 1
    assert relatorio["resumo"]["vinculo_completo_ambiguo"] == 1
    assert relatorio["resumo"]["sem_vinculo_completo"] == 6
    assert relatorio["resumo"]["classificacao"] == "ligacao_parcial_ou_ambigua"

    causas = relatorio["causas_sem_vinculo"]
    assert causas["canal_nao_bate"] == 1
    assert causas["usuario_id_nao_bate"] == 2
    assert causas["tenant_id_nao_bate"] == 1
    assert causas["data_inicio_data_fim_nao_batem"] == 2
    assert causas["mes_ano_equivalente_datas_diferentes"] == 1
    assert causas["usuario_inexistente"] == 1
    assert causas["usuario_tenant_diferente_do_detalhe"] == 1
    assert causas["vinculo_ambiguo"] == 1


def test_diagnostico_gera_amostras_agregadas_sem_ids_completos():
    db = _session()

    relatorio = analisar_dre_detalhe_canais_vinculo(db)
    amostras = relatorio["amostras_agregadas_sem_vinculo"]

    assert amostras
    assert all("tenant_ref" in item for item in amostras)
    assert all("usuario_ref" in item for item in amostras)
    assert all(TENANT_A not in json.dumps(item) for item in amostras)
    assert all(TENANT_B not in json.dumps(item) for item in amostras)


def test_diagnostico_nao_expoe_dados_sensiveis():
    db = _session()

    relatorio = analisar_dre_detalhe_canais_vinculo(db)
    serializado = json.dumps(relatorio, ensure_ascii=False).lower()

    assert "sensitive_name" not in serializado
    assert "sensitive_email" not in serializado
    assert "sensitive_doc" not in serializado
    assert TENANT_A not in serializado
    assert TENANT_B not in serializado
    assert "1000" not in serializado


def test_diagnostico_nao_altera_dados():
    db = _session()
    antes = db.execute(text("SELECT COUNT(*) FROM dre_detalhe_canais")).scalar()

    analisar_dre_detalhe_canais_vinculo(db)

    depois = db.execute(text("SELECT COUNT(*) FROM dre_detalhe_canais")).scalar()
    assert depois == antes
