"""Etapa 0.4: telefone maior na conversa e conferencia dos vinculos antigos."""

from pathlib import Path
from types import SimpleNamespace

from app.whatsapp import customer_lookup as lookup
from app.whatsapp.models import WhatsAppSession
from app.whatsapp.models_handoff import WhatsAppHandoff
from scripts.conferir_vinculo_sessoes_whatsapp import classificar_vinculo

MIGRACAO = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "zzzzk20261022a1_whatsapp_telefone_40_caracteres.py"
)


def test_telefone_da_conversa_e_do_atendimento_comporta_40_caracteres():
    assert WhatsAppSession.__table__.c.phone_number.type.length == 40
    assert WhatsAppHandoff.__table__.c.phone_number.type.length == 40


def test_migracao_amplia_as_duas_tabelas_e_encadeia_no_ultimo_head():
    texto = MIGRACAO.read_text(encoding="utf-8")

    assert 'revision = "zzzzk20261022a1"' in texto
    assert 'down_revision = "zzzzj20261019a1"' in texto
    assert "whatsapp_ia_sessions" in texto and "whatsapp_handoffs" in texto
    assert "sa.String(40)" in texto


def _res(situacao, ids=()):
    return lookup.ResolucaoTutor(
        situacao, ids[0] if len(ids) == 1 else None, tuple(ids)
    )


def test_vinculo_com_telefone_correspondente_esta_ok():
    cadastro = SimpleNamespace(celular="(11) 99999-8888", telefone=None)

    assert classificar_vinculo(5, "5511999998888", cadastro, _res("nenhum")) == "ok"


def test_vinculo_com_telefone_diferente_e_duvidoso():
    cadastro = SimpleNamespace(celular="(21) 98888-7777", telefone=None)

    assert (
        classificar_vinculo(5, "5511999998888", cadastro, _res("nenhum")) == "duvidoso"
    )


def test_vinculo_para_cadastro_inexistente_e_duvidoso():
    assert classificar_vinculo(5, "5511999998888", None, _res("nenhum")) == "duvidoso"


def test_sem_vinculo_classifica_pela_regra_atual():
    assert (
        classificar_vinculo(None, "5511999998888", None, _res("unico", (3,)))
        == "sem_vinculo_e_unico"
    )
    assert (
        classificar_vinculo(None, "5511999998888", None, _res("ambiguo", (3, 4)))
        == "sem_vinculo_ambiguo"
    )
    assert (
        classificar_vinculo(None, "5511999998888", None, _res("nenhum"))
        == "sem_vinculo"
    )
