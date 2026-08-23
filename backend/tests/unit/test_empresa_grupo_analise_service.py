from datetime import date, datetime
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
)
from app.db import Base
from app.empresa_grupo_analise_service import EmpresaGrupoAnaliseService
from app.empresa_grupo_models import EmpresaGrupo, EmpresaGrupoMembro
from app.financeiro_models import ContaPagar, ContaReceber
from app.models import Tenant
from app.produtos_models import Produto
from app.tenancy.context import clear_current_tenant, get_current_tenant, tenant_context
from app.vendas_models import Venda

EMPRESA_A = "51111111-1111-1111-1111-111111111111"
EMPRESA_B = "52222222-2222-2222-2222-222222222222"
EMPRESA_FORA = "53333333-3333-3333-3333-333333333333"
AGORA = datetime(2026, 8, 22, 12, 0)


@pytest.fixture()
def db_local():
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
            EmpresaGrupo.__table__,
            EmpresaGrupoMembro.__table__,
            Venda.__table__,
            Produto.__table__,
            ContaPagar.__table__,
            ContaReceber.__table__,
        ],
    )
    session = Session(engine, expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
        clear_current_tenant()


def _produto(
    nome, estoque, custo, *, ativo=True, tipo_produto="SIMPLES", tipo_kit=None
):
    return Produto(
        user_id=1,
        codigo=nome.upper().replace(" ", "-"),
        nome=nome,
        preco_custo=custo,
        preco_venda=custo * 2,
        estoque_atual=estoque,
        situacao=ativo,
        ativo=ativo,
        tipo_produto=tipo_produto,
        tipo_kit=tipo_kit,
        is_parent=False,
    )


def _venda(numero, valor, data_venda, status="finalizada"):
    return Venda(
        numero_venda=numero,
        vendedor_id=1,
        user_id=1,
        subtotal=valor,
        total=valor,
        status=status,
        data_venda=data_venda,
    )


def _receber(valor, recebido, vencimento):
    return ContaReceber(
        descricao="Conta a receber teste",
        valor_original=valor,
        valor_recebido=recebido,
        valor_final=valor,
        data_emissao=date(2026, 8, 1),
        data_vencimento=vencimento,
        status="pendente",
        dre_subcategoria_id=1,
        canal="loja_fisica",
        user_id=1,
    )


def _pagar(valor, pago, vencimento):
    return ContaPagar(
        descricao="Conta a pagar teste",
        valor_original=valor,
        valor_pago=pago,
        valor_final=valor,
        data_emissao=date(2026, 8, 1),
        data_vencimento=vencimento,
        status="pendente",
        user_id=1,
    )


def _preparar_cenario(db: Session):
    db.add_all(
        [
            Tenant(id=EMPRESA_A, name="Loja A", name_normalized="loja a"),
            Tenant(id=EMPRESA_B, name="Loja B", name_normalized="loja b"),
            Tenant(id=EMPRESA_FORA, name="Loja Fora", name_normalized="loja fora"),
        ]
    )
    db.flush()
    grupo = EmpresaGrupo(
        nome="Grupo Centro",
        criado_por_empresa_id=EMPRESA_A,
        criado_por_usuario_id=1,
        status="ativo",
    )
    db.add(grupo)
    db.flush()
    db.add_all(
        [
            EmpresaGrupoMembro(
                grupo_id=grupo.id,
                empresa_id=EMPRESA_A,
                papel="responsavel",
                status="ativo",
            ),
            EmpresaGrupoMembro(
                grupo_id=grupo.id,
                empresa_id=EMPRESA_B,
                papel="membro",
                status="ativo",
            ),
        ]
    )

    with tenant_context(EMPRESA_A):
        db.add_all(
            [
                _venda("A-1", 100, datetime(2026, 8, 20, 10, 0)),
                _venda("A-CANCELADA", 999, datetime(2026, 8, 21, 10, 0), "cancelada"),
                _produto("Produto A", 5, 10),
                _produto(
                    "Kit virtual A", 10, 100, tipo_produto="KIT", tipo_kit="VIRTUAL"
                ),
                _receber(80, 20, date(2026, 8, 20)),
                _pagar(50, 10, date(2026, 8, 30)),
            ]
        )
        db.flush()

    with tenant_context(EMPRESA_B):
        db.add_all(
            [
                _venda("B-1", 200, datetime(2026, 8, 18, 10, 0)),
                _venda("B-ANTIGA", 300, datetime(2026, 6, 1, 10, 0)),
                _produto("Produto B", 3, 20),
                _produto("Produto inativo B", 100, 30, ativo=False),
                _receber(100, 0, date(2026, 8, 30)),
                _pagar(70, 20, date(2026, 8, 10)),
            ]
        )
        db.flush()

    db.commit()
    return grupo


def test_consolida_apenas_membros_ativos_sem_misturar_contextos(db_local):
    grupo = _preparar_cenario(db_local)

    with tenant_context(EMPRESA_A):
        resultado = EmpresaGrupoAnaliseService(db_local, agora=AGORA).obter(
            grupo.id,
            EMPRESA_A,
            periodo_dias=30,
        )
        assert get_current_tenant() == UUID(EMPRESA_A)

    assert resultado["periodo"] == {
        "dias": 30,
        "data_inicio": "2026-07-24",
        "data_fim": "2026-08-22",
    }
    assert [item["empresa_nome"] for item in resultado["empresas"]] == [
        "Loja A",
        "Loja B",
    ]
    assert resultado["totais"]["vendas"] == {
        "quantidade": 2,
        "finalizadas": 2,
        "valor_total": 300.0,
        "ticket_medio": 150.0,
    }
    assert resultado["totais"]["estoque"] == {
        "produtos_ativos": 2,
        "quantidade": 8.0,
        "valor_custo": 110.0,
    }
    assert resultado["totais"]["financeiro"] == {
        "receber_aberto": 160.0,
        "receber_vencido": 60.0,
        "pagar_aberto": 90.0,
        "pagar_vencido": 50.0,
    }


def test_empresa_fora_do_grupo_nao_acessa_a_visao(db_local):
    grupo = _preparar_cenario(db_local)

    with tenant_context(EMPRESA_FORA):
        with pytest.raises(HTTPException) as erro:
            EmpresaGrupoAnaliseService(db_local, agora=AGORA).obter(
                grupo.id,
                EMPRESA_FORA,
                periodo_dias=30,
            )

    assert erro.value.status_code == 403
    assert erro.value.detail == "Sua empresa não participa deste grupo."
