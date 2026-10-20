"""Importados ficam no historico sem afetar a DRE ou outros tenants."""

import json
import re
from contextlib import nullcontext

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.financeiro.sistema_antigo_sem_dre import retirar_sistema_antigo_dre
from app.scripts import retirar_sistema_antigo_dre as cli
from app.utils.tenant_safe_sql import TenantSafeSQLError


TENANT_ALVO = "11111111-1111-1111-1111-111111111111"
TENANT_OUTRO = "22222222-2222-2222-2222-222222222222"


@pytest.fixture
def historico_db():
    engine = create_engine("sqlite://", poolclass=StaticPool)
    db = sessionmaker(bind=engine)()
    db.execute(text("CREATE TABLE tenants (id TEXT PRIMARY KEY, name TEXT NOT NULL)"))
    db.execute(
        text(
            "INSERT INTO tenants VALUES (:alvo, 'Tecno Agropet'), (:outro, 'Outra loja')"
        ),
        {"alvo": TENANT_ALVO, "outro": TENANT_OUTRO},
    )
    db.execute(
        text(
            """
            CREATE TABLE contas_pagar (
                id INTEGER PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                descricao TEXT NOT NULL,
                valor_final NUMERIC(10, 2) NOT NULL,
                status TEXT NOT NULL,
                data_emissao TEXT NOT NULL,
                data_vencimento TEXT NOT NULL,
                valor_pago NUMERIC(10, 2) NOT NULL,
                observacoes TEXT,
                afeta_dre BOOLEAN NOT NULL,
                dre_subcategoria_id INTEGER
            )
            """
        )
    )
    db.execute(
        text(
            """
            INSERT INTO contas_pagar VALUES
              (10, :alvo, 'Aluguel (sistema antigo)', 100, 'pago',
               '2025-01-01', '2025-02-01', 100, 'Importacao preservada', 1, 5),
              (11, :alvo, 'Telefonia (SISTEMA ANTIGO)', 50, 'pendente',
               '2026-10-05', '2028-01-01', 0, 'Parcela futura', 1, NULL),
              (12, :alvo, 'Energia (sistema antigo)', 25, 'cancelado',
               '2024-01-01', '2024-02-01', 0, 'Cancelamento preservado', 1, 9),
              (13, :alvo, 'Agua (sistema antigo)', 40, 'pago',
               '2026-10-05', '2026-10-10', 40, 'Ja excluida da DRE', 0, NULL),
              (14, :alvo, 'Despesa normal CorePet', 30, 'pago',
               '2026-10-05', '2026-10-10', 30, 'Lancamento atual', 1, 8),
              (15, :alvo, 'Manutencao de sistema antigo sem marcador', 70, 'pago',
               '2026-10-05', '2026-10-10', 70, 'Nao e importacao identificada', 1, 6),
              (16, :alvo, 'Software (sistema antigo)', 20, 'parcial',
               '2026-10-05', '2026-10-10', 5, 'Categoria antiga remanescente', 0, 4),
              (20, :outro, 'Aluguel (sistema antigo)', 90, 'pago',
               '2026-10-05', '2026-10-10', 90, 'Outro tenant preservado', 1, 5)
            """
        ),
        {"alvo": TENANT_ALVO, "outro": TENANT_OUTRO},
    )
    db.commit()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def _snapshot(db):
    return {
        row["id"]: dict(row)
        for row in db.execute(text("SELECT * FROM contas_pagar ORDER BY id")).mappings()
    }


def _previa(db, **kwargs):
    return retirar_sistema_antigo_dre(db, tenant_id=TENANT_ALVO, **kwargs)


def test_previa_identifica_marcacao_em_qualquer_data_sem_alterar_historico(
    historico_db,
):
    antes = _snapshot(historico_db)

    previa = _previa(historico_db)

    assert previa["ok"] is True
    assert previa["dry_run"] is True
    assert previa["applied"] is False
    assert previa["tenant_id"] == TENANT_ALVO
    assert previa["tenant_nome"] == "Tecno Agropet"
    assert previa["resumo"]["contas_marcadas"] == 5
    assert previa["resumo"]["contas_a_alterar"] == 4
    assert previa["resumo"]["valor_total"] == "195.00"
    assert {item["id"] for item in previa["contas_pagar"]} == {10, 11, 12, 16}
    assert re.fullmatch(r"[0-9a-f]{64}", previa["plano_hash"])
    assert _snapshot(historico_db) == antes
    assert _previa(historico_db)["plano_hash"] == previa["plano_hash"]


def test_aplicar_altera_apenas_flags_das_contas_marcadas_e_e_idempotente(historico_db):
    antes = _snapshot(historico_db)
    previa = _previa(historico_db)

    aplicado = _previa(
        historico_db, apply_changes=True, plano_hash=previa["plano_hash"]
    )

    assert aplicado["ok"] is True
    assert aplicado["applied"] is True
    assert aplicado["dry_run"] is False
    assert aplicado["plano_hash"] == previa["plano_hash"]
    depois = _snapshot(historico_db)
    assert depois.keys() == antes.keys()
    for conta_id, original in antes.items():
        esperado = dict(original)
        if conta_id in {10, 11, 12, 16}:
            esperado.update(afeta_dre=0, dre_subcategoria_id=None)
        assert depois[conta_id] == esperado

    nova_previa = _previa(historico_db)
    assert nova_previa["resumo"]["contas_marcadas"] == 5
    assert nova_previa["resumo"]["contas_a_alterar"] == 0
    assert nova_previa["resumo"]["valor_total"] == "0.00"
    assert nova_previa["contas_pagar"] == []
    _previa(historico_db, apply_changes=True, plano_hash=nova_previa["plano_hash"])
    assert _snapshot(historico_db) == depois


@pytest.mark.parametrize("plano_hash", [None, "", "a" * 64])
def test_aplicar_exige_hash_da_previa_atual(historico_db, plano_hash):
    antes = _snapshot(historico_db)
    with pytest.raises(ValueError):
        _previa(historico_db, apply_changes=True, plano_hash=plano_hash)
    assert _snapshot(historico_db) == antes


def test_mudanca_apos_previa_bloqueia_aplicacao_inteira(historico_db):
    previa = _previa(historico_db)
    historico_db.execute(text("UPDATE contas_pagar SET valor_final = 51 WHERE id = 11"))
    historico_db.commit()
    antes = _snapshot(historico_db)

    with pytest.raises(ValueError):
        _previa(historico_db, apply_changes=True, plano_hash=previa["plano_hash"])

    assert _snapshot(historico_db) == antes


@pytest.mark.parametrize(
    "tenant_id,tenant_nome",
    [
        (TENANT_OUTRO, "Tecno Agropet"),
        (TENANT_ALVO, "Nome errado"),
        ("33333333-3333-3333-3333-333333333333", "Tecno Agropet"),
        ("nao-e-uuid", "Tecno Agropet"),
        ("", "Tecno Agropet"),
    ],
)
def test_identidade_incorreta_do_tenant_nao_altera_contas(
    historico_db, tenant_id, tenant_nome
):
    antes = _snapshot(historico_db)
    with pytest.raises(ValueError):
        retirar_sistema_antigo_dre(
            historico_db, tenant_id=tenant_id, tenant_nome=tenant_nome
        )
    assert _snapshot(historico_db) == antes


def test_erro_no_meio_da_aplicacao_reverte_todas_as_contas(historico_db):
    previa = _previa(historico_db)
    historico_db.execute(
        text(
            """
            CREATE TRIGGER falha_segunda_conta
            BEFORE UPDATE ON contas_pagar
            WHEN NEW.id = 11
            BEGIN
                SELECT RAISE(ABORT, 'falha simulada');
            END
            """
        )
    )
    historico_db.commit()
    antes = _snapshot(historico_db)

    with pytest.raises(TenantSafeSQLError, match="falha simulada"):
        _previa(historico_db, apply_changes=True, plano_hash=previa["plano_hash"])

    assert _snapshot(historico_db) == antes


def test_cli_previa_emite_json_sem_alterar_contas(historico_db, monkeypatch, capsys):
    antes = _snapshot(historico_db)
    monkeypatch.setattr(cli, "SessionLocal", lambda: nullcontext(historico_db))

    codigo = cli.main(["--tenant-id", TENANT_ALVO])

    report = json.loads(capsys.readouterr().out)
    assert codigo == 0
    assert report["dry_run"] is True
    assert report["resumo"]["contas_a_alterar"] == 4
    assert _snapshot(historico_db) == antes


@pytest.mark.parametrize(
    "extra_args,erro",
    [([], "--plano-hash"), (["--plano-hash", "a" * 64], "--allow-production-apply")],
)
def test_cli_bloqueia_aplicar_sem_hash_ou_sem_override_de_producao(
    monkeypatch, capsys, extra_args, erro
):
    monkeypatch.setenv("APP_ENV", "production")

    def banco_nao_deve_ser_aberto():
        raise AssertionError("Validacao deve ocorrer antes de abrir o banco")

    monkeypatch.setattr(cli, "SessionLocal", banco_nao_deve_ser_aberto)

    codigo = cli.main(["--tenant-id", TENANT_ALVO, "--apply", *extra_args])

    report = json.loads(capsys.readouterr().err)
    assert codigo == 1
    assert report["ok"] is False
    assert erro in report["error"]
