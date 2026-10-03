from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.campaigns import models as campaign_models  # noqa: F401 - registra FKs do schema de teste
from app.empresa_config_geral_models import EmpresaConfigGeral
from app.empresa_config_routes import EmpresaConfigGeralUpdate
from app.financeiro_models import ContaReceber, FormaPagamento
from app.models import UserTenant
from app.security.crediario_override import definir_liberacao_crediario
from app.vendas.bloqueio_crediario import validar_bloqueio_crediario


def test_limite_precisa_ser_ao_menos_um_dia():
    with pytest.raises(ValidationError):
        EmpresaConfigGeralUpdate(dias_atraso_bloqueio_venda=0)


def test_bloqueia_somente_ao_atingir_limite_de_atraso(
    db_session, tenant_context, monkeypatch
):
    tenant_id = uuid4()
    tenant_context(tenant_id)
    db_session.add(
        EmpresaConfigGeral(
            tenant_id=tenant_id,
            bloquear_venda_crediario_atrasado=False,
            dias_atraso_bloqueio_venda=10,
        )
    )
    forma = FormaPagamento(
        tenant_id=tenant_id, nome="Crediário", tipo="crediario", user_id=1
    )
    db_session.add(forma)
    db_session.flush()
    conta = ContaReceber(
        tenant_id=tenant_id,
        cliente_id=101,
        descricao="Parcela de crediário",
        forma_pagamento_id=forma.id,
        dre_subcategoria_id=1,
        canal="loja_fisica",
        valor_original=Decimal("100.00"),
        valor_final=Decimal("100.00"),
        valor_recebido=Decimal("0.00"),
        data_emissao=date.today() - timedelta(days=30),
        data_vencimento=date.today() - timedelta(days=9),
        status="pendente",
        user_id=1,
    )
    db_session.add(conta)
    db_session.flush()

    validar_bloqueio_crediario(db_session, tenant_id, 101)
    config = db_session.query(EmpresaConfigGeral).filter_by(tenant_id=tenant_id).one()
    config.bloquear_venda_crediario_atrasado = True
    db_session.flush()
    validar_bloqueio_crediario(db_session, tenant_id, 101)

    conta.data_vencimento = date.today() - timedelta(days=10)
    db_session.flush()
    with pytest.raises(HTTPException) as exc:
        validar_bloqueio_crediario(db_session, tenant_id, 101)
    assert exc.value.status_code == 409
    assert "10 dias" in exc.value.detail

    chamadas = []
    monkeypatch.setattr(
        "app.vendas.bloqueio_crediario.check_permission",
        lambda *args: chamadas.append(("permissao", args[2])),
    )
    monkeypatch.setattr(
        "app.vendas.bloqueio_crediario.log_action",
        lambda *args, **kwargs: chamadas.append(("auditoria", kwargs)),
    )
    validar_bloqueio_crediario(
        db_session,
        tenant_id,
        101,
        venda_id=301,
        user_id=7,
        motivo_liberacao="Cliente autorizou pagamento imediato",
    )
    assert chamadas[0] == ("permissao", "usuarios.manage")
    assert chamadas[1][1]["entity_id"] == 301
    assert chamadas[1][1]["new_value"]["conta_receber_id"] == conta.id

    def negar_permissao(*args):
        raise HTTPException(403, "Sem permissão")

    monkeypatch.setattr(
        "app.vendas.bloqueio_crediario.check_permission", negar_permissao
    )
    with pytest.raises(HTTPException) as sem_permissao:
        validar_bloqueio_crediario(
            db_session,
            tenant_id,
            101,
            venda_id=301,
            user_id=8,
            motivo_liberacao="Cliente autorizou pagamento imediato",
        )
    assert sem_permissao.value.status_code == 403

    conta.valor_recebido = Decimal("100.00")
    db_session.flush()
    validar_bloqueio_crediario(db_session, tenant_id, 101)


def test_nao_bloqueia_outro_cliente_ou_outro_tenant(db_session, tenant_context):
    tenant_id = uuid4()
    tenant_context(tenant_id)
    db_session.add(
        EmpresaConfigGeral(
            tenant_id=tenant_id,
            bloquear_venda_crediario_atrasado=True,
            dias_atraso_bloqueio_venda=1,
        )
    )
    forma = FormaPagamento(
        tenant_id=tenant_id, nome="Crediário", tipo="crediario", user_id=1
    )
    db_session.add(forma)
    db_session.flush()
    db_session.add(
        ContaReceber(
            tenant_id=tenant_id,
            cliente_id=101,
            descricao="Parcela",
            forma_pagamento_id=forma.id,
            dre_subcategoria_id=1,
            canal="loja_fisica",
            valor_original=Decimal("50.00"),
            valor_final=Decimal("50.00"),
            valor_recebido=Decimal("0.00"),
            data_emissao=date.today() - timedelta(days=10),
            data_vencimento=date.today() - timedelta(days=2),
            status="pendente",
            user_id=1,
        )
    )
    db_session.flush()

    validar_bloqueio_crediario(db_session, tenant_id, 102)
    outro_tenant = uuid4()
    tenant_context(outro_tenant)
    validar_bloqueio_crediario(db_session, outro_tenant, 101)


def test_liberacao_individual_pode_ser_revogada_e_nao_atravessa_lojas(
    db_session, tenant_factory, user_factory, monkeypatch
):
    tenant = tenant_factory()
    tenant_id = UUID(str(tenant.id))
    autorizado = user_factory(tenant.id)
    nao_autorizado = user_factory(tenant.id)
    vinculo = db_session.query(UserTenant).filter_by(user_id=autorizado.id).one()
    db_session.add(
        EmpresaConfigGeral(
            tenant_id=tenant_id,
            bloquear_venda_crediario_atrasado=True,
            dias_atraso_bloqueio_venda=30,
        )
    )
    forma = FormaPagamento(
        tenant_id=tenant_id, nome="Crediário", tipo="crediario", user_id=autorizado.id
    )
    db_session.add(forma)
    db_session.flush()
    db_session.add(
        ContaReceber(
            tenant_id=tenant_id,
            cliente_id=101,
            descricao="Parcela vencida",
            forma_pagamento_id=forma.id,
            dre_subcategoria_id=1,
            canal="loja_fisica",
            valor_original=Decimal("100.00"),
            valor_final=Decimal("100.00"),
            valor_recebido=Decimal("0.00"),
            data_emissao=date.today() - timedelta(days=60),
            data_vencimento=date.today() - timedelta(days=40),
            status="vencido",
            user_id=autorizado.id,
        )
    )
    db_session.flush()

    monkeypatch.setattr(
        "app.security.crediario_override.log_action", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        "app.vendas.bloqueio_crediario.log_action", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        "app.vendas.bloqueio_crediario.check_permission",
        lambda *args: (_ for _ in ()).throw(HTTPException(403, "Sem permissão")),
    )

    with pytest.raises(HTTPException) as negado:
        validar_bloqueio_crediario(
            db_session,
            tenant_id,
            101,
            venda_id=10,
            user_id=autorizado.id,
            motivo_liberacao="Autorização de teste",
        )
    assert negado.value.status_code == 403

    definir_liberacao_crediario(
        db_session,
        tenant_id=tenant_id,
        user_id=autorizado.id,
        autorizado=True,
        actor_user_id=nao_autorizado.id,
    )
    db_session.flush()
    assert vinculo.pode_liberar_venda_crediario_atrasado is True
    validar_bloqueio_crediario(
        db_session,
        tenant_id,
        101,
        venda_id=10,
        user_id=autorizado.id,
        motivo_liberacao="Autorização de teste",
    )
    with pytest.raises(HTTPException) as outro_usuario:
        validar_bloqueio_crediario(
            db_session,
            tenant_id,
            101,
            venda_id=10,
            user_id=nao_autorizado.id,
            motivo_liberacao="Autorização de teste",
        )
    assert outro_usuario.value.status_code == 403

    definir_liberacao_crediario(
        db_session,
        tenant_id=tenant_id,
        user_id=autorizado.id,
        autorizado=False,
        actor_user_id=nao_autorizado.id,
    )
    db_session.flush()
    with pytest.raises(HTTPException) as revogado:
        validar_bloqueio_crediario(
            db_session,
            tenant_id,
            101,
            venda_id=10,
            user_id=autorizado.id,
            motivo_liberacao="Autorização de teste",
        )
    assert revogado.value.status_code == 403

    with pytest.raises(HTTPException) as outra_loja:
        definir_liberacao_crediario(
            db_session,
            tenant_id=uuid4(),
            user_id=autorizado.id,
            autorizado=True,
            actor_user_id=nao_autorizado.id,
        )
    assert outra_loja.value.status_code == 404
