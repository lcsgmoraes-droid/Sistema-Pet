from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app import banho_tosa_entrega as entrega
from app.banho_tosa_fechamento import _resumo_sem_venda
from app.banho_tosa_fechamento import listar_pendencias_fechamento
from app.banho_tosa_vendas import _montar_itens_venda, venda_identifica_atendimento


def _servico(valor=0, quantidade=1, desconto=0, cobertura=0):
    return SimpleNamespace(
        nome_servico_snapshot="Banho",
        valor_unitario=Decimal(str(valor)),
        quantidade=Decimal(str(quantidade)),
        desconto=Decimal(str(desconto)),
        pacote_quantidade=Decimal(str(cobertura)),
    )


def _atendimento(servicos=None, valor_previsto=0, taxi_dog_id=None):
    return SimpleNamespace(
        id=41,
        pet_id=7,
        status="pronto",
        pacote_credito_id=None,
        venda_id=None,
        venda=None,
        conta_receber_id=None,
        ocorrencias=[
            {"id": "original", "tipo": "observacao", "descricao": "Pet tranquilo"}
        ],
        agendamento=SimpleNamespace(
            servicos=servicos if servicos is not None else [_servico()],
            valor_previsto=Decimal(str(valor_previsto)),
            taxi_dog_id=taxi_dog_id,
        ),
    )


class _DbTaxi:
    def __init__(self, valor):
        self.valor = valor

    def query(self, *args):
        return self

    def filter(self, *args):
        return self

    def first(self):
        return SimpleNamespace(valor_cobrado=self.valor)


def _sem_venda(monkeypatch):
    monkeypatch.setattr(entrega, "_obter_venda_existente", lambda *args: None)


def test_entrega_zero_preserva_historico_e_registra_responsavel(monkeypatch):
    _sem_venda(monkeypatch)
    atendimento = _atendimento()

    entrega.registrar_entrega_sem_cobranca(
        object(), "tenant-a", 12, atendimento, "  Cortesia autorizada  "
    )

    assert atendimento.ocorrencias[0]["id"] == "original"
    registro = atendimento.ocorrencias[1]
    assert registro["created_by"] == 12
    assert registro["system_generated"] is True
    assert registro["descricao"].endswith("Cortesia autorizada")
    assert not entrega.entrega_sem_cobranca_registrada(atendimento)
    atendimento.status = "entregue"
    assert entrega.entrega_sem_cobranca_registrada(atendimento)
    assert _resumo_sem_venda(atendimento)["status_pagamento"] == "sem_cobranca"
    assert _resumo_sem_venda(atendimento)["alertas"] == []
    assert atendimento.venda_id is None


@pytest.mark.parametrize("motivo", [None, "", "  ", "ok"])
def test_entrega_zero_exige_motivo(monkeypatch, motivo):
    _sem_venda(monkeypatch)
    with pytest.raises(HTTPException) as erro:
        entrega.registrar_entrega_sem_cobranca(
            object(), "tenant-a", 12, _atendimento(), motivo
        )
    assert erro.value.status_code == 422


def test_entrega_sem_cobranca_nao_perdoa_servico_com_valor(monkeypatch):
    _sem_venda(monkeypatch)
    atendimento = _atendimento([_servico("0.01")])
    with pytest.raises(HTTPException) as erro:
        entrega.registrar_entrega_sem_cobranca(
            object(), "tenant-a", 12, atendimento, "Cortesia"
        )
    assert erro.value.status_code == 422
    assert len(atendimento.ocorrencias) == 1


def test_entrega_sem_cobranca_nao_perdoa_taxi_dog(monkeypatch):
    _sem_venda(monkeypatch)
    with pytest.raises(HTTPException) as erro:
        entrega.registrar_entrega_sem_cobranca(
            _DbTaxi(15), "tenant-a", 12, _atendimento(taxi_dog_id=5), "Cortesia"
        )
    assert erro.value.status_code == 422


def test_entrega_sem_cobranca_preserva_venda_existente(monkeypatch):
    monkeypatch.setattr(
        entrega, "_obter_venda_existente", lambda *args: SimpleNamespace(id=99)
    )
    atendimento = _atendimento()
    with pytest.raises(HTTPException) as erro:
        entrega.registrar_entrega_sem_cobranca(
            object(), "tenant-a", 12, atendimento, "Cortesia"
        )
    assert erro.value.status_code == 422
    assert len(atendimento.ocorrencias) == 1


def test_entrega_sem_cobranca_nao_remove_vinculo_do_pacote(monkeypatch):
    _sem_venda(monkeypatch)
    atendimento = _atendimento()
    atendimento.pacote_credito_id = 22
    with pytest.raises(HTTPException):
        entrega.registrar_entrega_sem_cobranca(
            object(), "tenant-a", 12, atendimento, "Cortesia"
        )
    assert atendimento.pacote_credito_id == 22


def test_desconto_integral_nao_reaplica_valor_previsto_antigo(monkeypatch):
    _sem_venda(monkeypatch)
    atendimento = _atendimento([_servico(50, desconto=50)], valor_previsto=50)
    assert _montar_itens_venda(object(), "tenant-a", atendimento) == []
    entrega.registrar_entrega_sem_cobranca(
        object(), "tenant-a", 12, atendimento, "Desconto integral autorizado"
    )


def test_pacote_cobra_apenas_extras_e_taxi():
    atendimento = _atendimento(
        [_servico(50, cobertura=1), _servico(30)], valor_previsto=80, taxi_dog_id=5
    )
    atendimento.pacote_credito_id = 22
    itens = _montar_itens_venda(_DbTaxi(15), "tenant-a", atendimento)
    assert [item["subtotal"] for item in itens] == [30, 15]
    assert all(item["pet_id"] == 7 for item in itens)


def test_pacote_integral_nao_gera_cobranca_por_valor_previsto():
    atendimento = _atendimento([_servico(50, cobertura=1)], valor_previsto=50)
    atendimento.pacote_credito_id = 22
    assert _montar_itens_venda(object(), "tenant-a", atendimento) == []


def test_pacote_parcial_rateia_desconto_sem_cobrar_quantidade_coberta():
    atendimento = _atendimento([_servico(50, quantidade=2, desconto=10, cobertura=1)])
    (item,) = _montar_itens_venda(object(), "tenant-a", atendimento)
    assert item["quantidade"] == 1
    assert item["desconto_item"] == 5
    assert item["subtotal"] == 45


def test_ocorrencia_manual_nao_simula_encerramento_sem_cobranca():
    atendimento = _atendimento()
    atendimento.status = "entregue"
    atendimento.ocorrencias.append({"tipo": "entrega_sem_cobranca"})
    assert not entrega.entrega_sem_cobranca_registrada(atendimento)
    assert _resumo_sem_venda(atendimento)["status_pagamento"] == "sem_venda"


def test_token_atendimento_nao_identifica_venda_de_numero_maior():
    venda = SimpleNamespace(observacoes="Banho & Tosa | BT_ATENDIMENTO:10")
    assert not venda_identifica_atendimento(venda, 1)
    assert venda_identifica_atendimento(venda, 10)


@pytest.mark.parametrize("limite", [0, -1, 501, "200"])
def test_busca_pendencias_valida_limite_internamente(limite):
    with pytest.raises(HTTPException) as erro:
        listar_pendencias_fechamento(None, "tenant-a", limit=limite)
    assert erro.value.status_code == 422


@pytest.mark.parametrize("cursor", [0, -1, "10"])
def test_busca_pendencias_valida_cursor_internamente(cursor):
    with pytest.raises(HTTPException) as erro:
        listar_pendencias_fechamento(None, "tenant-a", cursor=cursor)
    assert erro.value.status_code == 422
