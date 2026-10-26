"""Ensaio de fusao administrativa com dados ficticios e rollback obrigatorio."""

import os
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app import caixa_models, financeiro_models, produtos_models, vendas_models  # noqa: F401
from app.campaigns.models import (
    Campaign,
    CampaignStatusEnum,
    CampaignTypeEnum,
    LoyaltyStamp,
)
from app.models import AppAccessProfile, Cliente, Role, User, UserTenant
from app.routes.ecommerce_auth_beneficios import meus_beneficios
from app.routes.ecommerce_auth_cliente import _get_or_create_cliente_for_user
from app.services.pessoa_merge_service import (
    executar_fusao_pessoas,
    montar_preview_fusao_pessoas,
)
from app.tenancy.context import clear_current_tenant, set_current_tenant
from app.vendas_models import Venda


def test_preview_e_correcao_do_vinculo_preservam_carimbo_sem_commit():
    database_url = os.getenv("COREPET_TEST_POSTGRES_URL")
    if not database_url:
        pytest.skip("Informe COREPET_TEST_POSTGRES_URL de um banco DEV local")
    destino = make_url(database_url)
    assert destino.host in {"localhost", "127.0.0.1", "::1"}
    assert str(destino.database).endswith("_dev"), (
        "Este ensaio aceita somente banco DEV local"
    )
    engine = create_engine(database_url)
    try:
        with Session(engine) as db:
            try:
                tenant_id = db.execute(
                    text(
                        "SELECT id FROM tenants WHERE lower(status) IN ('active', 'ativo') ORDER BY created_at LIMIT 1"
                    )
                ).scalar_one()
                tenant = UUID(str(tenant_id))
                set_current_tenant(tenant)
                criador = db.query(User).filter(User.tenant_id == tenant).first()
                assert criador is not None
                sufixo = uuid4().hex[:10]
                usuario_app = User(
                    tenant_id=tenant,
                    username=f"ensaio-app-{sufixo}",
                    nome="Pessoa fictícia do ensaio",
                    is_active=True,
                    login_phone=f"+55119{uuid4().int % 100000000:08d}",
                )
                db.add(usuario_app)
                db.flush()
                principal = Cliente(
                    tenant_id=tenant,
                    user_id=criador.id,
                    codigo=f"F-P-{sufixo}",
                    nome="Pessoa completa fictícia",
                    celular=usuario_app.login_phone,
                    ativo=True,
                    is_cliente=True,
                )
                duplicado = Cliente(
                    tenant_id=tenant,
                    user_id=criador.id,
                    auth_user_id=usuario_app.id,
                    codigo=f"F-D-{sufixo}",
                    nome="Pessoa fictícia",
                    ativo=True,
                    is_cliente=True,
                    is_funcionario=True,
                    is_veterinario=True,
                    is_entregador=True,
                    entregador_ativo=True,
                )
                campanha = Campaign(
                    tenant_id=tenant,
                    name=f"Ensaio {sufixo}",
                    campaign_type=CampaignTypeEnum.loyalty_stamp,
                    status=CampaignStatusEnum.active,
                    params={"stamps_to_complete": 10},
                )
                cargo = Role(tenant_id=tenant, name=f"Equipe ensaio {sufixo}")
                db.add_all([principal, duplicado, campanha, cargo])
                db.flush()
                vinculo_equipe = UserTenant(
                    tenant_id=tenant,
                    user_id=usuario_app.id,
                    role_id=cargo.id,
                    is_active=True,
                )
                db.add(vinculo_equipe)
                perfis_esperados = {
                    "cliente",
                    "funcionario",
                    "banho_tosa",
                    "entregador",
                    "taxi_dog",
                    "veterinario",
                }
                db.add_all(
                    [
                        AppAccessProfile(
                            tenant_id=tenant,
                            user_id=usuario_app.id,
                            cliente_id=duplicado.id,
                            profile_type=perfil,
                            is_active=True,
                            granted_by_user_id=criador.id,
                        )
                        for perfil in perfis_esperados
                    ]
                )
                db.execute(
                    Venda.__table__.insert(),
                    [
                        {
                            "tenant_id": tenant,
                            "numero_venda": f"E-{sufixo}-{indice:03d}",
                            "vendedor_id": criador.id,
                            "user_id": criador.id,
                            "vendedor_funcionario_id": duplicado.id,
                            "subtotal": 1,
                            "total": 1,
                        }
                        for indice in range(306)
                    ],
                )
                db.add(
                    LoyaltyStamp(
                        tenant_id=tenant,
                        customer_id=principal.id,
                        campaign_id=campanha.id,
                        stamp_index=1,
                        is_manual=True,
                        notes="Ensaio local com rollback",
                        created_at=datetime.now(timezone.utc),
                    )
                )
                db.flush()

                assert (
                    _get_or_create_cliente_for_user(db, usuario_app).id == duplicado.id
                )
                assert (
                    meus_beneficios(current_user=usuario_app, db=db)["carimbos"][
                        "total_geral"
                    ]
                    == 0
                )
                consultas = []

                def observar_consulta(
                    _conn, _cursor, statement, _params, _context, _many
                ):
                    consultas.append(statement)

                event.listen(engine, "before_cursor_execute", observar_consulta)
                preview = montar_preview_fusao_pessoas(
                    db,
                    tenant_id=tenant,
                    principal_id=principal.id,
                    duplicado_id=duplicado.id,
                )
                assert not any(
                    "FOR UPDATE" in consulta.upper() for consulta in consultas
                )
                assert preview["bloqueios"] == []
                assert preview["principal"]["codigo"] == principal.codigo
                assert preview["duplicado"]["codigo"] == duplicado.codigo

                consultas.clear()
                resultado = executar_fusao_pessoas(
                    db,
                    tenant_id=tenant,
                    principal_id=principal.id,
                    duplicado_id=duplicado.id,
                    decisoes_campos={},
                    user_id=criador.id,
                    observacao="Ensaio DEV fictício com rollback obrigatório",
                    commit=False,
                )
                assert any("FOR UPDATE" in consulta.upper() for consulta in consultas)
                event.remove(engine, "before_cursor_execute", observar_consulta)
                assert resultado["success"] is True
                assert principal.auth_user_id == usuario_app.id
                assert duplicado.auth_user_id is None
                assert duplicado.merged_into_id == principal.id
                assert duplicado.ativo is False
                assert (
                    principal.is_funcionario
                    and principal.is_veterinario
                    and principal.is_entregador
                )
                grants = (
                    db.query(AppAccessProfile)
                    .filter(
                        AppAccessProfile.tenant_id == tenant,
                        AppAccessProfile.cliente_id == principal.id,
                        AppAccessProfile.is_active.is_(True),
                    )
                    .all()
                )
                assert {grant.profile_type for grant in grants} == perfis_esperados
                assert {grant.user_id for grant in grants} == {usuario_app.id}
                db.refresh(vinculo_equipe)
                db.refresh(usuario_app)
                assert vinculo_equipe.role_id == cargo.id and vinculo_equipe.is_active
                assert usuario_app.is_active and not usuario_app.is_admin
                assert (
                    db.query(Venda)
                    .filter(
                        Venda.tenant_id == tenant,
                        Venda.vendedor_funcionario_id == principal.id,
                        Venda.numero_venda.like(f"E-{sufixo}-%"),
                    )
                    .count()
                    == 306
                )
                assert (
                    db.query(Venda)
                    .filter(
                        Venda.tenant_id == tenant,
                        Venda.vendedor_funcionario_id == duplicado.id,
                    )
                    .count()
                    == 0
                )
                assert (
                    _get_or_create_cliente_for_user(db, usuario_app).id == principal.id
                )
                assert (
                    meus_beneficios(current_user=usuario_app, db=db)["carimbos"][
                        "total_geral"
                    ]
                    == 1
                )
            finally:
                db.rollback()
                clear_current_tenant()
        with engine.connect() as connection:
            assert (
                connection.execute(
                    text(
                        "SELECT count(*) FROM users WHERE tenant_id = :tenant AND username = :username"
                    ),
                    {"tenant": tenant, "username": usuario_app.username},
                ).scalar_one()
                == 0
            )
    finally:
        engine.dispose()
