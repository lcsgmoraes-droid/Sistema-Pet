"""Devolucoes reais em banco isolado recompõem apenas os lotes da venda."""

import json
from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Query, Session
from sqlalchemy.sql.sqltypes import Uuid

from app import caixa_models, ecommerceai_integration_models, ofertas_estudio_models  # noqa: F401
from app.estoque import service as estoque_service
from app.empresa_grupo_estoque_compartilhado_service import contexto_tenant_estoque
from app.financeiro_models import ContaReceber
from app.models import Cliente
from app.produtos_models import EstoqueMovimentacao, Produto, ProdutoLote
from app.vendas.devolucoes_routes import prever_devolucao, registrar_devolucao
from app.vendas_devolucoes_models import VendaDevolucao
from app.vendas_models import Venda, VendaItem, VendaPagamento


@pytest.fixture
def dados(tenant_context, monkeypatch):
    original = Uuid.bind_processor

    def adaptar_uuid(tipo, dialect):
        processador = original(tipo, dialect)
        if dialect.name != "sqlite" or not tipo.as_uuid or not processador:
            return processador
        return lambda valor: processador(
            UUID(valor) if isinstance(valor, str) else valor
        )

    monkeypatch.setattr(Uuid, "bind_processor", adaptar_uuid)
    monkeypatch.setattr(
        estoque_service, "_agenda_sync_bling", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        estoque_service.EstoqueService,
        "_ajustar_estoque_canal_online",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        estoque_service.EstoqueService,
        "_resolver_user_id_operacao",
        lambda **_kwargs: 1,
    )
    monkeypatch.setattr(
        "app.vendas.devolucoes_routes.log_action", lambda **_kwargs: None
    )
    monkeypatch.setattr(
        "app.campaigns.sale_return_service.preflight_purchase_benefits_on_return",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "app.campaigns.sale_return_service.reconcile_purchase_benefits_on_return",
        lambda *_args, **_kwargs: None,
    )
    engine = create_engine("sqlite://")
    for modelo in (
        Produto,
        ProdutoLote,
        EstoqueMovimentacao,
        Cliente,
        Venda,
        VendaItem,
        VendaPagamento,
        VendaDevolucao,
        ContaReceber,
    ):
        modelo.__table__.create(engine)
    db = Session(engine)
    tenant = uuid4()
    tenant_context(tenant)
    usuario = SimpleNamespace(id=1, nome="Atendente")

    def montar(
        *,
        compartilhado=False,
        duas_linhas=False,
        comprovantes=False,
        lotes_por_movimento=False,
    ):
        estoque_tenant = uuid4() if compartilhado else tenant
        db.execute(
            Produto.__table__.insert().values(
                id=11,
                tenant_id=estoque_tenant,
                user_id=1,
                nome="Sache",
                codigo="SACHE",
                tipo_produto="SIMPLES",
                estoque_atual=12,
            )
        )
        # O lote 99 e mais antigo no FIFO atual, mas nao pertence a esta venda.
        for ident, saldo, inicial, ordem, status in (
            (12, 0, 2, 2, "esgotado"),
            (13, 10, 13, 3, "ativo"),
            (99, 7, 7, 1, "ativo"),
        ):
            db.execute(
                ProdutoLote.__table__.insert().values(
                    id=ident,
                    produto_id=11,
                    tenant_id=estoque_tenant,
                    nome_lote=f"L-{ident}",
                    quantidade_disponivel=saldo,
                    quantidade_inicial=inicial,
                    ordem_entrada=ordem,
                    status=status,
                    data_validade=datetime.now() + timedelta(days=90),
                )
            )
        db.execute(
            Cliente.__table__.insert().values(
                id=47, tenant_id=tenant, user_id=1, nome="Cliente", credito=0
            )
        )
        db.execute(
            Venda.__table__.insert().values(
                id=8,
                tenant_id=tenant,
                user_id=1,
                vendedor_id=1,
                numero_venda="VEN-8",
                cliente_id=47,
                subtotal=25,
                total=23,
                desconto_valor=2,
                status="finalizada",
            )
        )
        itens = ((3, 2, 12, 91), (4, 3, 13, 92)) if duas_linhas else ((3, 5, None, 91),)
        for ident, quantidade, lote_id, saida_id in itens:
            prova = {
                "versao": 1,
                "origem": "baixa_estoque_venda",
                "venda_id": 8,
                "venda_item_id": ident,
                "produto_id": 11,
                "movimentacao_id": saida_id,
                "quantidade": str(quantidade),
                "tenant_estoque_id": str(estoque_tenant),
                "custo_total": "4.00",
            }
            db.execute(
                VendaItem.__table__.insert().values(
                    id=ident,
                    tenant_id=tenant,
                    venda_id=8,
                    tipo="produto",
                    produto_id=11,
                    quantidade=quantidade,
                    preco_unitario=5,
                    subtotal=quantidade * 5,
                    lote_id=None if comprovantes else lote_id,
                    custo_original_saida=prova if comprovantes else None,
                    estoque_origem_tenant_id=estoque_tenant if compartilhado else None,
                )
            )
        partes = (
            (
                (91, 2, [{"lote_id": 12, "quantidade": 2}]),
                (92, 3, [{"lote_id": 13, "quantidade": 3}]),
            )
            if duas_linhas
            else (
                (
                    91,
                    5,
                    [
                        {"lote_id": 12, "quantidade": 2},
                        {"lote_id": 13, "quantidade": 3},
                    ],
                ),
            )
        )
        if lotes_por_movimento:
            partes = (
                (
                    91,
                    2,
                    [
                        {"lote_id": 12, "quantidade": 1},
                        {"lote_id": 13, "quantidade": 1},
                    ],
                ),
                (
                    92,
                    3,
                    [
                        {"lote_id": 12, "quantidade": 1},
                        {"lote_id": 13, "quantidade": 2},
                    ],
                ),
            )
        for ident, quantidade, composicao in partes:
            db.execute(
                EstoqueMovimentacao.__table__.insert().values(
                    id=ident,
                    tenant_id=estoque_tenant,
                    produto_id=11,
                    tipo="saida",
                    motivo="venda",
                    referencia_id=8,
                    referencia_tipo="venda",
                    quantidade=quantidade,
                    lotes_consumidos=json.dumps(composicao),
                    user_id=1,
                    status="confirmado",
                )
            )
        db.commit()

        def devolver(quantidade, *, item_id=3, chave=None):
            return registrar_devolucao(
                8,
                {
                    "itens": [{"item_id": item_id, "quantidade": quantidade}],
                    "motivo": "Produto devolvido",
                    "gerar_credito": True,
                    "chave_operacao": chave or str(uuid4()),
                },
                db=db,
                user_and_tenant=(usuario, tenant),
            )

        def saldo_lote(ident):
            with contexto_tenant_estoque(estoque_tenant, tenant):
                lote = db.get(ProdutoLote, ident)
                db.refresh(lote)
                return lote.quantidade_disponivel

        return SimpleNamespace(
            db=db,
            tenant=tenant,
            estoque_tenant=estoque_tenant,
            usuario=usuario,
            devolver=devolver,
            saldo_lote=saldo_lote,
        )

    yield montar
    db.close()
    engine.dispose()


def test_previa_nao_altera_saldo_e_devolucao_integral_recompoe_lotes_originais(dados):
    caso = dados()
    previa = prever_devolucao(
        8,
        {"itens": [{"item_id": 3, "quantidade": 5}]},
        db=caso.db,
        user_and_tenant=(caso.usuario, caso.tenant),
    )
    assert previa["valor_total_devolucao"] == 23
    assert (caso.saldo_lote(12), caso.saldo_lote(13), caso.saldo_lote(99)) == (0, 10, 7)
    assert caso.db.query(VendaDevolucao).count() == 0
    resultado = caso.devolver(5)
    assert resultado["status_venda"] == "devolvida_total"
    assert resultado["valor_total_devolucao"] == 23
    assert (caso.saldo_lote(12), caso.saldo_lote(13), caso.saldo_lote(99)) == (2, 13, 7)
    assert caso.db.get(Produto, 11).estoque_atual == 17
    assert caso.db.get(Cliente, 47).credito == Decimal("23")
    entrada = caso.db.query(EstoqueMovimentacao).filter_by(tipo="entrada").one()
    assert [
        (p["lote_id"], p["quantidade"], p["venda_item_id"])
        for p in json.loads(entrada.lotes_consumidos)
    ] == [(12, 2, 3), (13, 3, 3)]
    assert caso.db.get(ProdutoLote, 12).status == "ativo"


def test_parciais_e_reenvio_idempotente_preservam_saldo_e_centavos(dados):
    caso = dados()
    chave = str(uuid4())
    primeira = caso.devolver(1, chave=chave)
    assert primeira["valor_total_devolucao"] == 4.6
    assert (caso.saldo_lote(12), caso.saldo_lote(13)) == (1, 10)
    caso.devolver(2)
    assert (caso.saldo_lote(12), caso.saldo_lote(13)) == (2, 11)
    caso.devolver(2)
    assert caso.devolver(1, chave=chave) == primeira
    assert (caso.saldo_lote(12), caso.saldo_lote(13), caso.saldo_lote(99)) == (2, 13, 7)
    assert caso.db.query(VendaDevolucao).count() == 3
    assert caso.db.get(Produto, 11).estoque_atual == 17
    assert caso.db.get(Cliente, 47).credito == Decimal("23")
    with pytest.raises(HTTPException) as erro:
        caso.devolver(1)
    assert erro.value.status_code == 400
    assert caso.saldo_lote(12) == 2


@pytest.mark.parametrize("comprovantes", [False, True])
def test_linhas_do_mesmo_sku_devolvem_o_lote_da_linha_selecionada(dados, comprovantes):
    caso = dados(duas_linhas=True, comprovantes=comprovantes)
    caso.devolver(2, item_id=4)
    assert (caso.saldo_lote(12), caso.saldo_lote(13)) == (0, 12)
    caso.devolver(1, item_id=4)
    assert (caso.saldo_lote(12), caso.saldo_lote(13)) == (0, 13)
    caso.devolver(2, item_id=3)
    assert (caso.saldo_lote(12), caso.saldo_lote(13)) == (2, 13)


def test_sku_repetido_sem_origem_por_linha_bloqueia_ambiguidade(dados):
    caso = dados(duas_linhas=True)
    for item in caso.db.query(VendaItem).all():
        item.lote_id = None
    caso.db.commit()
    with pytest.raises(HTTPException) as erro:
        caso.devolver(1, item_id=4)
    assert erro.value.status_code == 409
    assert (caso.saldo_lote(12), caso.saldo_lote(13)) == (0, 10)


def test_comprovantes_multilote_preservam_quantidade_de_cada_lote_por_linha(dados):
    caso = dados(duas_linhas=True, comprovantes=True, lotes_por_movimento=True)
    caso.devolver(3, item_id=4)
    assert (caso.saldo_lote(12), caso.saldo_lote(13)) == (1, 12)
    caso.devolver(1, item_id=3)
    assert (caso.saldo_lote(12), caso.saldo_lote(13)) == (2, 12)
    caso.devolver(1, item_id=3)
    assert (caso.saldo_lote(12), caso.saldo_lote(13)) == (2, 13)


def test_lote_principal_do_movimento_original_sem_json_e_rastreavel(dados):
    caso = dados(duas_linhas=True)
    for saida_id, lote_id in ((91, 12), (92, 13)):
        saida = caso.db.get(EstoqueMovimentacao, saida_id)
        saida.lotes_consumidos = None
        saida.lote_id = lote_id
    caso.db.commit()
    caso.devolver(1, item_id=4)
    assert (caso.saldo_lote(12), caso.saldo_lote(13)) == (0, 11)


def test_registro_bloqueia_produto_e_lotes_e_previa_so_consulta(dados, monkeypatch):
    caso = dados()
    bloqueados = []
    original = Query.with_for_update

    def observar(consulta, *args, **kwargs):
        bloqueados.append(consulta.column_descriptions[0].get("entity"))
        return original(consulta, *args, **kwargs)

    monkeypatch.setattr(Query, "with_for_update", observar)
    prever_devolucao(
        8,
        {"itens": [{"item_id": 3, "quantidade": 1}]},
        db=caso.db,
        user_and_tenant=(caso.usuario, caso.tenant),
    )
    assert bloqueados == []
    caso.devolver(1)
    assert Produto in bloqueados
    assert ProdutoLote in bloqueados


def test_falha_depois_do_estoque_desfaz_lotes_produto_credito_e_evento(
    dados, monkeypatch
):
    caso = dados()

    def falhar(*_args, **_kwargs):
        raise RuntimeError("Falha depois de recompor os lotes")

    monkeypatch.setattr(
        "app.campaigns.sale_return_service.reconcile_purchase_benefits_on_return",
        falhar,
    )
    with pytest.raises(HTTPException) as erro:
        caso.devolver(2)
    assert erro.value.status_code == 500
    assert (caso.saldo_lote(12), caso.saldo_lote(13)) == (0, 10)
    assert caso.db.get(Produto, 11).estoque_atual == 12
    assert caso.db.get(Cliente, 47).credito == 0
    assert caso.db.query(VendaDevolucao).count() == 0
    assert caso.db.query(EstoqueMovimentacao).filter_by(tipo="entrada").count() == 0


def test_devolucao_compartilhada_recompoe_lotes_na_empresa_dona(dados):
    caso = dados(compartilhado=True)
    caso.devolver(3)
    assert (caso.saldo_lote(12), caso.saldo_lote(13), caso.saldo_lote(99)) == (2, 11, 7)
    with contexto_tenant_estoque(caso.estoque_tenant, caso.tenant):
        assert caso.db.get(Produto, 11).estoque_atual == 15
        entrada = caso.db.query(EstoqueMovimentacao).filter_by(tipo="entrada").one()
        assert entrada.tenant_id == caso.estoque_tenant
    assert caso.db.query(VendaDevolucao).one().tenant_id == caso.tenant


@pytest.mark.parametrize("alvo", ["tenant", "produto", "ausente"])
def test_lote_de_outro_tenant_ou_produto_nao_pode_ser_recomposto(dados, alvo):
    caso = dados()
    lote = caso.db.get(ProdutoLote, 12)
    if alvo == "tenant":
        lote.tenant_id = uuid4()
    elif alvo == "produto":
        lote.produto_id = 999
    else:
        caso.db.delete(lote)
    caso.db.commit()
    with pytest.raises(HTTPException) as erro:
        caso.devolver(1)
    assert erro.value.status_code == 409
    assert caso.db.query(VendaDevolucao).count() == 0
    assert caso.db.get(Produto, 11).estoque_atual == 12
    assert caso.saldo_lote(13) == 10


@pytest.mark.parametrize(
    "historico",
    [
        "json_invalido",
        "quantidade_incompleta",
        "devolucao_sem_lotes",
        "devolucao_excessiva",
    ],
)
def test_historico_incompleto_ou_duplicado_nao_recompoe_lotes(dados, historico):
    caso = dados()
    if historico == "json_invalido":
        caso.db.get(EstoqueMovimentacao, 91).lotes_consumidos = "{invalido"
    elif historico == "quantidade_incompleta":
        caso.db.get(
            EstoqueMovimentacao, 91
        ).lotes_consumidos = '[{"lote_id": 12, "quantidade": 2}]'
    else:
        caso.db.add(
            EstoqueMovimentacao(
                tenant_id=caso.tenant,
                produto_id=11,
                tipo="entrada",
                motivo="devolucao",
                referencia_id=8,
                referencia_tipo="venda",
                quantidade=3,
                user_id=1,
                lotes_consumidos='[{"lote_id": 12, "quantidade": 3, "venda_item_id": 3}]'
                if historico == "devolucao_excessiva"
                else None,
            )
        )
    caso.db.commit()
    with pytest.raises(HTTPException) as erro:
        caso.devolver(1)
    assert erro.value.status_code == 409
    assert (caso.saldo_lote(12), caso.saldo_lote(13)) == (0, 10)
    assert caso.db.get(Produto, 11).estoque_atual == 12


@pytest.mark.parametrize("status", ["bloqueado", "vencido", "esgotado"])
def test_recomposicao_nao_libera_lote_vencido_ou_bloqueado(dados, status):
    caso = dados()
    lote = caso.db.get(ProdutoLote, 12)
    lote.status = status
    lote.data_validade = datetime.now() - timedelta(days=1)
    caso.db.commit()
    caso.devolver(1)
    assert caso.saldo_lote(12) == 1
    assert caso.db.get(ProdutoLote, 12).status == (
        "vencido" if status == "esgotado" else status
    )
