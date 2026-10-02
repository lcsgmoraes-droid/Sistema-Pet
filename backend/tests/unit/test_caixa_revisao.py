from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.caixa import revisao


class _Query:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *args):
        return self

    def all(self):
        return self.rows


class _Session:
    def __init__(self, rows=()):
        self.rows = rows

    def query(self, model):
        return _Query(self.rows)


def _caixa():
    return SimpleNamespace(
        id=12, status="fechado",
        data_abertura=datetime(2026, 10, 1, 8, 0),
        data_fechamento=datetime(2026, 10, 1, 20, 0),
        valor_abertura=100.0, valor_informado=170.0,
        valor_esperado=100.0, diferenca=70.0,
    )


def test_revisao_valida_caixa_fechado_sem_afetar_caixa_atual(monkeypatch):
    caixa = _caixa()
    monkeypatch.setattr(revisao, "buscar_caixa_acessivel", lambda *args, **kwargs: (caixa, False))
    monkeypatch.setattr(revisao, "now_brasilia", lambda: datetime(2026, 10, 2, 12, 0))

    resultado = revisao.validar_revisao_caixa(
        _Session(), caixa_id=12, data_ocorrencia=datetime(2026, 10, 1, 13, 0),
        motivo="Pagamento esquecido", usuario=SimpleNamespace(id=4, is_admin=True),
        tenant_id="empresa-a",
    )

    assert resultado is caixa
    assert caixa.status == "fechado"


@pytest.mark.parametrize(
    "usuario,data_ocorrencia,motivo,codigo",
    [
        (SimpleNamespace(id=4, is_admin=False), datetime(2026, 10, 1, 13), "Pagamento esquecido", 403),
        (SimpleNamespace(id=4, is_admin=True), datetime(2026, 10, 1, 21), "Pagamento esquecido", 400),
        (SimpleNamespace(id=4, is_admin=True), datetime(2026, 10, 1, 13), "curto", 400),
    ],
)
def test_revisao_bloqueia_permissao_data_e_motivo(
    monkeypatch, usuario, data_ocorrencia, motivo, codigo
):
    monkeypatch.setattr(revisao, "buscar_caixa_acessivel", lambda *args, **kwargs: (_caixa(), False))
    monkeypatch.setattr(revisao, "now_brasilia", lambda: datetime(2026, 10, 2, 12, 0))
    with pytest.raises(HTTPException) as erro:
        revisao.validar_revisao_caixa(
            _Session(), caixa_id=12, data_ocorrencia=data_ocorrencia,
            motivo=motivo, usuario=usuario, tenant_id="empresa-a",
        )
    assert erro.value.status_code == codigo


def test_recalculo_considera_dinheiro_e_preserva_valor_contado():
    caixa = _caixa()
    movimentos = [
        SimpleNamespace(tipo="venda", forma_pagamento="Dinheiro", valor=70.0),
        SimpleNamespace(tipo="venda", forma_pagamento="PIX", valor=25.0),
    ]

    revisao.recalcular_fechamento_revisado(
        _Session(movimentos), caixa=caixa, tenant_id="empresa-a"
    )

    assert caixa.status == "fechado"
    assert caixa.valor_informado == 170.0
    assert caixa.valor_esperado == 170.0
    assert caixa.diferenca == 0.0
