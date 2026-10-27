"""Liquidar um repasse não representa nova venda nem nova comissão."""

import asyncio
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import Request
from sqlalchemy.schema import CreateTable

from app import contas_receber_recebimentos_routes as rotas
from app.comissoes_models import ComissaoItem
from app.contas_receber_schemas import RecebimentoCreate, RecebimentoLoteCreate
from app.financeiro_models import ContaReceber, Recebimento
from app.ia.aba5_models import FluxoCaixa
from app.idempotency_models import IdempotencyKey
from app.vendas_models import VendaPagamento

pytest_plugins = ["tests.unit.test_finalizacao_recebiveis_atomicidade"]
DIA = date(2026, 10, 26)


@pytest.fixture
def liquidacao(cenario, monkeypatch):
    c = cenario
    with c.db.get_bind().begin() as conn:
        for model in (FluxoCaixa, ComissaoItem, IdempotencyKey):
            conn.execute(
                CreateTable(model.__table__, include_foreign_key_constraints=[])
            )
    c.venda.total = c.venda.subtotal = Decimal("100")
    c.venda.status = "finalizada"
    c.venda.funcionario_id = 7
    c.usuario = SimpleNamespace(id=1, nome="Operador QA")
    c.auth = (c.usuario, c.tenant)
    monkeypatch.setattr(rotas, "carregar_config_encargos", lambda *_: None)
    c.gerador = Mock(return_value={"success": True, "total_comissao": 10})
    monkeypatch.setattr("app.comissoes_service.gerar_comissoes_venda", c.gerador)
    c.db.commit()
    return c


def _conta(c, pagamento):
    registro = ContaReceber(
        tenant_id=c.tenant,
        venda_id=c.venda.id,
        forma_pagamento_id=1,
        descricao="Repasse da operadora ou parcela de crediário",
        observacoes=f"[venda_pagamento:{pagamento.id}]",
        valor_original=100,
        valor_final=100,
        valor_recebido=0,
        status="pendente",
        user_id=1,
        dre_subcategoria_id=1,
        canal="loja_fisica",
        data_emissao=DIA,
        data_vencimento=DIA,
    )
    c.db.add(registro)
    c.db.commit()
    return registro


def _receber(c, registro, em_lote, chave):
    dados = (
        RecebimentoLoteCreate(
            conta_ids=[registro.id],
            data_recebimento=DIA,
            forma_pagamento_id=1,
            caixa_id=2,
        )
        if em_lote
        else RecebimentoCreate(
            valor_recebido=100, data_recebimento=DIA, forma_pagamento_id=1, caixa_id=2
        )
    )
    path = (
        "/contas-receber/receber-lote"
        if em_lote
        else f"/contas-receber/{registro.id}/receber"
    )

    async def body():
        return {"type": "http.request", "body": dados.model_dump_json().encode()}

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": path,
            "headers": [(b"idempotency-key", chave.encode())],
            "query_string": b"",
            "server": ("localhost", 8000),
            "scheme": "http",
            "path_params": {} if em_lote else {"conta_id": registro.id},
        },
        receive=body,
    )
    opcoes = {"request": request, "db": c.db, "user_and_tenant": c.auth}
    return asyncio.run(
        rotas.registrar_recebimentos_lote(lote=dados, **opcoes)
        if em_lote
        else rotas.registrar_recebimento(
            conta_id=registro.id, recebimento=dados, **opcoes
        )
    )


@pytest.mark.parametrize("em_lote", [False, True])
@pytest.mark.parametrize(
    "tipo,valor", [("percentual", "10"), ("lucro", "5"), ("fixo", "3.25")]
)
def test_repasse_liquidado_e_reenviado_preserva_comissao_original(
    liquidacao, em_lote, tipo, valor
):
    c = liquidacao
    pagamento = VendaPagamento(
        tenant_id=c.tenant,
        venda_id=c.venda.id,
        forma_pagamento="Cartão de crédito",
        valor=100,
    )
    c.db.add(pagamento)
    c.db.add(
        ComissaoItem(
            tenant_id=c.tenant,
            venda_id=c.venda.id,
            funcionario_id=c.venda.funcionario_id,
            data_venda=DIA,
            tipo_calculo=tipo,
            valor_comissao=Decimal(valor),
            valor_comissao_gerada=Decimal(valor),
            parcela_numero=1,
            status="pendente",
        )
    )
    c.db.commit()
    registro = _conta(c, pagamento)
    chave = str(uuid4())
    _receber(c, registro, em_lote, chave)
    repetido = _receber(c, registro, em_lote, chave)

    assert repetido.status_code == 200
    assert repetido.headers["X-Idempotency-Replayed"] == "true"
    assert registro.status == "recebido" and registro.valor_recebido == Decimal("100")
    assert c.db.query(Recebimento).count() == 1
    assert c.db.query(FluxoCaixa).filter_by(status="realizado").one().valor == 100
    assert c.db.query(ComissaoItem).count() == 1
    assert c.db.query(ComissaoItem).one().valor_comissao_gerada == Decimal(valor)
    c.gerador.assert_not_called()


@pytest.mark.parametrize("em_lote", [False, True])
def test_crediario_com_marcador_continua_gerando_comissao_uma_vez(liquidacao, em_lote):
    c = liquidacao
    plano = VendaPagamento(
        tenant_id=c.tenant,
        venda_id=c.venda.id,
        forma_pagamento="Crediário",
        forma_pagamento_id=1,
        valor=100,
    )
    c.db.add(plano)
    c.db.commit()
    registro = _conta(c, plano)
    chave = str(uuid4())
    _receber(c, registro, em_lote, chave)
    _receber(c, registro, em_lote, chave)
    c.gerador.assert_called_once()
    assert c.gerador.call_args.kwargs["tenant_id"] == c.tenant
    assert c.gerador.call_args.kwargs["valor_pago"] == Decimal("100")
    assert c.db.query(Recebimento).count() == 1


def test_guard_nao_gera_comissao_de_conta_de_outra_empresa(liquidacao):
    c = liquidacao
    conta_alheia = SimpleNamespace(tenant_id=uuid4(), venda_id=c.venda.id)
    assert (
        rotas._gerar_comissao_baixa_lote(c.db, conta_alheia, c.tenant, 1, 100) is None
    )
    c.gerador.assert_not_called()
