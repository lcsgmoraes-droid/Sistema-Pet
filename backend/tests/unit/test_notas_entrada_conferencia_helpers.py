import os
from types import SimpleNamespace

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"

from app.notas_entrada.conferencia import (  # noqa: E402
    _obter_acao_conferencia,
    _quantidades_conferencia_item,
    _serializar_conferencia_item,
    _status_conferencia_item,
)


def test_status_conferencia_identifica_falta_e_avaria():
    item = SimpleNamespace(
        quantidade=10,
        quantidade_conferida=7,
        quantidade_avariada=2,
        observacao_conferencia="  embalagem rasgada ",
        acao_sugerida="reposicao_fornecedor",
    )

    assert _quantidades_conferencia_item(item) == {
        "quantidade_nf": 10,
        "quantidade_conferida": 7,
        "quantidade_avariada": 2,
        "quantidade_faltante": 1,
    }
    assert _status_conferencia_item(item) == "falta_avaria"

    payload = _serializar_conferencia_item(item)
    assert payload["tem_divergencia"] is True
    assert payload["acao_sugerida"] == "reposicao_fornecedor"
    assert payload["observacao_conferencia"] == "embalagem rasgada"


def test_acao_conferencia_volta_para_sem_acao_quando_nao_tem_divergencia():
    assert _obter_acao_conferencia("nf_devolucao", tem_divergencia=False) == "sem_acao"
    assert (
        _obter_acao_conferencia("acao_invalida", tem_divergencia=True)
        == "contatar_fornecedor"
    )
