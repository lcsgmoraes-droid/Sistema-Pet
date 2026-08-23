from datetime import date
from uuid import UUID

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import (  # noqa: F401
    caixa_models,
    dre_plano_contas_models,
    ecommerceai_integration_models,
    vendas_models,
)
from app.db import Base
from app.empresa_grupo_models import (
    EmpresaGrupo,
    EmpresaGrupoMembro,
    EmpresaGrupoProdutoVinculo,
    EmpresaGrupoTransferencia,
)
from app.estoque.transferencia_grupo_schemas import (
    TransferenciaGrupoExecutarRequest,
    TransferenciaGrupoItemRequest,
    TransferenciaGrupoPreviaRequest,
)
from app.estoque.transferencia_grupo_service import (
    MOTIVO_CANCELAMENTO_GRUPO,
    cancelar_transferencia_integrada_por_conta,
    executar_transferencia_integrada,
    preparar_previa_transferencia,
)
from app.financeiro_models import ContaPagar, ContaReceber
from app.models import Role, Tenant, User, UserTenant
from app.produtos_models import EstoqueMovimentacao, Produto
from app.tenancy.context import tenant_context

EMPRESA_A = "41111111-1111-1111-1111-111111111111"
EMPRESA_B = "42222222-2222-2222-2222-222222222222"


@pytest.fixture()
def db_local():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = Session(engine, expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _preparar_cenario(db_session):
    db_session.add_all(
        [
            Tenant(id=EMPRESA_A, name="Loja Origem", name_normalized="loja origem"),
            Tenant(id=EMPRESA_B, name="Loja Destino", name_normalized="loja destino"),
        ]
    )
    db_session.flush()

    with tenant_context(EMPRESA_A):
        usuario_a = User(
            email="grupo-origem@teste.corepet",
            nome="Usuário Origem",
            is_active=True,
        )
        perfil_a = Role(name="Administrador origem")
        db_session.add_all([usuario_a, perfil_a])
        db_session.flush()
        db_session.add(
            UserTenant(
                user_id=usuario_a.id,
                role_id=perfil_a.id,
                is_active=True,
            )
        )
        produto_a = Produto(
            user_id=usuario_a.id,
            codigo="RACAO-ORIGEM",
            nome="Ração 10 kg",
            codigo_barras="7891234567890",
            preco_custo=20,
            preco_venda=30,
            estoque_atual=5,
            situacao=True,
            tipo_produto="SIMPLES",
            is_parent=False,
        )
        db_session.add(produto_a)
        db_session.flush()

    with tenant_context(EMPRESA_B):
        usuario_b = User(
            email="grupo-destino@teste.corepet",
            nome="Usuário Destino",
            is_active=True,
        )
        perfil_b = Role(name="Administrador destino")
        db_session.add_all([usuario_b, perfil_b])
        db_session.flush()
        db_session.add(
            UserTenant(
                user_id=usuario_b.id,
                role_id=perfil_b.id,
                is_active=True,
            )
        )
        produto_b = Produto(
            user_id=usuario_b.id,
            codigo="RACAO-DESTINO",
            nome="Ração especial 10 kg",
            codigo_barras="7891234567890",
            preco_custo=19,
            preco_venda=32,
            estoque_atual=1,
            situacao=True,
            tipo_produto="SIMPLES",
            is_parent=False,
        )
        db_session.add(produto_b)
        db_session.flush()

    grupo = EmpresaGrupo(
        nome="Grupo Teste",
        criado_por_empresa_id=EMPRESA_A,
        criado_por_usuario_id=usuario_a.id,
        status="ativo",
    )
    db_session.add(grupo)
    db_session.flush()
    db_session.add_all(
        [
            EmpresaGrupoMembro(
                grupo_id=grupo.id,
                empresa_id=EMPRESA_A,
                papel="responsavel",
                status="ativo",
                usuario_referencia_id=usuario_a.id,
            ),
            EmpresaGrupoMembro(
                grupo_id=grupo.id,
                empresa_id=EMPRESA_B,
                papel="membro",
                status="ativo",
                usuario_referencia_id=usuario_b.id,
            ),
        ]
    )
    db_session.flush()
    db_session.commit()
    return grupo, usuario_a, produto_a, produto_b


def _payload(grupo_id: int, chave: str) -> TransferenciaGrupoExecutarRequest:
    return TransferenciaGrupoExecutarRequest(
        grupo_id=grupo_id,
        empresa_destino_id=UUID(EMPRESA_B),
        chave_idempotencia=UUID(chave),
        data_vencimento=date(2026, 8, 31),
        observacao="Reposição entre lojas",
        itens=[
            TransferenciaGrupoItemRequest(
                produto_id=1,
                quantidade=2,
                custo_unitario=20,
                valor_total=40,
            )
        ],
    )


def _ajustar_produto_payload(payload, produto_id: int):
    payload.itens[0].produto_id = produto_id
    return payload


def _silenciar_pos_commit(monkeypatch):
    monkeypatch.setattr(
        "app.estoque.transferencia_grupo_service.sincronizar_bling_background",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "app.estoque.transferencia_grupo_service.registrar_uso_funcionalidade",
        lambda *_args, **_kwargs: True,
    )


def test_previa_aceita_vinculo_manual_quando_codigos_sao_diferentes(db_local):
    grupo, usuario_a, produto_a, produto_b = _preparar_cenario(db_local)
    produto_a.codigo_barras = "1111111111111"
    produto_b.codigo_barras = "2222222222222"
    db_local.add(
        EmpresaGrupoProdutoVinculo(
            grupo_id=grupo.id,
            empresa_a_id=EMPRESA_A,
            produto_a_id=produto_a.id,
            empresa_b_id=EMPRESA_B,
            produto_b_id=produto_b.id,
            status="ativo",
            criado_por_empresa_id=EMPRESA_A,
            criado_por_usuario_id=usuario_a.id,
        )
    )
    db_local.commit()
    payload = TransferenciaGrupoPreviaRequest(
        grupo_id=grupo.id,
        empresa_destino_id=UUID(EMPRESA_B),
        itens=[
            TransferenciaGrupoItemRequest(
                produto_id=produto_a.id,
                quantidade=2,
                custo_unitario=20,
                valor_total=40,
            )
        ],
    )

    with tenant_context(EMPRESA_A):
        resultado = preparar_previa_transferencia(
            db_local,
            empresa_origem_id=EMPRESA_A,
            payload=payload,
        )

    assert resultado["todos_mapeados"] is True
    assert resultado["itens"][0]["produto_destino_id"] == produto_b.id
    assert resultado["itens"][0]["identificador"] == "Vínculo do grupo"
    assert resultado["itens"][0]["mensagem"] == (
        "Produto correspondente confirmado pelo vínculo do grupo."
    )


def test_transferencia_integrada_movimenta_estoque_e_financeiro_dos_dois_lados(
    db_local, monkeypatch
):
    db_session = db_local
    grupo, usuario_a, produto_a, produto_b = _preparar_cenario(db_session)
    _silenciar_pos_commit(monkeypatch)
    payload = _ajustar_produto_payload(
        _payload(grupo.id, "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        produto_a.id,
    )

    with tenant_context(EMPRESA_A):
        resultado = executar_transferencia_integrada(
            db_session,
            empresa_origem_id=EMPRESA_A,
            usuario_origem_id=usuario_a.id,
            payload=payload,
        )
        resultado_repetido = executar_transferencia_integrada(
            db_session,
            empresa_origem_id=EMPRESA_A,
            usuario_origem_id=usuario_a.id,
            payload=payload,
        )

    db_session.expire_all()
    assert resultado["sucesso"] is True
    assert resultado_repetido["idempotente"] is True
    assert (
        resultado_repetido["transferencia_grupo_id"]
        == resultado["transferencia_grupo_id"]
    )
    with tenant_context(EMPRESA_A):
        assert db_session.get(Produto, produto_a.id).estoque_atual == pytest.approx(3)
        assert db_session.query(ContaReceber).count() == 1
    with tenant_context(EMPRESA_B):
        assert db_session.get(Produto, produto_b.id).estoque_atual == pytest.approx(3)
        assert db_session.query(ContaPagar).count() == 1
    transferencia = db_session.query(EmpresaGrupoTransferencia).one()
    assert transferencia.status == "concluida"
    assert transferencia.conta_receber_origem_id == resultado["conta_receber_origem_id"]
    assert transferencia.conta_pagar_destino_id == resultado["conta_pagar_destino_id"]


def test_falha_na_entrada_reverte_toda_a_saida_da_origem(db_local, monkeypatch):
    db_session = db_local
    grupo, usuario_a, produto_a, _produto_b = _preparar_cenario(db_session)
    _silenciar_pos_commit(monkeypatch)
    monkeypatch.setattr(
        "app.estoque.transferencia_grupo_service.registrar_entrada_parceiro",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            HTTPException(status_code=409, detail="Falha simulada no destino")
        ),
    )
    payload = _ajustar_produto_payload(
        _payload(grupo.id, "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
        produto_a.id,
    )

    with tenant_context(EMPRESA_A):
        with pytest.raises(HTTPException, match="Falha simulada no destino"):
            executar_transferencia_integrada(
                db_session,
                empresa_origem_id=EMPRESA_A,
                usuario_origem_id=usuario_a.id,
                payload=payload,
            )
        db_session.rollback()

    db_session.expire_all()
    with tenant_context(EMPRESA_A):
        produto_recarregado = db_session.get(Produto, produto_a.id)
        assert produto_recarregado is not None
        assert produto_recarregado.estoque_atual == pytest.approx(5)
        assert db_session.query(ContaReceber).count() == 0
    with tenant_context(EMPRESA_B):
        assert db_session.query(ContaPagar).count() == 0
    with tenant_context(EMPRESA_A):
        assert db_session.query(EmpresaGrupoTransferencia).count() == 0


def test_cancelamento_integrado_reverte_estoque_e_financeiro_dos_dois_lados(
    db_local, monkeypatch
):
    db_session = db_local
    grupo, usuario_a, produto_a, produto_b = _preparar_cenario(db_session)
    _silenciar_pos_commit(monkeypatch)
    payload = _ajustar_produto_payload(
        _payload(grupo.id, "cccccccc-cccc-4ccc-8ccc-cccccccccccc"),
        produto_a.id,
    )

    with tenant_context(EMPRESA_A):
        resultado = executar_transferencia_integrada(
            db_session,
            empresa_origem_id=EMPRESA_A,
            usuario_origem_id=usuario_a.id,
            payload=payload,
        )
        cancelamento = cancelar_transferencia_integrada_por_conta(
            db_session,
            empresa_origem_id=EMPRESA_A,
            usuario_origem_id=usuario_a.id,
            conta_receber_origem_id=resultado["conta_receber_origem_id"],
        )
        cancelamento_repetido = cancelar_transferencia_integrada_por_conta(
            db_session,
            empresa_origem_id=EMPRESA_A,
            usuario_origem_id=usuario_a.id,
            conta_receber_origem_id=resultado["conta_receber_origem_id"],
        )

    db_session.expire_all()
    assert cancelamento is not None
    assert cancelamento["transferencia_integrada"] is True
    assert cancelamento["status"] == "cancelada"
    assert cancelamento["idempotente"] is False
    assert cancelamento_repetido is not None
    assert cancelamento_repetido["idempotente"] is True

    with tenant_context(EMPRESA_A):
        assert db_session.get(Produto, produto_a.id).estoque_atual == pytest.approx(5)
        conta_receber = db_session.get(
            ContaReceber, resultado["conta_receber_origem_id"]
        )
        assert conta_receber.status == "cancelado"
        assert (
            db_session.query(EstoqueMovimentacao)
            .filter(EstoqueMovimentacao.motivo == MOTIVO_CANCELAMENTO_GRUPO)
            .count()
            == 1
        )
    with tenant_context(EMPRESA_B):
        assert db_session.get(Produto, produto_b.id).estoque_atual == pytest.approx(1)
        conta_pagar = db_session.get(ContaPagar, resultado["conta_pagar_destino_id"])
        assert conta_pagar.status == "cancelado"
        assert (
            db_session.query(EstoqueMovimentacao)
            .filter(EstoqueMovimentacao.motivo == MOTIVO_CANCELAMENTO_GRUPO)
            .count()
            == 1
        )
    transferencia = db_session.get(
        EmpresaGrupoTransferencia, resultado["transferencia_grupo_id"]
    )
    assert transferencia.status == "cancelada"
    assert (
        transferencia.resultado["cancelamento"]["cancelado_por_usuario_id"]
        == usuario_a.id
    )


def test_cancelamento_integrado_bloqueia_se_estoque_destino_ja_foi_consumido(
    db_local, monkeypatch
):
    db_session = db_local
    grupo, usuario_a, produto_a, produto_b = _preparar_cenario(db_session)
    _silenciar_pos_commit(monkeypatch)
    payload = _ajustar_produto_payload(
        _payload(grupo.id, "dddddddd-dddd-4ddd-8ddd-dddddddddddd"),
        produto_a.id,
    )

    with tenant_context(EMPRESA_A):
        resultado = executar_transferencia_integrada(
            db_session,
            empresa_origem_id=EMPRESA_A,
            usuario_origem_id=usuario_a.id,
            payload=payload,
        )
    with tenant_context(EMPRESA_B):
        produto_destino = db_session.get(Produto, produto_b.id)
        produto_destino.estoque_atual = 1
        db_session.commit()

    with tenant_context(EMPRESA_A):
        with pytest.raises(HTTPException, match="Reponha o estoque"):
            cancelar_transferencia_integrada_por_conta(
                db_session,
                empresa_origem_id=EMPRESA_A,
                usuario_origem_id=usuario_a.id,
                conta_receber_origem_id=resultado["conta_receber_origem_id"],
            )
        db_session.rollback()

    db_session.expire_all()
    with tenant_context(EMPRESA_A):
        assert db_session.get(Produto, produto_a.id).estoque_atual == pytest.approx(3)
        conta_receber = db_session.get(
            ContaReceber, resultado["conta_receber_origem_id"]
        )
        assert conta_receber.status == "pendente"
    with tenant_context(EMPRESA_B):
        assert db_session.get(Produto, produto_b.id).estoque_atual == pytest.approx(1)
        conta_pagar = db_session.get(ContaPagar, resultado["conta_pagar_destino_id"])
        assert conta_pagar.status == "pendente"
    transferencia = db_session.get(
        EmpresaGrupoTransferencia, resultado["transferencia_grupo_id"]
    )
    assert transferencia.status == "concluida"
