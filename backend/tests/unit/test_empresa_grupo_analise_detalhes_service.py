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
from app.empresa_grupo_planejamento_service import (
    EmpresaGrupoPlanejamentoService,
)
from app.empresa_grupo_produto_vinculo_service import (
    EmpresaGrupoProdutoVinculoService,
)
from app.financeiro_models import ContaPagar, ContaReceber
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


def _receber(descricao, valor, recebido, vencimento, cliente_id):
    return ContaReceber(
        descricao=descricao,
        cliente_id=cliente_id,
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
                    _receber(
                        f"Cliente {prefixo}",
                        150 if prefixo == "A" else 80,
                        50 if prefixo == "A" else 0,
                        date(2026, 8, 22) if prefixo == "A" else date(2026, 9, 10),
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


def test_consolida_estoque_por_ean_quando_equivalente_nao_teve_venda(db_local):
    grupo, referencias = _preparar(db_local)
    produto_sem_venda = referencias[EMPRESA_B]["produto_ean"]
    with tenant_context(EMPRESA_B):
        item_vendido = (
            db_local.query(VendaItem)
            .filter(VendaItem.produto_id == produto_sem_venda.id)
            .one()
        )
        db_local.delete(item_vendido)
    db_local.commit()

    service = EmpresaGrupoAnaliseDetalhesService(db_local, agora=AGORA)
    resultado = service.listar_produtos_vendidos(
        grupo.id, EMPRESA_A, periodo_dias=30, busca="RACAO-B"
    )

    assert resultado["resumo"]["produtos"] == 1
    produto = resultado["itens"][0]
    assert produto["tipo_vinculo"] == "ean"
    assert produto["quantidade"] == 2.0
    assert produto["valor_total"] == 100.0
    assert produto["estoque_grupo"] == 10.0
    assert {item["empresa_nome"] for item in produto["empresas"]} == {
        "Loja A",
        "Loja B",
    }
    detalhe_sem_venda = next(
        item for item in produto["empresas"] if item["empresa_id"] == EMPRESA_B
    )
    assert detalhe_sem_venda["quantidade"] == 0.0
    assert detalhe_sem_venda["valor_total"] == 0.0
    assert detalhe_sem_venda["pedidos"] == 0


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


def test_vinculo_manual_inclui_estoque_do_equivalente_sem_venda(db_local):
    grupo, referencias = _preparar(db_local)
    vinculos_service = EmpresaGrupoProdutoVinculoService(db_local, agora=AGORA)
    produto_a = referencias[EMPRESA_A]["produto_manual"]
    produto_b = referencias[EMPRESA_B]["produto_manual"]
    vinculos_service.vincular_produtos(
        grupo.id,
        EMPRESA_A,
        1,
        SimpleNamespace(empresa_id=EMPRESA_A, produto_id=produto_a.id),
        SimpleNamespace(empresa_id=EMPRESA_B, produto_id=produto_b.id),
    )
    with tenant_context(EMPRESA_B):
        item_vendido = (
            db_local.query(VendaItem).filter(VendaItem.produto_id == produto_b.id).one()
        )
        db_local.delete(item_vendido)
    db_local.commit()

    service = EmpresaGrupoAnaliseDetalhesService(db_local, agora=AGORA)
    resultado = service.listar_produtos_vendidos(
        grupo.id, EMPRESA_A, periodo_dias=30, busca="PET-B"
    )

    assert resultado["resumo"]["produtos"] == 1
    produto = resultado["itens"][0]
    assert produto["tipo_vinculo"] == "manual"
    assert produto["quantidade"] == 1.0
    assert produto["valor_total"] == 10.0
    assert produto["estoque_grupo"] == 6.0
    assert {item["empresa_nome"] for item in produto["empresas"]} == {
        "Loja A",
        "Loja B",
    }


def test_empresa_fora_do_grupo_nao_acessa_detalhes(db_local):
    grupo, _referencias = _preparar(db_local)
    service = EmpresaGrupoAnaliseDetalhesService(db_local, agora=AGORA)

    with pytest.raises(HTTPException) as erro:
        service.listar_pedidos(grupo.id, EMPRESA_FORA)

    assert erro.value.status_code == 403


def test_reposicao_inteligente_prioriza_transferencia_antes_da_compra(db_local):
    grupo, referencias = _preparar(db_local)
    referencias[EMPRESA_A]["produto_ean"].estoque_atual = 0
    referencias[EMPRESA_B]["produto_ean"].estoque_atual = 10
    db_local.commit()

    service = EmpresaGrupoPlanejamentoService(db_local, agora=AGORA)
    resultado = service.listar_reposicao_inteligente(
        grupo.id,
        EMPRESA_A,
        periodo_dias=30,
        dias_cobertura=30,
        busca="RACAO-B",
    )

    assert resultado["resumo"]["produtos_para_transferir"] == 1
    assert resultado["resumo"]["produtos_para_comprar"] == 0
    item = resultado["itens"][0]
    assert item["quantidade_compra_sugerida"] == 0
    assert item["transferencias_sugeridas"] == [
        {
            "empresa_origem_id": EMPRESA_B,
            "empresa_origem_nome": "Loja B",
            "produto_origem_id": referencias[EMPRESA_B]["produto_ean"].id,
            "sku_origem": "RACAO-B",
            "empresa_destino_id": EMPRESA_A,
            "empresa_destino_nome": "Loja A",
            "produto_destino_id": referencias[EMPRESA_A]["produto_ean"].id,
            "sku_destino": "RACAO-A",
            "quantidade": 2.0,
        }
    ]


def test_reposicao_inteligente_sugere_compra_para_deficit_do_grupo(db_local):
    grupo, referencias = _preparar(db_local)
    referencias[EMPRESA_A]["produto_ean"].estoque_atual = 0
    referencias[EMPRESA_B]["produto_ean"].estoque_atual = 0
    db_local.commit()

    service = EmpresaGrupoPlanejamentoService(db_local, agora=AGORA)
    resultado = service.listar_reposicao_inteligente(
        grupo.id,
        EMPRESA_A,
        periodo_dias=30,
        dias_cobertura=30,
        busca="7891000000011",
    )

    assert resultado["resumo"]["produtos_para_comprar"] == 1
    item = resultado["itens"][0]
    assert item["prioridade"] == "critico"
    assert item["quantidade_compra_sugerida"] == 4
    assert item["valor_compra_estimado"] == 40
    assert {empresa["compra_sugerida"] for empresa in item["empresas"]} == {2.0}


def test_reposicao_inteligente_conta_apenas_produtos_com_acao_ao_mostrar_todos(
    db_local,
):
    grupo, referencias = _preparar(db_local)
    referencias[EMPRESA_A]["produto_ean"].estoque_atual = 10
    referencias[EMPRESA_B]["produto_ean"].estoque_atual = 10
    db_local.commit()

    service = EmpresaGrupoPlanejamentoService(db_local, agora=AGORA)
    resultado = service.listar_reposicao_inteligente(
        grupo.id,
        EMPRESA_A,
        periodo_dias=30,
        dias_cobertura=30,
        busca="7891000000011",
        somente_acao=False,
    )

    assert resultado["resumo"]["produtos_analisados"] == 1
    assert resultado["resumo"]["produtos_com_acao"] == 0
    assert len(resultado["itens"]) == 1
    assert resultado["itens"][0]["prioridade"] == "normal"
    assert resultado["itens"][0]["quantidade_compra_sugerida"] == 0
    assert resultado["itens"][0]["transferencias_sugeridas"] == []


def test_analise_financeira_cruza_entradas_saidas_e_vencimentos(db_local):
    grupo, _referencias = _preparar(db_local)
    service = EmpresaGrupoPlanejamentoService(db_local, agora=AGORA)

    resultado = service.analisar_financeiro(grupo.id, EMPRESA_A)

    assert resultado["resumo"] == {
        "receber_aberto": 180.0,
        "pagar_aberto": 260.0,
        "saldo_liquido": -80.0,
        "receber_vencido": 0.0,
        "pagar_vencido": 180.0,
        "saldo_30_dias": 100.0,
        "inadimplencia_receber_percentual": 0.0,
        "atraso_pagar_percentual": 69.2,
    }
    faixas = {item["chave"]: item for item in resultado["faixas"]}
    assert faixas["vencido"]["pagar"] == 180.0
    assert faixas["hoje"]["receber"] == 100.0
    assert faixas["8_15"]["pagar"] == 80.0
    assert faixas["16_30"]["receber"] == 80.0
