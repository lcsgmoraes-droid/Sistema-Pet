from datetime import date, datetime
from types import SimpleNamespace

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
from app.empresa_grupo_analise_detalhes_service import (
    EmpresaGrupoAnaliseDetalhesService,
)
from app.empresa_grupo_models import (
    EmpresaGrupo,
    EmpresaGrupoMembro,
    EmpresaGrupoProdutoVinculo,
)
from app.empresa_grupo_produto_vinculo_service import (
    EmpresaGrupoProdutoVinculoService,
)
from app.financeiro_models import ContaPagar
from app.models import Tenant
from app.models_cadastros import Cliente
from app.produtos_models import PedidoCompra, PedidoCompraItem, Produto
from app.tenancy.context import clear_current_tenant, tenant_context
from app.vendas_models import Venda, VendaItem

EMPRESA_A = "61111111-1111-1111-1111-111111111111"
EMPRESA_B = "62222222-2222-2222-2222-222222222222"
EMPRESA_FORA = "63333333-3333-3333-3333-333333333333"
AGORA = datetime(2026, 8, 22, 12, 0)


@pytest.fixture()
def db_local(monkeypatch):
    clear_current_tenant()
    monkeypatch.setattr(
        "app.empresa_grupo_produto_vinculo_service.log_business_event",
        lambda **_kwargs: None,
    )
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
            EmpresaGrupoProdutoVinculo.__table__,
            Cliente.__table__,
            Produto.__table__,
            Venda.__table__,
            VendaItem.__table__,
            PedidoCompra.__table__,
            PedidoCompraItem.__table__,
            ContaPagar.__table__,
        ],
    )
    session = Session(engine, expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
        clear_current_tenant()


def _produto(nome, sku, ean, estoque):
    return Produto(
        user_id=1,
        codigo=sku,
        codigo_barras=ean,
        nome=nome,
        preco_custo=10,
        preco_venda=20,
        estoque_atual=estoque,
        estoque_minimo=2,
        situacao=True,
        ativo=True,
        tipo_produto="SIMPLES",
        is_parent=False,
    )


def _venda(numero, valor, quando, cliente_id, status="finalizada"):
    return Venda(
        numero_venda=numero,
        vendedor_id=1,
        user_id=1,
        cliente_id=cliente_id,
        subtotal=valor,
        total=valor,
        status=status,
        canal="loja_fisica",
        data_venda=quando,
    )


def _conta(descricao, valor, pago, vencimento, fornecedor_id):
    return ContaPagar(
        descricao=descricao,
        fornecedor_id=fornecedor_id,
        valor_original=valor,
        valor_pago=pago,
        valor_final=valor,
        data_emissao=date(2026, 8, 1),
        data_vencimento=vencimento,
        status="pendente",
        user_id=1,
    )


def _preparar(db: Session):
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

    referencias = {}
    for empresa_id, prefixo, ean, valor, vencimento in (
        (EMPRESA_A, "A", "7891000000011", 100, date(2026, 8, 30)),
        (EMPRESA_B, "B", "7891000000011", 200, date(2026, 8, 10)),
    ):
        with tenant_context(empresa_id):
            cliente = Cliente(user_id=1, nome=f"Cliente {prefixo}")
            produto_ean = _produto(f"Ração {prefixo}", f"RACAO-{prefixo}", ean, 5)
            produto_manual = _produto(
                f"Petisco {prefixo}", f"PET-{prefixo}", f"78920000000{prefixo}", 3
            )
            db.add_all([cliente, produto_ean, produto_manual])
            db.flush()
            venda = _venda(
                f"{prefixo}-1",
                valor,
                datetime(2026, 8, 20, 10, 0),
                cliente.id,
            )
            db.add(venda)
            db.flush()
            pedido_compra = PedidoCompra(
                numero_pedido=f"PC-{prefixo}-1",
                fornecedor_id=cliente.id,
                status="enviado" if prefixo == "A" else "recebido_total",
                valor_total=valor,
                valor_final=valor,
                data_pedido=datetime(2026, 8, 19, 10, 0),
                sugestao_ia=prefixo == "A",
                user_id=1,
            )
            db.add(pedido_compra)
            db.flush()
            db.add_all(
                [
                    VendaItem(
                        venda_id=venda.id,
                        tipo="produto",
                        produto_id=produto_ean.id,
                        quantidade=2,
                        preco_unitario=valor / 2,
                        subtotal=valor,
                    ),
                    VendaItem(
                        venda_id=venda.id,
                        tipo="produto",
                        produto_id=produto_manual.id,
                        quantidade=1,
                        preco_unitario=10,
                        subtotal=10,
                    ),
                    PedidoCompraItem(
                        pedido_compra_id=pedido_compra.id,
                        produto_id=produto_ean.id,
                        quantidade_pedida=4,
                        quantidade_recebida=2 if prefixo == "A" else 4,
                        unidade_compra="UN",
                        quantidade_total_unidades=4,
                        preco_unitario=valor / 4,
                        valor_total=valor,
                        sugestao_ia=prefixo == "A",
                    ),
                    _conta(
                        f"Fornecedor {prefixo}",
                        valor,
                        20,
                        vencimento,
                        cliente.id,
                    ),
                ]
            )
            db.flush()
            referencias[empresa_id] = {
                "produto_ean": produto_ean,
                "produto_manual": produto_manual,
            }
    db.commit()
    return grupo, referencias


def test_lista_pedidos_e_contas_pagar_das_duas_empresas(db_local):
    grupo, _referencias = _preparar(db_local)
    service = EmpresaGrupoAnaliseDetalhesService(db_local, agora=AGORA)

    pedidos = service.listar_pedidos(grupo.id, EMPRESA_A, periodo_dias=30)
    pedidos_compra = service.listar_pedidos_compra(grupo.id, EMPRESA_A, periodo_dias=30)
    contas = service.listar_contas_pagar(grupo.id, EMPRESA_A, situacao="abertas")

    assert pedidos["resumo"] == {
        "pedidos": 2,
        "unidades": 6.0,
        "valor_total": 300.0,
        "ticket_medio": 150.0,
    }
    assert {item["empresa_nome"] for item in pedidos["itens"]} == {"Loja A", "Loja B"}
    assert pedidos_compra["resumo"] == {
        "pedidos": 2,
        "em_andamento": 1,
        "sugeridos_ia": 1,
        "valor_total": 300.0,
    }
    assert {item["fornecedor_nome"] for item in pedidos_compra["itens"]} == {
        "Cliente A",
        "Cliente B",
    }
    assert contas["resumo"] == {
        "contas": 2,
        "valor_total": 300.0,
        "valor_pago": 40.0,
        "saldo_aberto": 260.0,
        "saldo_vencido": 180.0,
    }
    assert contas["itens"][0]["empresa_nome"] == "Loja B"
    assert contas["itens"][0]["vencida"] is True


def test_consolida_produtos_automaticamente_por_ean_e_pesquisa_por_sku(db_local):
    grupo, referencias = _preparar(db_local)
    service = EmpresaGrupoAnaliseDetalhesService(db_local, agora=AGORA)

    resultado = service.listar_produtos_vendidos(
        grupo.id, EMPRESA_A, periodo_dias=30, busca="RACAO-B"
    )

    assert resultado["resumo"]["produtos"] == 1
    produto = resultado["itens"][0]
    assert produto["tipo_vinculo"] == "ean"
    assert produto["quantidade"] == 4.0
    assert produto["valor_total"] == 300.0
    assert produto["estoque_grupo"] == 10.0
    assert {item["empresa_nome"] for item in produto["empresas"]} == {
        "Loja A",
        "Loja B",
    }

    referencias[EMPRESA_A]["produto_ean"].estoque_atual = -2
    referencias[EMPRESA_B]["produto_ean"].estoque_atual = -1
    db_local.commit()
    produto_sem_estoque = service.listar_produtos_vendidos(
        grupo.id, EMPRESA_A, periodo_dias=30, busca="RACAO-B"
    )["itens"][0]

    assert produto_sem_estoque["estoque_grupo"] == -3.0
    assert produto_sem_estoque["cobertura_dias"] == 0.0


def test_vinculo_manual_agrupa_skus_diferentes_e_pode_ser_removido(db_local):
    grupo, referencias = _preparar(db_local)
    service = EmpresaGrupoAnaliseDetalhesService(db_local, agora=AGORA)
    vinculos_service = EmpresaGrupoProdutoVinculoService(db_local, agora=AGORA)
    referencia_a = SimpleNamespace(
        empresa_id=EMPRESA_A,
        produto_id=referencias[EMPRESA_A]["produto_manual"].id,
    )
    referencia_b = SimpleNamespace(
        empresa_id=EMPRESA_B,
        produto_id=referencias[EMPRESA_B]["produto_manual"].id,
    )

    vinculo = vinculos_service.vincular_produtos(
        grupo.id, EMPRESA_A, 1, referencia_a, referencia_b
    )
    produtos = service.listar_produtos_vendidos(
        grupo.id, EMPRESA_A, periodo_dias=30, busca="Petisco"
    )

    assert vinculo["produto_a"]["empresa_nome"] == "Loja A"
    assert produtos["resumo"]["produtos"] == 1
    assert produtos["itens"][0]["tipo_vinculo"] == "manual"
    assert (
        vinculos_service.listar_vinculos(grupo.id, EMPRESA_A)["pode_gerenciar"] is True
    )

    with pytest.raises(HTTPException) as erro:
        vinculos_service.vincular_produtos(
            grupo.id, EMPRESA_B, 1, referencia_a, referencia_b
        )
    assert erro.value.status_code == 403

    vinculos_service.remover_vinculo(grupo.id, vinculo["id"], EMPRESA_A, 1)
    assert vinculos_service.listar_vinculos(grupo.id, EMPRESA_A)["itens"] == []


def test_empresa_fora_do_grupo_nao_acessa_detalhes(db_local):
    grupo, _referencias = _preparar(db_local)
    service = EmpresaGrupoAnaliseDetalhesService(db_local, agora=AGORA)

    with pytest.raises(HTTPException) as erro:
        service.listar_pedidos(grupo.id, EMPRESA_FORA)

    assert erro.value.status_code == 403
