import pytest
from fastapi import HTTPException

from app.produtos_routes import _normalizar_filtro_ativo_produtos
from app.vendas_routes import _normalizar_motivo_exclusao_venda


def test_normalizar_motivo_exclusao_venda_exige_justificativa():
    with pytest.raises(HTTPException) as exc:
        _normalizar_motivo_exclusao_venda("curto")

    assert exc.value.status_code == 400


def test_normalizar_motivo_exclusao_venda_remove_espacos():
    assert (
        _normalizar_motivo_exclusao_venda("  Cliente pediu cancelamento  ")
        == "Cliente pediu cancelamento"
    )


def test_normalizar_filtro_ativo_produtos_todos_remove_filtro_ativo():
    assert _normalizar_filtro_ativo_produtos(True, incluir_inativos=True) is None


def test_normalizar_filtro_ativo_produtos_preserva_ativos_e_inativos():
    assert _normalizar_filtro_ativo_produtos(True) is True
    assert _normalizar_filtro_ativo_produtos(False) is False
