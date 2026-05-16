from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.routes.modulos_routes import (
    MODULOS_BETA_PUBLICOS,
    MODULOS_FORA_DA_OFERTA_PUBLICA,
    MODULOS_PREMIUM,
    _normalizar_modulos_ativos,
    _raw_modulos_ativos_valido,
    _resolver_modulos_ativos,
)


def test_plano_legado_free_continua_liberado_para_nao_quebrar_tenants_existentes():
    ativos = _resolver_modulos_ativos(
        raw_modulos=None,
        assinaturas_ativas=[],
        agora=datetime(2026, 4, 24, tzinfo=timezone.utc),
        plano="free",
    )

    assert set(ativos) >= set(MODULOS_PREMIUM)


def test_plano_basico_nao_libera_extras_sem_assinatura_ou_modulo_expresso():
    ativos = _resolver_modulos_ativos(
        raw_modulos=None,
        assinaturas_ativas=[],
        agora=datetime(2026, 5, 13, tzinfo=timezone.utc),
        plano="basico",
    )

    assert ativos == []


def test_bling_nao_entra_na_vitrine_beta_publica():
    assert "bling" in MODULOS_PREMIUM
    assert "bling" in MODULOS_FORA_DA_OFERTA_PUBLICA
    assert "bling" not in MODULOS_BETA_PUBLICOS


def test_plano_basico_preserva_assinaturas_ativas_e_ignora_expiradas():
    agora = datetime(2026, 4, 24, tzinfo=timezone.utc)
    assinaturas = [
        SimpleNamespace(modulo="compras", data_fim=None),
        SimpleNamespace(modulo="expirado", data_fim=agora - timedelta(days=1)),
    ]

    ativos = _resolver_modulos_ativos(
        raw_modulos='["entregas"]',
        assinaturas_ativas=assinaturas,
        agora=agora,
        plano="basico",
    )

    assert "entregas" in ativos
    assert "compras" in ativos
    assert "expirado" not in ativos


def test_plano_completo_libera_todos_modulos_controlados():
    ativos = _resolver_modulos_ativos(
        raw_modulos=None,
        assinaturas_ativas=[],
        agora=datetime(2026, 5, 13, tzinfo=timezone.utc),
        plano="enterprise",
    )

    assert set(ativos) == set(MODULOS_PREMIUM)


def test_modulos_ativos_json_vazio_e_valido():
    assert _raw_modulos_ativos_valido("[]") is True
    assert _normalizar_modulos_ativos('["entregas", 123, "campanhas"]') == [
        "entregas",
        "campanhas",
    ]
