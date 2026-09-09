"""Provas de saldo e estoque com devolucoes sucessivas em banco isolado."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.sql.sqltypes import Uuid

from app import (  # noqa: F401 - registra relacoes dos modelos no banco isolado
    caixa_models,
    ecommerceai_integration_models,
    ofertas_estudio_models,
    vendas_models,
)

from app.estoque import service as estoque_service
from app.estoque.transferencia_parceiro_baixa_routes import (
    registrar_recebimento_transferencia_parceiro,
)
from app.estoque.transferencia_parceiro_baixa_lote_service import (
    _estornar_estoque_transferencia,
)
from app.estoque.transferencia_parceiro_devolucao_service import (
    buscar_resumos_devolucao,
    preparar_devolucao,
)
from app.estoque.transferencia_parceiro_schemas import (
    TransferenciaParceiroRecebimentoRequest,
)
from app.financeiro_models import ContaReceber, Recebimento, LancamentoManual
from app.models import Cliente
from app.produtos_models import Produto, EstoqueMovimentacao


@pytest.fixture
def dados(tenant_context, monkeypatch):
    # PostgreSQL aceita UUID como string; o adaptador SQLite exige o objeto UUID.
    processador_original = Uuid.bind_processor

    def processador_sqlite(tipo, dialect):
        processador = processador_original(tipo, dialect)
        if dialect.name != "sqlite" or not tipo.as_uuid or not processador:
            return processador
        return lambda valor: processador(
            UUID(valor) if isinstance(valor, str) else valor
        )

    monkeypatch.setattr(Uuid, "bind_processor", processador_sqlite)
    engine = create_engine("sqlite://")
    for modelo in (
        Cliente,
        ContaReceber,
        Produto,
        EstoqueMovimentacao,
        Recebimento,
        LancamentoManual,
    ):
        modelo.__table__.create(engine)
    tenant = uuid4()
    tenant_context(tenant)
    # As integracoes externas ficam fora da prova; estoque e conta usam o servico real.
    monkeypatch.setattr(
        estoque_service, "_agenda_sync_bling", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        estoque_service.EstoqueService,
        "_ajustar_estoque_canal_online",
        lambda *_args, **_kwargs: None,
    )
    with Session(engine) as db:
        for ident, nome, quantidade, total in (
            (1, "Cimalgex", 8, 109.21),
            (2, "Doxifin", 3, 63.45),
        ):
            db.execute(
                Produto.__table__.insert().values(
                    id=ident,
                    tenant_id=tenant,
                    nome=nome,
                    codigo=str(ident),
                    estoque_atual=10,
                    preco_custo=total / quantidade,
                    user_id=1,
                    tipo_produto="SIMPLES",
                )
            )
            db.execute(
                EstoqueMovimentacao.__table__.insert().values(
                    id=ident,
                    tenant_id=tenant,
                    produto_id=ident,
                    tipo="saida",
                    motivo="transf_parceiro",
                    referencia_id=100,
                    referencia_tipo="transferencia_parceiro",
                    quantidade=quantidade,
                    custo_unitario=round(total / quantidade, 2),
                    valor_total=total,
                    user_id=1,
                )
            )
        db.execute(
            ContaReceber.__table__.insert().values(
                id=100,
                tenant_id=tenant,
                descricao="Transferencia de teste",
                documento="TRP-100",
                valor_original=172.66,
                valor_final=172.66,
                valor_recebido=0,
                data_emissao=date(2026, 9, 4),
                data_vencimento=date(2026, 9, 30),
                status="pendente",
                user_id=1,
                canal="transferencia_parceiro",
                dre_subcategoria_id=1,
            )
        )
        db.commit()

        def baixar(valor, itens, **extras):
            payload = TransferenciaParceiroRecebimentoRequest(
                valor_recebido=valor,
                modo_baixa="produto_devolvido",
                devolver_estoque=True,
                itens_devolucao=[
                    {"produto_id": ident, "quantidade": qtd} for ident, qtd in itens
                ],
                **extras,
            )
            return registrar_recebimento_transferencia_parceiro.__wrapped__(
                100, payload, db=db, user_and_tenant=(SimpleNamespace(id=1), tenant)
            )

        yield SimpleNamespace(db=db, tenant=tenant, baixar=baixar)
    engine.dispose()


def test_duas_devolucoes_parciais_e_final_mantem_estoque_saldo_e_centavos(dados):
    primeira = dados.baixar(27.30, [(1, 2)])
    assert primeira["status"] == "parcial"
    assert primeira["saldo_aberto"] == 145.36
    assert dados.db.get(Produto, 1).estoque_atual == 12
    assert dados.db.get(Produto, 2).estoque_atual == 10

    segunda = dados.baixar(48.46, [(1, 2), (2, 1)])
    assert segunda["saldo_aberto"] == 96.90
    resumo = buscar_resumos_devolucao(
        dados.db, tenant_id=dados.tenant, conta_ids=[100]
    )[100]
    assert [item["quantidade_disponivel"] for item in resumo["itens"]] == [4, 2]
    assert len(resumo["devolucoes"]) == 3

    final = dados.baixar(96.90, [(1, 4), (2, 2)])
    assert final["saldo_aberto"] == 0
    assert final["status"] == "recebido"
    assert dados.db.get(Produto, 1).estoque_atual == 18
    assert dados.db.get(Produto, 2).estoque_atual == 13
    assert dados.db.query(Recebimento).count() == 0
    assert dados.db.query(LancamentoManual).count() == 0
    assert "Cimalgex x 4" in dados.db.get(ContaReceber, 100).observacoes
    with pytest.raises(HTTPException):
        dados.baixar(13.65, [(1, 1)])
    assert dados.db.get(Produto, 1).estoque_atual == 18


@pytest.mark.parametrize(
    "valor,itens,erro",
    [
        (27.30, [(1, 9)], "restante"),
        (27.30, [(999, 2)], "invalido"),
        (27.30, [(1, 1), (1, 1)], "repetido"),
        (27.29, [(1, 2)], "corresponder"),
        (27.30, [], "pelo menos"),
        (27.30, [(1, 0.0001)], "3 casas"),
    ],
)
def test_rejeita_pedidos_invalidos_sem_alterar_conta_ou_estoque(
    dados, valor, itens, erro
):
    with pytest.raises(HTTPException, match=erro):
        dados.baixar(valor, itens)
    assert dados.db.get(ContaReceber, 100).valor_recebido == 0
    assert dados.db.get(Produto, 1).estoque_atual == 10
    assert dados.db.query(EstoqueMovimentacao).count() == 2


def test_nao_repete_quantidade_ja_devolvida(dados):
    dados.baixar(81.91, [(1, 6)])
    with pytest.raises(HTTPException, match="restante"):
        dados.baixar(40.95, [(1, 3)])
    assert dados.db.get(Produto, 1).estoque_atual == 16


def test_finalizacao_em_lote_devolve_apenas_o_restante(dados):
    dados.baixar(27.30, [(1, 2)])
    ids = _estornar_estoque_transferencia(
        dados.db,
        conta=dados.db.get(ContaReceber, 100),
        user_id=1,
        tenant_id=dados.tenant,
        observacao="Finalizacao em lote",
    )
    assert len(ids) == 2
    assert dados.db.get(Produto, 1).estoque_atual == 18
    assert dados.db.get(Produto, 2).estoque_atual == 13


def test_isolamento_por_empresa_e_transferencia(dados):
    assert buscar_resumos_devolucao(dados.db, tenant_id=uuid4(), conta_ids=[100]) == {}
    assert (
        buscar_resumos_devolucao(dados.db, tenant_id=dados.tenant, conta_ids=[999])
        == {}
    )


def test_devolucao_apos_pagamento_nao_pode_exceder_saldo(dados):
    conta = dados.db.get(ContaReceber, 100)
    conta.valor_recebido = Decimal("160.00")
    dados.db.commit()
    with pytest.raises(HTTPException, match="saldo"):
        dados.baixar(27.30, [(1, 2)])
    assert dados.db.get(Produto, 1).estoque_atual == 10


def test_quantidade_fracionada_e_total_original_prevalecem_sobre_custo_arredondado():
    item = dict(
        produto_id=1,
        produto_nome="Racao",
        quantidade=1.5,
        quantidade_devolvida=0,
        quantidade_disponivel=1.5,
        valor_total=10,
        valor_devolvido=0,
    )
    preparados, total = preparar_devolucao(
        [item], [SimpleNamespace(produto_id=1, quantidade=0.5)]
    )
    assert total == Decimal("3.33")
    assert preparados[0]["quantidade"] == 0.5


def test_falha_na_segunda_entrada_desfaz_estoque_e_baixa(dados, monkeypatch):
    original = estoque_service.EstoqueService.estornar_estoque

    def falhar_segundo(**kwargs):
        if kwargs["produto_id"] == 2:
            raise ValueError("Falha simulada")
        return original(**kwargs)

    monkeypatch.setattr(
        estoque_service.EstoqueService, "estornar_estoque", falhar_segundo
    )
    with pytest.raises(ValueError, match="Falha simulada"):
        dados.baixar(48.45, [(1, 2), (2, 1)])
    assert dados.db.get(ContaReceber, 100).valor_recebido == 0
    assert dados.db.get(Produto, 1).estoque_atual == 10
    assert dados.db.get(Produto, 2).estoque_atual == 10
    assert dados.db.query(EstoqueMovimentacao).count() == 2


def test_cliente_antigo_ainda_pode_devolver_remessa_inteira_sem_baixa(dados):
    payload = TransferenciaParceiroRecebimentoRequest(
        valor_recebido=172.66,
        modo_baixa="produto_devolvido",
        devolver_estoque=True,
    )
    resultado = registrar_recebimento_transferencia_parceiro.__wrapped__(
        100,
        payload,
        db=dados.db,
        user_and_tenant=(SimpleNamespace(id=1), dados.tenant),
    )
    assert resultado["saldo_aberto"] == 0
    assert dados.db.get(Produto, 1).estoque_atual == 18
