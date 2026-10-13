from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.empresa_config_geral_models import EmpresaConfigGeral
from app.empresa_config_routes import (
    EmpresaConfigGeralCreate,
    EmpresaConfigGeralUpdate,
    get_config_pdv,
    update_config_empresa,
)


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, condition):
        self.rows = [r for r in self.rows if r.tenant_id == condition.right.value]
        return self

    def with_for_update(self):
        return self

    def first(self):
        return self.rows[0] if self.rows else None


class FakeSession:
    def __init__(self, rows):
        self.rows = rows
        self.commits = 0

    def query(self, model):
        assert model is EmpresaConfigGeral
        return FakeQuery(self.rows.copy())

    def commit(self):
        self.commits += 1

    def refresh(self, row):
        pass


def test_flag_endereco_usa_default_desativado_e_rejeita_null():
    assert EmpresaConfigGeralCreate().mostrar_endereco_cliente_pdv is False
    assert "mostrar_endereco_cliente_pdv" not in (
        EmpresaConfigGeralUpdate().model_dump(exclude_unset=True)
    )
    with pytest.raises(ValidationError):
        EmpresaConfigGeralUpdate(mostrar_endereco_cliente_pdv=None)
    assert (
        get_config_pdv.__wrapped__(user_and_tenant=(None, uuid4()), db=FakeSession([]))[
            "mostrar_endereco_cliente_pdv"
        ]
        is False
    )


def test_flag_endereco_persiste_por_empresa_sem_alterar_vendedor(monkeypatch):
    tenant_a, tenant_b = uuid4(), uuid4()
    rows = [
        EmpresaConfigGeral(
            id=index,
            tenant_id=tenant,
            mostrar_endereco_cliente_pdv=False,
            vendedor_obrigatorio_pdv=True,
        )
        for index, tenant in enumerate((tenant_a, tenant_b), 1)
    ]
    db = FakeSession(rows)
    monkeypatch.setattr("app.empresa_config_routes._obter_nome_acesso", lambda *_: None)
    actor = SimpleNamespace(id=42)
    for enabled in (True, False):
        response = update_config_empresa.__wrapped__(
            config_data=EmpresaConfigGeralUpdate(mostrar_endereco_cliente_pdv=enabled),
            user_and_tenant=(actor, tenant_a),
            db=db,
        )
        assert response.mostrar_endereco_cliente_pdv is enabled
        assert response.vendedor_obrigatorio_pdv is True
        assert rows[0].mostrar_endereco_cliente_pdv is enabled
        assert rows[1].mostrar_endereco_cliente_pdv is False
        for tenant, expected in ((tenant_a, enabled), (tenant_b, False)):
            pdv = get_config_pdv.__wrapped__(user_and_tenant=(actor, tenant), db=db)
            assert pdv["mostrar_endereco_cliente_pdv"] is expected
            assert pdv["vendedor_obrigatorio_pdv"] is True
    assert db.commits == 2
