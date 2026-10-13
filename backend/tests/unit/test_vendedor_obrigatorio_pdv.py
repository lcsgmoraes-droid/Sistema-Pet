from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.empresa_config_geral_models import EmpresaConfigGeral
from app.empresa_config_routes import EmpresaConfigGeralUpdate, get_config_pdv
from app.vendas.vendedor_obrigatorio import exigir_vendedor_pdv


class FakeQuery:
    def __init__(self, configs):
        self.configs = configs

    def filter(self, condition):
        tenant_id = condition.right.value
        self.configs = [
            config for config in self.configs if config.tenant_id == tenant_id
        ]
        return self

    def first(self):
        return self.configs[0] if self.configs else None


class FakeSession:
    def __init__(self, configs):
        self.configs = configs

    def query(self, model):
        assert model is EmpresaConfigGeral
        return FakeQuery(self.configs.copy())


def test_regra_de_vendedor_e_isolada_por_empresa():
    tenant_obrigatorio = uuid4()
    tenant_opcional = uuid4()
    db = FakeSession(
        [
            SimpleNamespace(
                tenant_id=tenant_obrigatorio, vendedor_obrigatorio_pdv=True
            ),
            SimpleNamespace(tenant_id=tenant_opcional, vendedor_obrigatorio_pdv=False),
        ]
    )

    with pytest.raises(HTTPException) as exc_info:
        exigir_vendedor_pdv(db, tenant_obrigatorio, None)
    assert exc_info.value.status_code == 400
    assert "Selecione o vendedor" in exc_info.value.detail

    exigir_vendedor_pdv(db, tenant_obrigatorio, 123)
    exigir_vendedor_pdv(db, tenant_obrigatorio, None, canal="ecommerce")
    exigir_vendedor_pdv(db, tenant_opcional, None)
    assert get_config_pdv.__wrapped__(
        user_and_tenant=(None, tenant_opcional), db=db
    ) == {
        "vendedor_obrigatorio_pdv": False,
        "mostrar_endereco_cliente_pdv": False,
    }
    assert get_config_pdv.__wrapped__(
        user_and_tenant=(None, tenant_obrigatorio), db=db
    ) == {
        "vendedor_obrigatorio_pdv": True,
        "mostrar_endereco_cliente_pdv": False,
    }


def test_preferencia_e_opcional_por_padrao():
    assert EmpresaConfigGeralUpdate().vendedor_obrigatorio_pdv is None
    tenant_id = uuid4()
    db = FakeSession([])
    exigir_vendedor_pdv(db, tenant_id, None)
    assert get_config_pdv.__wrapped__(user_and_tenant=(None, tenant_id), db=db) == {
        "vendedor_obrigatorio_pdv": False,
        "mostrar_endereco_cliente_pdv": False,
    }
