from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.caixa.escopo import buscar_caixa_aberto, buscar_caixa_acessivel
from app.caixa.service import CaixaService
from app.caixa_models import Caixa
from app.empresa_config_geral_models import EmpresaConfigGeral
from app.empresa_config_routes import _validar_ativacao_caixa_compartilhado


def _criar_config(db_session, tenant_id, *, compartilhado: bool):
    config = EmpresaConfigGeral(
        tenant_id=tenant_id,
        caixa_compartilhado=compartilhado,
    )
    db_session.add(config)
    db_session.flush()
    return config


def _criar_caixa(db_session, tenant_id, *, usuario_id: int, numero: int):
    caixa = Caixa(
        tenant_id=tenant_id,
        numero_caixa=numero,
        usuario_id=usuario_id,
        usuario_nome=f"Usuario {usuario_id}",
        valor_abertura=100,
        status="aberto",
    )
    db_session.add(caixa)
    db_session.flush()
    return caixa


def test_modo_individual_nao_expoe_caixa_de_outro_usuario(
    db_session, tenant_context
):
    tenant_id = uuid4()
    tenant_context(tenant_id)
    _criar_config(db_session, tenant_id, compartilhado=False)
    _criar_caixa(db_session, tenant_id, usuario_id=10, numero=1)

    caixa, compartilhado = buscar_caixa_aberto(
        db_session, tenant_id=tenant_id, usuario_id=20
    )

    assert compartilhado is False
    assert caixa is None


def test_modo_compartilhado_reutiliza_caixa_da_empresa(db_session, tenant_context):
    tenant_id = uuid4()
    tenant_context(tenant_id)
    _criar_config(db_session, tenant_id, compartilhado=True)
    caixa_aberto = _criar_caixa(db_session, tenant_id, usuario_id=10, numero=1)

    caixa, compartilhado = buscar_caixa_aberto(
        db_session, tenant_id=tenant_id, usuario_id=20
    )
    caixa_por_id, _ = buscar_caixa_acessivel(
        db_session,
        caixa_id=caixa_aberto.id,
        tenant_id=tenant_id,
        usuario_id=20,
    )
    validado = CaixaService.validar_caixa_aberto(
        user_id=20,
        db=db_session,
        tenant_id=tenant_id,
    )

    assert compartilhado is True
    assert caixa.id == caixa_aberto.id
    assert caixa_por_id.id == caixa_aberto.id
    assert validado["caixa_id"] == caixa_aberto.id


def test_ativacao_exige_somente_um_caixa_aberto(db_session, tenant_context):
    tenant_id = uuid4()
    tenant_context(tenant_id)
    _criar_caixa(db_session, tenant_id, usuario_id=10, numero=1)
    _criar_caixa(db_session, tenant_id, usuario_id=20, numero=2)

    with pytest.raises(HTTPException) as exc:
        _validar_ativacao_caixa_compartilhado(db_session, tenant_id)

    assert exc.value.status_code == 400
    assert "somente um caixa aberto" in exc.value.detail


def test_migration_preserva_modo_individual_como_padrao():
    from pathlib import Path

    migration = (
        Path(__file__).resolve().parents[2]
        / "alembic/versions/zzh20260904a1_caixa_compartilhado_empresa.py"
    ).read_text(encoding="utf-8")

    assert 'down_revision = "zzg20260904a1"' in migration
    assert '"caixa_compartilhado"' in migration
    assert 'server_default=sa.text("false")' in migration
