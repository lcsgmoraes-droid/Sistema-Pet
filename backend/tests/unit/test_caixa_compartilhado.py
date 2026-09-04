from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.caixa.escopo import buscar_caixa_aberto, buscar_caixa_acessivel
from app.caixa.service import CaixaService
from app.empresa_config_geral_models import EmpresaConfigGeral
from app.empresa_config_routes import _validar_ativacao_caixa_compartilhado


class _FakeQuery:
    def __init__(self, items):
        self.items = list(items)

    def filter(self, *conditions):
        for condition in conditions:
            field = getattr(getattr(condition, "left", None), "key", None)
            right = getattr(condition, "right", None)
            value = getattr(right, "value", None)
            if field is not None and hasattr(right, "value"):
                self.items = [
                    item for item in self.items if getattr(item, field, None) == value
                ]
        return self

    def with_for_update(self):
        return self

    def order_by(self, *args):
        return self

    def first(self):
        return self.items[0] if self.items else None

    def count(self):
        return len(self.items)


class _FakeSession:
    def __init__(self, *, config=None, caixas=()):
        self.config = config
        self.caixas = list(caixas)

    def query(self, target):
        if target is EmpresaConfigGeral:
            return _FakeQuery([self.config] if self.config else [])
        return _FakeQuery(self.caixas)


def _config(tenant_id, *, compartilhado: bool):
    return SimpleNamespace(
        tenant_id=tenant_id,
        caixa_compartilhado=compartilhado,
    )


def _caixa(tenant_id, *, caixa_id: int, usuario_id: int, numero: int):
    return SimpleNamespace(
        id=caixa_id,
        tenant_id=tenant_id,
        numero_caixa=numero,
        usuario_id=usuario_id,
        usuario_nome=f"Usuario {usuario_id}",
        valor_abertura=100,
        data_abertura=None,
        status="aberto",
    )


def test_modo_individual_nao_expoe_caixa_de_outro_usuario():
    tenant_id = uuid4()
    db = _FakeSession(
        config=_config(tenant_id, compartilhado=False),
        caixas=[_caixa(tenant_id, caixa_id=1, usuario_id=10, numero=1)],
    )

    caixa, compartilhado = buscar_caixa_aberto(db, tenant_id=tenant_id, usuario_id=20)

    assert compartilhado is False
    assert caixa is None


def test_modo_compartilhado_reutiliza_caixa_da_empresa():
    tenant_id = uuid4()
    caixa_aberto = _caixa(tenant_id, caixa_id=1, usuario_id=10, numero=1)
    db = _FakeSession(
        config=_config(tenant_id, compartilhado=True),
        caixas=[caixa_aberto],
    )

    caixa, compartilhado = buscar_caixa_aberto(db, tenant_id=tenant_id, usuario_id=20)
    caixa_por_id, _ = buscar_caixa_acessivel(
        db,
        caixa_id=caixa_aberto.id,
        tenant_id=tenant_id,
        usuario_id=20,
    )
    validado = CaixaService.validar_caixa_aberto(
        user_id=20,
        db=db,
        tenant_id=tenant_id,
    )

    assert compartilhado is True
    assert caixa.id == caixa_aberto.id
    assert caixa_por_id.id == caixa_aberto.id
    assert validado["caixa_id"] == caixa_aberto.id


def test_ativacao_exige_somente_um_caixa_aberto():
    tenant_id = uuid4()
    db = _FakeSession(
        caixas=[
            _caixa(tenant_id, caixa_id=1, usuario_id=10, numero=1),
            _caixa(tenant_id, caixa_id=2, usuario_id=20, numero=2),
        ]
    )

    with pytest.raises(HTTPException) as exc:
        _validar_ativacao_caixa_compartilhado(db, tenant_id)

    assert exc.value.status_code == 400
    assert "somente um caixa aberto" in exc.value.detail


def test_migration_preserva_modo_individual_como_padrao():
    migration = (
        Path(__file__).resolve().parents[2]
        / "alembic/versions/zzh20260904a1_caixa_compartilhado_empresa.py"
    ).read_text(encoding="utf-8")

    assert 'down_revision = "zzg20260904a1"' in migration
    assert '"caixa_compartilhado"' in migration
    assert 'server_default=sa.text("false")' in migration
