"""Regressao do pagamento parcial, reabertura e desconto sem dinheiro novo."""

from datetime import date, datetime
import os
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import Enum, create_engine, func, text
from sqlalchemy.schema import CreateSchema, CreateTable, DropSchema
from sqlalchemy.orm import Session

from app import caixa_models, produtos_models  # noqa: F401 - relacionamentos
from app.caixa.service import CaixaService
from app.financeiro import ContasReceberService
from app.financeiro_models import (
    CategoriaFinanceira,
    ContaReceber,
    FormaPagamento,
    LancamentoManual,
    Recebimento,
)
from app.models import AuditLog, Cliente
from app.vendas import finalizacao, finalizacao_pos_commit
from app.vendas_models import Venda, VendaItem, VendaPagamento


@pytest.fixture
def cenario(monkeypatch, tenant_context):
    pg_url = os.environ.get("TEST_RECEBIVEIS_POSTGRES_URL")
    schema = "test_recebiveis_" + uuid4().hex
    engine = create_engine(pg_url or "sqlite://")
    if pg_url:
        assert engine.url.host in {"127.0.0.1", "localhost"}
        with engine.begin() as conn:
            conn.execute(CreateSchema(schema))
        engine.dispose()
        engine = create_engine(
            pg_url, connect_args={"options": f"-csearch_path={schema}"}
        )
    for model in (
        Cliente,
        Venda,
        VendaItem,
        VendaPagamento,
        CategoriaFinanceira,
        FormaPagamento,
        ContaReceber,
        Recebimento,
        LancamentoManual,
        AuditLog,
    ):
        if pg_url:
            for coluna in model.__table__.columns:
                if isinstance(coluna.type, Enum):
                    coluna.type.create(engine, checkfirst=True)
            with engine.begin() as conn:
                conn.execute(
                    CreateTable(model.__table__, include_foreign_key_constraints=[])
                )
        else:
            model.__table__.create(engine)
    tenant = uuid4()
    tenant_context(tenant)
    monkeypatch.setattr(
        CaixaService, "validar_caixa_aberto", lambda **kw: {"caixa_id": 1}
    )
    monkeypatch.setattr(
        finalizacao, "get_or_build_venda_rentabilidade_snapshot", lambda *a, **kw: {}
    )
    monkeypatch.setattr(finalizacao, "publicar_eventos_finalizacao", lambda **kw: None)
    monkeypatch.setattr(
        finalizacao_pos_commit,
        "processar_contas_pagar_entrega",
        lambda **kw: {"success": False},
    )
    monkeypatch.setattr(
        finalizacao_pos_commit,
        "processar_contas_pagar_taxas",
        lambda **kw: {"success": False},
    )
    monkeypatch.setattr(
        "app.services.pendencia_estoque_service.finalizar_pendencias_por_venda",
        lambda **kw: {},
    )
    monkeypatch.setattr(
        "app.services.product_recurrence.process_finalized_sale_recurrence",
        lambda *a, **kw: {"created": [], "completed": [], "skipped": []},
    )
    with Session(engine, expire_on_commit=False) as db:
        db.add(
            FormaPagamento(
                id=1,
                tenant_id=tenant,
                nome="PIX",
                tipo="pix",
                prazo_dias=0,
                ativo=True,
                user_id=1,
            )
        )
        venda = Venda(
            id=1,
            tenant_id=tenant,
            numero_venda="TEST-REABERTURA",
            user_id=1,
            vendedor_id=1,
            subtotal=135,
            total=135,
            status="aberta",
            data_venda=datetime(2026, 9, 4),
            caixa_id=1,
            dre_gerada=True,
        )
        db.add(venda)
        db.add(
            CategoriaFinanceira(
                id=1,
                tenant_id=tenant,
                nome="Receitas de Vendas",
                tipo="receita",
                user_id=1,
            )
        )
        db.add(
            LancamentoManual(
                id=1,
                tenant_id=tenant,
                tipo="entrada",
                valor=135,
                descricao="Venda prevista",
                data_lancamento=date.today(),
                status="previsto",
                documento="VENDA-1",
                categoria_id=1,
                user_id=1,
            )
        )
        db.commit()

        def finalizar(valor=None, db_session=None):
            return finalizacao.finalizar_venda(
                venda_id=1,
                pagamentos=[]
                if valor is None
                else [
                    {"forma_pagamento": "PIX", "forma_pagamento_id": 1, "valor": valor}
                ],
                user_id=1,
                user_nome="Teste",
                tenant_id=tenant,
                db=db_session or db,
                processar_baixa_estoque_item=lambda **kw: [],
            )

        yield SimpleNamespace(db=db, venda=venda, tenant=tenant, finalizar=finalizar)
    if pg_url:
        assert schema.startswith("test_recebiveis_") and len(schema) == 48
        with engine.begin() as conn:
            conn.execute(DropSchema(schema, cascade=True))
    engine.dispose()


def test_reabertura_com_desconto_nao_repete_recebimento(cenario):
    cenario.finalizar(121)
    cenario.venda.status = "aberta"
    cenario.venda.total = Decimal("121")
    cenario.venda.desconto_valor = Decimal("14")
    cenario.db.commit()
    resultado = cenario.finalizar()
    assert cenario.db.query(VendaPagamento).count() == 1
    assert cenario.db.query(ContaReceber).count() == 1
    assert cenario.db.query(Recebimento).count() == 1
    assert cenario.db.query(func.sum(Recebimento.valor_recebido)).scalar() == Decimal(
        "121"
    )
    assert resultado["operacoes"]["contas_criadas"] == []
    assert cenario.db.query(LancamentoManual).filter_by(status="previsto").count() == 0
    assert cenario.db.query(func.sum(LancamentoManual.valor)).filter_by(
        status="realizado"
    ).scalar() == Decimal("121")


def test_duas_baixas_parciais_criam_apenas_recebimentos_novos(cenario):
    cenario.finalizar(100)
    cenario.finalizar(35)
    assert cenario.db.query(VendaPagamento).count() == 2
    assert cenario.db.query(Recebimento).count() == 2
    assert cenario.db.query(func.sum(Recebimento.valor_recebido)).scalar() == Decimal(
        "135"
    )


def test_erro_ao_criar_recebivel_desfaz_pagamento_e_permite_tentar_de_novo(
    cenario, monkeypatch
):
    original = ContasReceberService._criar_conta_simples

    def falhar_depois_da_baixa(**kwargs):
        original(**kwargs)
        raise RuntimeError("Falha controlada apos inserir recebimento")

    with monkeypatch.context() as patch:
        patch.setattr(
            ContasReceberService, "_criar_conta_simples", falhar_depois_da_baixa
        )
        with pytest.raises(HTTPException):
            cenario.finalizar(121)
    assert cenario.db.query(VendaPagamento).count() == 0
    assert cenario.db.query(ContaReceber).count() == 0
    assert cenario.db.query(Recebimento).count() == 0
    assert cenario.db.get(Venda, 1).status == "aberta"
    cenario.finalizar(121)
    assert cenario.db.query(Recebimento).count() == 1


def test_segunda_finalizacao_da_venda_quitada_e_bloqueada(cenario):
    cenario.finalizar(135)
    with pytest.raises(HTTPException) as exc:
        cenario.finalizar(135)
    assert exc.value.status_code == 400
    assert cenario.db.query(Recebimento).count() == 1


def test_baixa_em_conta_existente_nao_cria_outro_recebimento(cenario):
    cenario.db.add(
        ContaReceber(
            tenant_id=cenario.tenant,
            venda_id=1,
            descricao="Conta anterior",
            dre_subcategoria_id=1,
            canal="loja_fisica",
            valor_original=135,
            valor_final=135,
            valor_recebido=0,
            status="pendente",
            user_id=1,
            data_emissao=date.today(),
            data_vencimento=date.today(),
        )
    )
    cenario.db.commit()
    cenario.finalizar(121)
    assert cenario.db.query(ContaReceber).count() == 1
    assert cenario.db.query(Recebimento).count() == 1
    assert cenario.db.query(func.sum(Recebimento.valor_recebido)).scalar() == Decimal(
        "121"
    )


def test_parcelas_novas_preservam_regra_persistida(cenario):
    from app.vendas.finalizacao_recebiveis import criar_recebiveis_dos_novos_pagamentos

    forma = cenario.db.get(FormaPagamento, 1)
    forma.tipo = "cartao_credito"
    forma.prazo_dias = 99
    cenario.db.add(
        VendaPagamento(
            venda_id=1,
            tenant_id=cenario.tenant,
            forma_pagamento_id=1,
            forma_pagamento="Cartao",
            valor=135,
            numero_parcelas=3,
            prazo_recebimento_dias=7,
            data_recebimento_prevista=date(2026, 10, 1),
        )
    )
    cenario.db.flush()
    ids = criar_recebiveis_dos_novos_pagamentos(
        db=cenario.db,
        venda=cenario.venda,
        tenant_id=cenario.tenant,
        user_id=1,
        pagamentos_anteriores=[],
    )
    contas = cenario.db.query(ContaReceber).order_by(ContaReceber.numero_parcela).all()
    assert len(ids) == 3
    assert [c.valor_final for c in contas] == [Decimal("45")] * 3
    assert contas[0].data_vencimento == date(2026, 10, 1)
    assert all(c.status == "pendente" for c in contas)
    assert cenario.db.query(Recebimento).count() == 0


def test_finalizacao_nao_acessa_venda_de_outro_tenant(cenario, tenant_context):
    tenant_context(uuid4())
    with pytest.raises(HTTPException) as exc:
        cenario.finalizar(121)
    assert exc.value.status_code == 404
    tenant_context(cenario.tenant)
    assert cenario.db.query(VendaPagamento).count() == 0


def test_duas_finalizacoes_concorrentes_no_postgres(cenario, monkeypatch):
    if cenario.db.bind.dialect.name != "postgresql":
        pytest.skip(
            "Executar com TEST_RECEBIVEIS_POSTGRES_URL local para verificar locks reais"
        )
    from concurrent.futures import ThreadPoolExecutor
    from queue import Queue
    from threading import Event
    import time
    from app.tenancy.context import tenant_context as contexto

    entrou, liberar = Event(), Event()
    pid_segundo = Queue()
    calcular = finalizacao._calcular_pagamentos_finalizacao

    def calcular_com_pausa(**kwargs):
        entrou.set()
        assert liberar.wait(5)
        return calcular(**kwargs)

    monkeypatch.setattr(
        finalizacao, "_calcular_pagamentos_finalizacao", calcular_com_pausa
    )

    def executar(segundo=False):
        with (
            contexto(cenario.tenant),
            Session(cenario.db.bind, expire_on_commit=False) as db,
        ):
            if segundo:
                # Simula uma sessao que ja leu a venda antes do primeiro commit.
                venda_em_cache = db.get(Venda, 1)
                assert venda_em_cache.status == "aberta"
                pid_segundo.put(db.execute(text("SELECT pg_backend_pid()")).scalar())
            try:
                return cenario.finalizar(135, db_session=db)
            except HTTPException as exc:
                return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        primeira = pool.submit(executar)
        assert entrou.wait(3)
        segunda = pool.submit(executar, True)
        try:
            pid = pid_segundo.get(timeout=3)
            bloqueado = False
            with cenario.db.bind.connect() as conn:
                for _ in range(40):
                    bloqueado = conn.execute(
                        text(
                            "SELECT wait_event_type='Lock' FROM pg_stat_activity WHERE pid=:pid"
                        ),
                        {"pid": pid},
                    ).scalar()
                    if bloqueado:
                        break
                    conn.commit()
                    time.sleep(0.025)
            assert bloqueado, "A segunda finalizacao deve aguardar o lock da primeira"
        finally:
            liberar.set()
        assert primeira.result(timeout=5)["venda"]["status"] == "finalizada"
        assert segunda.result(timeout=5) == 400
    assert cenario.db.query(VendaPagamento).count() == 1
    assert cenario.db.query(Recebimento).count() == 1
