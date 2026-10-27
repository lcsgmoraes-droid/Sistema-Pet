"""Etapa 1.4 do CRM: modelo de dados por loja, coerente com a migracao."""

import re
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from app.crm import models as crm
from app.db import Base

RAIZ = Path(__file__).resolve().parents[2]
MIGRACAO = RAIZ / "alembic/versions/zzzzm20261022a1_crm_modelo_de_dados.py"


def test_todas_as_tabelas_do_crm_sao_por_loja():
    assert len(crm.TABELAS_DO_CRM) == 8
    for nome in crm.TABELAS_DO_CRM:
        tabela = Base.metadata.tables[nome]
        assert nome.startswith("crm_")
        assert not tabela.c.tenant_id.nullable, nome
        assert tabela.c.tenant_id.index, nome


def test_migracao_cria_as_mesmas_tabelas_e_colunas_do_modelo():
    fonte = MIGRACAO.read_text(encoding="utf-8")
    assert "apply_tenant_rls" in fonte and "enable=True" in fonte
    for nome in crm.TABELAS_DO_CRM:
        trecho = fonte.split(f'"{nome}",\n        *_base')[1].split("op.create_table")[
            0
        ]
        for coluna in Base.metadata.tables[nome].c:
            if coluna.name in {"id", "tenant_id", "created_at", "updated_at"}:
                continue
            assert re.search(rf'"{coluna.name}"', trecho), (nome, coluna.name)


def test_indices_unicos_garantem_um_card_por_tutor_por_loja():
    indices = {i.name: i for i in Base.metadata.tables["crm_leads"].indexes}
    assert indices["uq_crm_leads_cliente"].unique
    assert indices["uq_crm_leads_telefone_sem_cadastro"].unique
    fonte = MIGRACAO.read_text(encoding="utf-8")
    assert "uq_crm_leads_cliente" in fonte
    assert "uq_crm_leads_telefone_sem_cadastro" in fonte


def test_migracao_continua_a_cadeia_com_uma_unica_cabeca():
    cfg = Config(str(RAIZ / "alembic.ini"))
    cfg.set_main_option("script_location", str(RAIZ / "alembic"))
    script = ScriptDirectory.from_config(cfg)

    assert len(script.get_heads()) == 1  # nunca duas pontas
    assert script.get_revision("zzzzm20261022a1").down_revision == "zzzzl20261022a1"


def test_tipos_de_coluna_do_funil():
    assert set(crm.TIPOS_DE_COLUNA) == {
        "entrada",
        "andamento",
        "concluido",
        "encerrado",
    }
