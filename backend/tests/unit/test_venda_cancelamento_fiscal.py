"""Regressões do cancelamento fiscal seguido do cancelamento da venda."""

from types import SimpleNamespace
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.intnfe import emission
from app.vendas import cancelamento_service
from app.vendas_models import Venda


def _venda(status="pago_nf", nfe_status="autorizada"):
    return SimpleNamespace(
        id=12,
        tenant_id=uuid4(),
        numero_venda="202610200012",
        status=status,
        nfe_provider="intnfe",
        nfe_status=nfe_status,
        nfe_tipo="nfce",
        nfe_modelo="65",
        nfe_correlation_id="corr-nota-18574",
        nfe_ambiente=1,
        nfe_numero=18574,
        nfe_serie=1,
        nfe_chave="1" * 44,
        nfe_protocolo="123",
        nfe_xml="<xml />",
        nfe_codigo_erro=None,
        nfe_motivo_rejeicao=None,
        nfe_cancelamento_status=None,
        nfe_cancelamento_codigo=None,
        nfe_cancelamento_motivo=None,
        nfe_cancelamento_solicitado_em=None,
    )


@pytest.mark.parametrize(
    ("codigo_emissor", "situacao", "status_venda"),
    [
        (5, "cancelada", "finalizada"),
        (3, "autorizada", "pago_nf"),
        (2, "autorizada", "pago_nf"),
    ],
)
def test_solicitacao_so_libera_venda_quando_emissor_confirma_cancelamento(
    monkeypatch, codigo_emissor, situacao, status_venda
):
    venda = _venda()
    db = MagicMock()
    api = MagicMock()
    api.cancel_document.return_value = {"success": True}
    api.document_status.return_value = {"status": codigo_emissor}
    api.document_events.return_value = []
    monkeypatch.setattr(emission, "_connection", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(emission, "_access_token", lambda *_args: "token-teste")
    monkeypatch.setattr(emission, "_remember_sequence_start", lambda *_args: None)
    monkeypatch.setattr(emission, "tentar_enfileirar_documento", lambda *_args: None)

    resultado = emission.cancel(db, venda, api, "Cancelamento solicitado pelo cliente")

    assert resultado["cancelamento_solicitado"] is (codigo_emissor != 5)
    assert resultado["situacao"] == situacao
    assert venda.nfe_status == situacao
    assert venda.status == status_venda
    api.cancel_document.assert_called_once()
    api.document_status.assert_called_once_with(
        "token-teste", "nfce", venda.nfe_correlation_id
    )
    assert db.commit.call_count == 2
    # A nota cancelada apenas destrava a venda; o estoque/financeiro continuam
    # sendo responsabilidade do cancelamento explícito da venda.
    db.query.assert_not_called()
    db.delete.assert_not_called()


@pytest.mark.parametrize(
    "status_venda", ["cancelada", "finalizada_devolucao", "baixa_parcial"]
)
def test_consulta_fiscal_nao_ressuscita_venda_cancelada_ou_devolvida(
    monkeypatch, status_venda
):
    venda = _venda(status=status_venda)
    api = MagicMock()
    api.document_status.return_value = {"status": 5}
    api.document_events.return_value = []
    monkeypatch.setattr(emission, "tentar_enfileirar_documento", lambda *_args: None)

    emission.reconcile(
        MagicMock(), venda, api, connection=object(), token="token-teste"
    )

    assert venda.nfe_status == "cancelada"
    assert venda.status == status_venda


@pytest.mark.parametrize(
    "status_concorrente", ["cancelada", "finalizada_devolucao", "pago_nf"]
)
def test_reconciliacao_rele_status_comercial_alterado_enquanto_aguarda_emissor(
    monkeypatch, tmp_path, status_concorrente
):
    from sqlalchemy import Column, DateTime, Integer, String, Uuid, create_engine
    from sqlalchemy.orm import declarative_base, sessionmaker

    # Duas sessões reais: a consulta fiscal carrega pago_nf, enquanto outra
    # operação conclui antes da resposta do emissor. O objeto da consulta fica
    # desatualizado e não pode sobrescrever o cancelamento/devolução concorrente.
    Base = declarative_base()

    class VendaConcorrente(Base):
        __tablename__ = "venda_concorrente"
        id = Column(Integer, primary_key=True)
        tenant_id = Column(Uuid, nullable=False)
        status = Column(String, nullable=False)
        nfe_status = Column(String, nullable=False)
        nfe_cancelamento_status = Column(String, nullable=True)
        nfe_cancelamento_codigo = Column(String, nullable=True)
        nfe_cancelamento_motivo = Column(String, nullable=True)
        nfe_cancelamento_solicitado_em = Column(DateTime(timezone=True), nullable=True)

    engine = create_engine(f"sqlite:///{(tmp_path / 'concorrencia.db').as_posix()}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine, expire_on_commit=False)
    tenant_id = uuid4()
    from app.tenancy.context import set_current_tenant

    set_current_tenant(tenant_id)
    with Session() as cadastro:
        registro = VendaConcorrente(
            tenant_id=tenant_id, status="pago_nf", nfe_status="autorizada"
        )
        cadastro.add(registro)
        cadastro.commit()
        venda_id = registro.id

    monkeypatch.setattr(emission, "tentar_enfileirar_documento", lambda *_args: None)
    with Session() as consulta_fiscal:
        venda = consulta_fiscal.get(VendaConcorrente, venda_id)
        for campo, valor in vars(_venda()).items():
            if campo.startswith("nfe_") and campo != "nfe_status":
                setattr(venda, campo, valor)
        assert venda.status == "pago_nf"

        def resposta_emissor(*_args):
            with Session() as outra_operacao:
                atual = outra_operacao.get(VendaConcorrente, venda_id)
                atual.status = status_concorrente
                outra_operacao.commit()
            assert venda.status == "pago_nf"
            return {"status": 5}

        api = SimpleNamespace(
            document_status=resposta_emissor, document_events=lambda *_args: []
        )
        emission.reconcile(
            consulta_fiscal, venda, api, connection=object(), token="token-teste"
        )

        esperado = (
            "finalizada" if status_concorrente == "pago_nf" else status_concorrente
        )
        assert venda.status == esperado

    with Session() as conferencia:
        persistida = conferencia.get(VendaConcorrente, venda_id)
        assert persistida.status == esperado
        assert persistida.nfe_status == "cancelada"
        assert persistida.tenant_id == tenant_id
    engine.dispose()


def test_cancelamento_tenant_incorreto_nao_encontra_venda_nem_executa_estornos(
    monkeypatch,
):
    venda = _venda()
    outro_tenant = uuid4()
    db = MagicMock()
    consulta = db.query.return_value
    consulta.filter_by.return_value = consulta
    consulta.with_for_update.return_value = consulta
    consulta.first.return_value = None
    monkeypatch.setattr("app.tenancy.context.set_tenant_context", lambda *_args: None)

    with pytest.raises(HTTPException, match="não encontrada") as erro:
        cancelamento_service.cancelar_venda(
            venda.id, "Cliente pediu cancelamento", 7, outro_tenant, db
        )

    assert erro.value.status_code == 404
    db.query.assert_called_once_with(Venda)
    consulta.filter_by.assert_called_once_with(id=venda.id, tenant_id=outro_tenant)
    db.delete.assert_not_called()
    db.add.assert_not_called()
    db.commit.assert_not_called()
    db.rollback.assert_called_once()
    assert venda.status == "pago_nf"


@pytest.mark.parametrize(
    ("quantidade_legado", "quantidade_itens"), [(0, 1), (0.4, 1), (1, 1), (1.4, 2)]
)
def test_cancelamento_venda_com_nota_cancelada_preserva_fiscal_e_estorna_uma_vez(
    monkeypatch, quantidade_legado, quantidade_itens
):
    from app.produtos_estoque_models import EstoqueMovimentacao
    from app.produtos_models import Produto
    from app.vendas_models import VendaItem

    venda = _venda(nfe_status="cancelada")
    venda.nfe_bling_id = 987
    venda.cliente_id = None
    venda.funcionario_id = None
    venda.total = 39.9
    venda.tem_entrega = False
    venda.to_dict = lambda: {
        "id": venda.id,
        "status": venda.status,
        "nfe_status": venda.nfe_status,
    }
    item = SimpleNamespace(
        id=1,
        tenant_id=venda.tenant_id,
        venda_id=venda.id,
        tipo="produto",
        produto_id=20,
        quantidade=1,
        estoque_origem_tenant_id=None,
        product_variation_id=None,
        custo_original_saida=None,
        lote_id=None,
    )
    itens = [
        SimpleNamespace(**{**vars(item), "id": indice + 1})
        for indice in range(quantidade_itens)
    ]
    produto = SimpleNamespace(
        id=20,
        tenant_id=venda.tenant_id,
        controlar_estoque=True,
        tipo_produto="SIMPLES",
        tipo_kit=None,
        estoque_atual=Decimal("10")
        - quantidade_itens
        + Decimal(str(quantidade_legado)),
    )
    db = MagicMock()
    consulta_legado = None

    def query(model):
        nonlocal consulta_legado
        consulta = MagicMock()
        consulta.filter_by.return_value = consulta
        consulta.filter.return_value = consulta
        consulta.with_for_update.return_value = consulta
        consulta.populate_existing.return_value = consulta
        consulta.order_by.return_value = consulta
        consulta.first.return_value = venda if model is Venda else None
        consulta.one_or_none.return_value = produto if model is Produto else None
        consulta.all.return_value = itens if model is VendaItem else []
        if model is EstoqueMovimentacao:
            consulta_legado = consulta
            consulta.all.return_value = [
                SimpleNamespace(
                    quantidade=quantidade_legado,
                    tipo="saida",
                    status="cancelado",
                    referencia_tipo="venda_bling",
                    lote_id=None,
                    lotes_consumidos=None,
                )
            ]
        return consulta

    db.query.side_effect = query
    monkeypatch.setattr("app.tenancy.context.set_tenant_context", lambda *_args: None)
    estoque = Decimal("10") - quantidade_itens + Decimal(str(quantidade_legado))

    def devolver(**kwargs):
        nonlocal estoque
        anterior = estoque
        estoque += Decimal(str(kwargs["quantidade"]))
        return {
            "produto_nome": "Produto",
            "estoque_anterior": anterior,
            "estoque_novo": estoque,
        }

    estornar = MagicMock(side_effect=devolver)
    monkeypatch.setattr("app.estoque.service.EstoqueService.estornar_estoque", estornar)
    for caminho in (
        "app.audit_log.log_action",
        "app.campaigns.coupon_service.reverse_coupon_redemptions_for_sale",
        "app.campaigns.loyalty_service.void_loyalty_stamps_for_sale",
        "app.vendas.cashback_financeiro.cancelar_despesas_cashback_venda",
    ):
        monkeypatch.setattr(caminho, lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "app.comissoes_estorno.estornar_comissoes_venda",
        lambda **_kwargs: {"success": True, "comissoes_estornadas": 0},
    )
    monkeypatch.setattr(
        cancelamento_service,
        "invalidate_venda_rentabilidade_snapshot",
        lambda *_args: None,
    )

    resultado = cancelamento_service.cancelar_venda(
        venda.id, "Cliente pediu cancelamento", 7, venda.tenant_id, db
    )

    assert resultado["venda"]["status"] == "cancelada"
    assert resultado["venda"]["nfe_status"] == "cancelada"
    assert estoque == Decimal("10")
    assert resultado["estornos"]["itens_estornados"] == (
        0 if quantidade_legado == 1 else 1
    )
    assert estornar.call_count == (0 if quantidade_legado == 1 else 1)
    if estornar.called:
        assert estornar.call_args.kwargs["tenant_id"] == venda.tenant_id
    consulta_legado.filter_by.assert_called_once_with(
        tenant_id=venda.tenant_id,
        referencia_id=venda.id,
        referencia_tipo="venda_bling",
        produto_id=item.produto_id,
        tipo="saida",
        status="cancelado",
    )
    db.commit.assert_called_once()

    with pytest.raises(HTTPException, match="já está cancelada"):
        cancelamento_service.cancelar_venda(
            venda.id, "Cliente pediu cancelamento", 7, venda.tenant_id, db
        )
    assert estoque == Decimal("10")
    assert estornar.call_count == (0 if quantidade_legado == 1 else 1)


@pytest.mark.asyncio
@pytest.mark.parametrize("confirmado", [True, False])
async def test_bling_so_libera_venda_apos_consultar_cancelamento_confirmado(
    monkeypatch, confirmado
):
    from app.nfe import operacional_routes

    venda = _venda()
    venda.nfe_bling_id = 987
    api = MagicMock()
    api.consultar_nfce.return_value = {
        "situacao": 4 if confirmado else 5,
        "chaveAcesso": venda.nfe_chave,
    }
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = venda
    monkeypatch.setattr(operacional_routes, "BlingAPI", lambda: api)
    monkeypatch.setattr(
        operacional_routes, "_exigir_bling_configurado_para_tenant", lambda *_args: None
    )
    monkeypatch.setattr(
        operacional_routes, "_registrar_status_contabil_bling", lambda *_args: None
    )

    resultado = await operacional_routes.cancelar_nfe(
        venda.nfe_bling_id,
        operacional_routes.CancelarNFeRequest(
            justificativa="Cancelamento a pedido do cliente"
        ),
        db=db,
        user_and_tenant=(SimpleNamespace(id=7), venda.tenant_id),
    )

    assert resultado["processando"] is not confirmado
    assert resultado["cancelamento_solicitado"] is not confirmado
    assert venda.status == ("finalizada" if confirmado else "pago_nf")
    assert venda.nfe_status.lower() == ("cancelada" if confirmado else "autorizada")
    api.consultar_nfce.assert_called_once_with(987)
    api.consultar_nfe.assert_not_called()


@pytest.mark.asyncio
async def test_webhook_cancelamento_fiscal_bling_nao_devolve_estoque(monkeypatch):
    from app.nfe import operacional_routes

    venda = _venda()
    venda.nfe_bling_id = 987
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = venda
    api = MagicMock()
    api.consultar_nfce.return_value = {"situacao": 4}
    request = SimpleNamespace(json=MagicMock())

    async def dados():
        return {"topic": "nfce", "id": 987}

    request.json = dados
    monkeypatch.setattr(operacional_routes, "BlingAPI", lambda: api)
    monkeypatch.setattr(
        operacional_routes, "bling_tenant_id_configurado", lambda: venda.tenant_id
    )
    monkeypatch.setattr(operacional_routes, "sync_rls_tenant", lambda *_args: None)
    monkeypatch.setattr(
        operacional_routes, "_registrar_status_contabil_bling", lambda *_args: None
    )

    resultado = await operacional_routes.webhook_bling(request, db=db)

    assert resultado["success"] is True
    assert venda.nfe_status == "Cancelada"
    assert venda.status == "finalizada"
    db.query.assert_called_once_with(Venda)
    db.add.assert_not_called()
    db.delete.assert_not_called()


@pytest.mark.asyncio
async def test_bling_consulta_indisponivel_nao_confirma_cancelamento(monkeypatch):
    from app.nfe import operacional_routes

    venda = _venda()
    api = MagicMock()
    api.consultar_nfce.side_effect = RuntimeError("Consulta indisponível")
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = venda
    monkeypatch.setattr(operacional_routes, "BlingAPI", lambda: api)
    monkeypatch.setattr(
        operacional_routes, "_exigir_bling_configurado_para_tenant", lambda *_args: None
    )

    resultado = await operacional_routes.cancelar_nfe(
        987,
        operacional_routes.CancelarNFeRequest(
            justificativa="Cancelamento a pedido do cliente"
        ),
        db=db,
        user_and_tenant=(SimpleNamespace(id=7), venda.tenant_id),
    )

    assert resultado["cancelamento_solicitado"] is True
    assert resultado["processando"] is True
    assert resultado["success"] is False
    assert venda.nfe_status == "autorizada"
    assert venda.status == "pago_nf"
    db.rollback.assert_called_once()


@pytest.mark.parametrize("status_nota", ["autorizada", "cancelada"])
def test_reabertura_legada_depende_do_cancelamento_fiscal_confirmado(
    monkeypatch, status_nota
):
    from app.vendas import status_routes

    venda = _venda(nfe_status=status_nota)
    venda.funcionario_id = None
    venda.cliente_id = None
    venda.to_dict = lambda: {"status": venda.status, "nfe_status": venda.nfe_status}
    db = MagicMock()
    consulta = db.query.return_value
    consulta.filter_by.return_value = consulta
    consulta.populate_existing.return_value = consulta
    consulta.with_for_update.return_value = consulta
    consulta.first.return_value = venda
    for caminho in (
        "app.campaigns.coupon_service.reverse_coupon_redemptions_for_sale",
        "app.campaigns.loyalty_service.void_loyalty_stamps_for_sale",
        "app.campaigns.sale_reopening_service.void_quick_repurchase_coupons_for_sale",
        "app.vendas.cashback_financeiro.remover_pagamentos_cashback_venda",
        "app.vendas.cashback_financeiro.cancelar_despesas_cashback_venda",
        "app.services.business_audit_service.build_sale_reopened_metadata",
        "app.services.business_audit_service.log_business_event",
    ):
        monkeypatch.setattr(caminho, lambda *_args, **_kwargs: {})
    monkeypatch.setattr(status_routes, "log_action", lambda **_kwargs: None)
    monkeypatch.setattr(
        status_routes, "invalidate_venda_rentabilidade_snapshot", lambda *_args: None
    )

    if status_nota == "autorizada":
        with pytest.raises(HTTPException, match="Cancele a nota fiscal primeiro"):
            status_routes.reabrir_venda(
                venda.id,
                db=db,
                user_and_tenant=(SimpleNamespace(id=7), venda.tenant_id),
            )
        assert venda.status == "pago_nf"
        db.commit.assert_not_called()
    else:
        resultado = status_routes.reabrir_venda(
            venda.id, db=db, user_and_tenant=(SimpleNamespace(id=7), venda.tenant_id)
        )
        assert resultado == {"status": "aberta", "nfe_status": "cancelada"}
        consulta.filter_by.assert_called_once_with(
            id=venda.id, tenant_id=venda.tenant_id
        )
        db.commit.assert_called_once()
