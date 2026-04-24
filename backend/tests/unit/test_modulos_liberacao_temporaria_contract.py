from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.routes.modulos_routes import (
    MODULOS_PREMIUM,
    _normalizar_modulos_ativos,
    _raw_modulos_ativos_valido,
    _resolver_modulos_ativos,
)


def test_modulos_premium_ficam_liberados_enquanto_pacotes_nao_existem():
    ativos = _resolver_modulos_ativos(
        raw_modulos=None,
        assinaturas_ativas=[],
        agora=datetime(2026, 4, 24, tzinfo=timezone.utc),
    )

    assert set(ativos) >= set(MODULOS_PREMIUM)


def test_modulos_preserva_assinaturas_ativas_e_ignora_expiradas():
    agora = datetime(2026, 4, 24, tzinfo=timezone.utc)
    assinaturas = [
        SimpleNamespace(modulo="modulo_futuro", data_fim=None),
        SimpleNamespace(modulo="expirado", data_fim=agora - timedelta(days=1)),
    ]

    ativos = _resolver_modulos_ativos(
        raw_modulos='["entregas"]',
        assinaturas_ativas=assinaturas,
        agora=agora,
    )

    assert "entregas" in ativos
    assert "modulo_futuro" in ativos
    assert "expirado" not in ativos


def test_modulos_ativos_json_vazio_e_valido():
    assert _raw_modulos_ativos_valido("[]") is True
    assert _normalizar_modulos_ativos('["entregas", 123, "campanhas"]') == [
        "entregas",
        "campanhas",
    ]
