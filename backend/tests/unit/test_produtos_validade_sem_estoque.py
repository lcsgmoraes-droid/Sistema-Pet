import os
from datetime import datetime
from types import SimpleNamespace

import pytest

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL") or "sqlite:///./test.db"
os.environ["DEBUG"] = "false"

from app.produtos import listagem  # noqa: E402
from app.produtos_models import Produto  # noqa: E402


class FakeQuery:
    def filter(self, *args):
        return self

    def all(self):
        return []


class FakeDb:
    def query(self, *args):
        return FakeQuery()


def produto_com_validade(**alteracoes):
    dados = {
        "id": 10,
        "tenant_id": "tenant-1",
        "categoria": None,
        "tipo_produto": "SIMPLES",
        "tipo_kit": None,
        "controlar_estoque": True,
        "controle_lote": False,
        "estoque_atual": 5,
        "estoque_virtual": None,
        "estoque_reservado": 0,
        "data_validade": datetime(2027, 1, 21),
        "lotes": [],
        "preco_venda": 20,
        "preco_promocional": None,
        "promocao_inicio": None,
        "promocao_fim": None,
    }
    dados.update(alteracoes)
    return SimpleNamespace(**dados)


def lote_com_validade(*, saldo=1, validade=None, status="ativo"):
    return SimpleNamespace(
        status=status,
        quantidade_disponivel=saldo,
        data_validade=validade,
    )


def validade_da_property(produto):
    return Produto.validade_proxima.fget(produto)


@pytest.mark.parametrize("estoque", [0, -2])
def test_validade_cadastrada_nao_aparece_sem_estoque_fisico(estoque):
    produto = produto_com_validade(estoque_atual=estoque)

    assert validade_da_property(produto) is None


@pytest.mark.parametrize("estoque", [0, -2])
def test_lote_com_saldo_antigo_nao_expoe_validade_do_produto_sem_estoque(estoque):
    produto = produto_com_validade(
        estoque_atual=estoque,
        controle_lote=True,
        lotes=[lote_com_validade(saldo=2, validade=datetime(2027, 1, 21))],
    )

    assert validade_da_property(produto) is None


def test_controle_lote_sem_lotes_nao_recupera_data_antiga_do_cadastro():
    produto = produto_com_validade(controle_lote=True)

    assert validade_da_property(produto) is None


def test_validade_mais_proxima_ignora_lote_zerado_e_usa_lote_com_saldo():
    validade_antiga = datetime(2026, 11, 1)
    validade_com_saldo = datetime(2027, 2, 1)
    produto = produto_com_validade(
        controle_lote=True,
        lotes=[
            lote_com_validade(saldo=0, validade=validade_antiga),
            lote_com_validade(saldo=3, validade=validade_com_saldo),
        ],
    )

    assert validade_da_property(produto) == validade_com_saldo


def test_lotes_sem_data_ou_inativos_nao_participam_da_validade_mais_proxima():
    validade_com_saldo = datetime(2027, 2, 1)
    produto = produto_com_validade(
        controle_lote=True,
        lotes=[
            lote_com_validade(saldo=2),
            lote_com_validade(
                saldo=1, validade=datetime(2026, 1, 1), status="excluido"
            ),
            lote_com_validade(saldo=3, validade=validade_com_saldo),
        ],
    )

    assert validade_da_property(produto) == validade_com_saldo


def test_apenas_lotes_sem_validade_nao_recuperam_data_antiga_do_cadastro():
    produto = produto_com_validade(
        controle_lote=True,
        lotes=[lote_com_validade(saldo=2)],
    )

    assert validade_da_property(produto) is None


def test_produto_sem_controle_lote_e_com_estoque_preserva_validade_cadastrada():
    produto = produto_com_validade()

    assert validade_da_property(produto) == produto.data_validade


def test_reserva_integral_preserva_validade_das_unidades_fisicas():
    produto = produto_com_validade(estoque_atual=5, estoque_reservado=5)

    assert validade_da_property(produto) == produto.data_validade


def test_kit_virtual_utiliza_estoque_virtual_positivo_para_validade():
    produto = produto_com_validade(
        tipo_produto="KIT",
        tipo_kit="VIRTUAL",
        estoque_atual=0,
        estoque_virtual=2,
    )

    assert validade_da_property(produto) == produto.data_validade


@pytest.mark.parametrize("estoque", [0, -2])
def test_listagem_sem_estoque_oculta_resumo_antigo_de_lote_com_saldo(estoque):
    produto = produto_com_validade(estoque_atual=estoque)
    validade = datetime(2027, 1, 21)

    listagem._enriquecer_produto_listagem(
        FakeDb(),
        produto,
        "tenant-1",
        incluir_detalhes_composto=False,
        validade_por_produto={
            produto.id: {
                "validade_proxima_listagem": validade,
                "lote_validade_proxima": "LOTE-ANTIGO",
                "lotes_validade_resumo": [
                    {
                        "id": 100,
                        "nome_lote": "LOTE-ANTIGO",
                        "data_validade": validade,
                        "quantidade_disponivel": 2,
                    }
                ],
            }
        },
    )

    assert produto.validade_proxima_listagem is None
    assert produto.lote_validade_proxima is None
    assert produto.lotes_validade_resumo == []
    assert produto.data_validade == validade


def test_listagem_preserva_validade_com_estoque_totalmente_reservado():
    produto = produto_com_validade(estoque_atual=5)
    validade = produto.data_validade

    listagem._enriquecer_produto_listagem(
        FakeDb(),
        produto,
        "tenant-1",
        reservas_por_produto={produto.id: 5},
        incluir_detalhes_composto=False,
        validade_por_produto={produto.id: {"validade_proxima_listagem": validade}},
    )

    assert produto.estoque_disponivel == 0
    assert produto.validade_proxima_listagem == validade


def test_listagem_kit_virtual_com_saldo_preserva_validade(monkeypatch):
    produto = produto_com_validade(
        tipo_produto="KIT", tipo_kit="VIRTUAL", estoque_atual=0
    )
    validade = produto.data_validade
    monkeypatch.setattr(
        listagem.KitEstoqueService,
        "calcular_estoque_virtual_kit",
        lambda *_args, **_kwargs: 2,
    )

    listagem._enriquecer_produto_listagem(
        FakeDb(),
        produto,
        "tenant-1",
        incluir_detalhes_composto=False,
        custos_compostos={},
        validade_por_produto={produto.id: {"validade_proxima_listagem": validade}},
    )

    assert produto.estoque_virtual == 2
    assert produto.validade_proxima_listagem == validade
