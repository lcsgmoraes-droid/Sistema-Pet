"""Etapa 1.1/1.3 do CRM: o modulo existe, nasce fora da oferta publica e tem permissoes."""

from pathlib import Path

from app.routes import modulos_routes as modulos
from app.services.default_roles_service import DEFAULT_TENANT_ROLES

RAIZ = Path(__file__).resolve().parents[3]
PERMISSOES_CRM = {
    "crm.visualizar",
    "crm.atender",
    "crm.leads",
    "crm.configurar",
    "crm.todas_lojas",
}


def test_crm_e_modulo_controlado_e_fora_da_oferta_publica():
    assert "crm" in modulos.MODULOS_PREMIUM
    assert "crm" in modulos.MODULOS_FORA_DA_OFERTA_PUBLICA
    assert "crm" in modulos.MODULOS_CONTRATACAO_SEPARADA


def test_crm_nao_entra_em_beta_trial_nem_planos_liberados():
    assert "crm" not in modulos.MODULOS_BETA_PUBLICOS
    assert "crm" not in modulos.MODULOS_TRIAL_COMPLETO
    assert "crm" not in (modulos.MODULOS_PREMIUM - modulos.MODULOS_CONTRATACAO_SEPARADA)


def test_perfil_gerente_padrao_recebe_as_permissoes_do_crm():
    assert PERMISSOES_CRM <= DEFAULT_TENANT_ROLES["Gerente"]
    assert not (PERMISSOES_CRM & DEFAULT_TENANT_ROLES["Caixa"])


def test_migracao_de_permissoes_encadeia_e_nao_bloqueia_ninguem():
    fonte = (
        RAIZ / "backend/alembic/versions/zzzzl20261022a1_permissoes_crm.py"
    ).read_text(encoding="utf-8")
    assert 'down_revision = "zzzzk20261022a1"' in fonte
    assert "ON CONFLICT (code) DO UPDATE" in fonte
    assert "NOT EXISTS" in fonte  # backfill idempotente
    for codigo in PERMISSOES_CRM:
        assert codigo in fonte


def test_frontend_registra_o_modulo_com_a_mesma_regra():
    ctx = (RAIZ / "frontend/src/contexts/ModulosContext.jsx").read_text(encoding="utf-8")
    assert '"crm",' in ctx
    assert '["bling", "fiscal", "crm"]' in ctx
    assert "  crm: {" in ctx
