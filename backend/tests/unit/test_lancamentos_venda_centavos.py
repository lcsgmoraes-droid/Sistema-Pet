"""O espelho financeiro da venda conserva cada centavo recebido e pendente."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.financeiro.contas_receber_service import ContasReceberService


def _lancamento(*, valor, documento="VENDA-42", status="previsto", ident=10):
    return SimpleNamespace(
        id=ident,
        valor=Decimal(valor),
        documento=documento,
        status=status,
        descricao="Venda TESTE-42",
        data_lancamento=date(2026, 10, 14),
        categoria_id=None,
        fornecedor_cliente="Cliente",
    )


def _db_com_consultas(*resultados):
    db = MagicMock()
    consulta = db.query.return_value
    consulta.filter.return_value = consulta
    consulta.all.side_effect = resultados
    inseridos = []

    def adicionar(lancamento):
        if lancamento.id is None:
            lancamento.id = 100 + len(inseridos)
        if all(item is not lancamento for item in inseridos):
            inseridos.append(lancamento)

    db.add.side_effect = adicionar
    return db, inseridos


def _atualizar(db, *, total, recebido):
    return ContasReceberService.atualizar_lancamentos_venda(
        venda_id=42,
        venda_numero="TESTE-42",
        total_venda=total,
        total_recebido=recebido,
        user_id=7,
        tenant_id=uuid4(),
        db=db,
    )


@pytest.mark.parametrize(
    "total, recebido, saldo",
    [(1.0, 0.99, "0.01"), (1.0, 0.01, "0.99")],
)
def test_espelho_registra_um_centavo_recebido_ou_pendente(total, recebido, saldo):
    previsto = _lancamento(valor=str(total))
    db, inseridos = _db_com_consultas([previsto], [])

    resultado = _atualizar(db, total=total, recebido=recebido)

    assert resultado["status"] == "parcialmente_pago"
    assert previsto.status == "previsto"
    assert previsto.valor == Decimal(saldo)
    realizados = [item for item in inseridos if item.status == "realizado"]
    assert len(realizados) == 1
    assert realizados[0].valor == Decimal(str(recebido))
    assert realizados[0].valor + previsto.valor == Decimal(str(total))


def test_complemento_de_um_centavo_realiza_previsao_do_saldo():
    previsto = _lancamento(valor="0.01")
    db, inseridos = _db_com_consultas([previsto], [])

    resultado = _atualizar(db, total=1.0, recebido=1.0)

    assert resultado["status"] == "totalmente_pago"
    assert resultado["lancamentos_criados"] == []
    assert previsto.status == "realizado"
    assert previsto.valor == Decimal("0.01")
    assert inseridos == [previsto]


def test_reconstroi_previsao_de_um_centavo_sem_apagar_historico():
    realizado = _lancamento(
        valor="0.99", documento="VENDA-42-REALIZADO", status="realizado"
    )
    db, inseridos = _db_com_consultas([], [], [realizado])

    resultado = _atualizar(db, total=1.0, recebido=0.99)

    assert resultado["status"] == "parcialmente_pago"
    previstos = [item for item in inseridos if item.status == "previsto"]
    assert len(previstos) == 1
    assert previstos[0].valor == Decimal("0.01")
    assert previstos[0].documento == "VENDA-42"
    assert realizado.status == "realizado"
    assert realizado.valor == Decimal("0.99")


def test_decimal_do_total_evitar_residuo_de_float_no_saldo():
    previsto = _lancamento(valor="0.30")
    db, inseridos = _db_com_consultas([previsto], [])

    resultado = _atualizar(db, total=0.1 + 0.2, recebido=0.29)

    assert resultado["status"] == "parcialmente_pago"
    assert previsto.valor == Decimal("0.01")
    assert next(
        item for item in inseridos if item.status == "realizado"
    ).valor == Decimal("0.29")


def test_reducao_do_total_preserva_realizado_historico_maior():
    realizado = _lancamento(valor="1.00", status="realizado")
    db, inseridos = _db_com_consultas([], [], [realizado])

    resultado = _atualizar(db, total=0.99, recebido=1.0)

    assert resultado["status"] == "nenhum"
    assert inseridos == []
    assert realizado.status == "realizado"
    assert realizado.valor == Decimal("1.00")
