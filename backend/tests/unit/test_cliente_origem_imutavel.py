from uuid import uuid4

import pytest

from app.models_cadastros import Cliente


def test_origem_pode_ser_definida_uma_vez_na_criacao():
    origem = uuid4()
    cliente = Cliente(tenant_id=origem, nome="Ana")
    cliente.origem_tenant_id = origem
    assert cliente.origem_tenant_id == origem


def test_origem_nao_pode_ser_trocada_depois_de_definida():
    cliente = Cliente(tenant_id=uuid4(), nome="Ana")
    cliente.origem_tenant_id = uuid4()
    with pytest.raises(ValueError):
        cliente.origem_tenant_id = uuid4()
