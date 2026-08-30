from uuid import UUID

import pytest
from fastapi import HTTPException
from sqlalchemy import Column, String, create_engine
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.empresa_grupo_estoque_compartilhado_service import (
    EmpresaGrupoEstoqueCompartilhadoService,
)
from app.empresa_grupo_models import (
    EmpresaGrupo,
    EmpresaGrupoEstoqueCompartilhado,
    EmpresaGrupoMembro,
)
from app.estoque.service import EstoqueService
from app.models import Tenant, User
from app.produtos_models import EstoqueMovimentacao, Produto, ProdutoLote
from app.tenancy.context import clear_current_tenant, tenant_context
from app.vendas.estoque_baixa import processar_baixa_estoque_item


ORIGEM = "71111111-1111-1111-1111-111111111111"
CONSUMIDORA = "72222222-2222-2222-2222-222222222222"


def test_id_de_empresa_se_adapta_ao_tipo_fisico_do_banco():
    service = EmpresaGrupoEstoqueCompartilhadoService(None)

    assert service._valor_empresa_para_coluna(ORIGEM, Column(String(36))) == ORIGEM
    assert service._valor_empresa_para_coluna(
        ORIGEM, Column(PostgresUUID(as_uuid=True))
    ) == UUID(ORIGEM)


@pytest.fixture()
def db(monkeypatch):
    clear_current_tenant()
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            Tenant.__table__,
            User.__table__,
            Produto.__table__,
            ProdutoLote.__table__,
            EstoqueMovimentacao.__table__,
            EmpresaGrupo.__table__,
            EmpresaGrupoMembro.__table__,
            EmpresaGrupoEstoqueCompartilhado.__table__,
        ],
    )
    session = Session(engine, expire_on_commit=False)
    monkeypatch.setattr(
        "app.empresa_grupo_estoque_compartilhado_service.log_business_event",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        "app.empresa_grupo_service.log_business_event",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        "app.empresa_grupo_estoque_compartilhado_service.registrar_uso_funcionalidade",
        lambda *_args, **_kwargs: True,
    )
    syncs = []
    monkeypatch.setattr(
        "app.estoque.service._agenda_sync_bling",
        lambda produto_id, estoque_novo, motivo: syncs.append(
            (produto_id, estoque_novo, motivo)
        ),
    )
    try:
        yield session, syncs
    finally:
        session.close()
        engine.dispose()
        clear_current_tenant()


def _preparar_cenario(db: Session):
    db.add_all(
        [
            Tenant(
                id=ORIGEM, name="GS Multi Marcas", name_normalized="gs multi marcas"
            ),
            Tenant(id=CONSUMIDORA, name="Atacadão", name_normalized="atacadao"),
        ]
    )
    db.flush()
    with tenant_context(ORIGEM):
        usuario = User(email="estoque-gabi@teste.corepet", nome="Gabi", is_active=True)
        db.add(usuario)
        db.flush()
        produto = Produto(
            user_id=usuario.id,
            codigo="ND-001",
            codigo_barras="7890000000001",
            nome="N&D Prime Gatos",
            preco_custo=60,
            preco_venda=99.9,
            estoque_atual=10,
            situacao=True,
            ativo=True,
            tipo="produto",
            tipo_produto="SIMPLES",
            is_parent=False,
        )
        db.add(produto)
        db.flush()

    grupo = EmpresaGrupo(
        nome="Consolidado Atacadão",
        criado_por_empresa_id=CONSUMIDORA,
        criado_por_usuario_id=1,
    )
    db.add(grupo)
    db.flush()
    db.add_all(
        [
            EmpresaGrupoMembro(
                grupo_id=grupo.id,
                empresa_id=CONSUMIDORA,
                papel="responsavel",
                status="ativo",
            ),
            EmpresaGrupoMembro(
                grupo_id=grupo.id,
                empresa_id=ORIGEM,
                papel="membro",
                status="ativo",
            ),
        ]
    )
    db.commit()
    return grupo, produto, usuario


def test_somente_produto_autorizado_pode_ser_resolvido_no_pdv(db):
    session, _syncs = db
    grupo, produto, _usuario = _preparar_cenario(session)
    service = EmpresaGrupoEstoqueCompartilhadoService(session)

    with tenant_context(CONSUMIDORA):
        with pytest.raises(HTTPException) as sem_autorizacao:
            service.resolver_produto_venda(session, CONSUMIDORA, produto.id)
    assert sem_autorizacao.value.status_code == 404

    with tenant_context(ORIGEM):
        resultado = service.compartilhar(grupo.id, ORIGEM, 1, CONSUMIDORA, [produto.id])
    assert resultado == {"ativados": 1, "selecionados": 1}

    with tenant_context(CONSUMIDORA):
        resolvido = service.resolver_produto_venda(session, CONSUMIDORA, produto.id)
    assert resolvido.compartilhado is True
    assert resolvido.tenant_origem_id == ORIGEM
    assert resolvido.empresa_origem_nome == "GS Multi Marcas"


def test_baixa_e_estorno_ocorrem_no_tenant_de_origem_e_disparam_sync(db):
    session, syncs = db
    grupo, produto, _usuario = _preparar_cenario(session)
    service = EmpresaGrupoEstoqueCompartilhadoService(session)
    with tenant_context(ORIGEM):
        service.compartilhar(grupo.id, ORIGEM, 1, CONSUMIDORA, [produto.id])

    with tenant_context(CONSUMIDORA):
        resolvido = service.resolver_produto_venda(session, CONSUMIDORA, produto.id)

    with tenant_context(resolvido.tenant_origem_id) as tenant_origem_uuid:
        processar_baixa_estoque_item(
            produto=resolvido.produto,
            quantidade_vendida=3,
            venda_id=900,
            user_id=0,
            tenant_id=tenant_origem_uuid,
            db=session,
            venda_codigo="VEN-900",
            observacao="Venda no PDV do Atacadão",
        )
    session.commit()

    with tenant_context(ORIGEM) as tenant_origem_uuid:
        produto_atualizado = (
            session.query(Produto).filter(Produto.id == produto.id).one()
        )
        movimentacao = (
            session.query(EstoqueMovimentacao)
            .filter(EstoqueMovimentacao.referencia_id == 900)
            .one()
        )
    assert produto_atualizado.estoque_atual == 7
    assert str(movimentacao.tenant_id) == ORIGEM
    assert syncs[-1] == (produto.id, 7.0, "venda")

    with tenant_context(ORIGEM) as tenant_origem_uuid:
        EstoqueService.estornar_estoque(
            produto_id=produto.id,
            quantidade=3,
            motivo="cancelamento_venda",
            referencia_id=900,
            referencia_tipo="venda",
            user_id=0,
            tenant_id=tenant_origem_uuid,
            db=session,
        )
    session.commit()

    with tenant_context(ORIGEM):
        produto_restaurado = (
            session.query(Produto).filter(Produto.id == produto.id).one()
        )
    assert produto_restaurado.estoque_atual == 10
    assert syncs[-1] == (produto.id, 10.0, "cancelamento_venda")


def test_remover_compartilhamento_bloqueia_nova_venda_sem_apagar_historico(db):
    session, _syncs = db
    grupo, produto, _usuario = _preparar_cenario(session)
    service = EmpresaGrupoEstoqueCompartilhadoService(session)
    with tenant_context(ORIGEM):
        service.compartilhar(grupo.id, ORIGEM, 1, CONSUMIDORA, [produto.id])
        item = service.listar(grupo.id, ORIGEM)[0]
        service.remover(grupo.id, item["id"], ORIGEM, 1)

    with tenant_context(CONSUMIDORA):
        with pytest.raises(HTTPException) as removido:
            service.resolver_produto_venda(session, CONSUMIDORA, produto.id)
        historico = service.carregar_produto_historico(
            session,
            produto_id=produto.id,
            tenant_origem_id=UUID(ORIGEM),
            compartilhamento_id=item["id"],
            empresa_origem_nome="GS Multi Marcas",
        )
    assert removido.value.status_code == 404
    assert historico.produto.nome == "N&D Prime Gatos"
    assert historico.compartilhamento_ativo is False


def test_remover_empresa_do_grupo_revoga_compartilhamentos_anteriores(db):
    from app.empresa_grupo_service import EmpresaGrupoService

    session, _syncs = db
    grupo, produto, _usuario = _preparar_cenario(session)
    compartilhamento_service = EmpresaGrupoEstoqueCompartilhadoService(session)
    with tenant_context(ORIGEM):
        compartilhamento_service.compartilhar(
            grupo.id, ORIGEM, 1, CONSUMIDORA, [produto.id]
        )

    with tenant_context(CONSUMIDORA):
        EmpresaGrupoService(session).remover_membro(
            CONSUMIDORA,
            1,
            grupo.id,
            ORIGEM,
        )

    compartilhamento = session.query(EmpresaGrupoEstoqueCompartilhado).one()
    assert compartilhamento.status == "removido"
    assert compartilhamento.removido_em is not None
