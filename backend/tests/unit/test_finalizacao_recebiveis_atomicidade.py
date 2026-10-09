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
from app.caixa_models import Caixa, MovimentacaoCaixa
from app.caixa.service import CaixaService
from app.empresa_config_geral_models import EmpresaConfigGeral
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
        Caixa,
        MovimentacaoCaixa,
        EmpresaConfigGeral,
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
        db.add(
            FormaPagamento(
                id=2,
                tenant_id=tenant,
                nome="Dinheiro",
                tipo="dinheiro",
                prazo_dias=0,
                ativo=True,
                user_id=1,
            )
        )
        db.add(
            Caixa(
                id=1,
                tenant_id=tenant,
                numero_caixa=1,
                usuario_id=1,
                usuario_nome="Teste",
                data_abertura=datetime(2026, 9, 4, 8),
                data_fechamento=datetime(2026, 9, 4, 20),
                status="fechado",
                valor_abertura=100,
                valor_informado=130,
                valor_esperado=100,
                diferenca=30,
            )
        )
        db.add(
            Caixa(
                id=2,
                tenant_id=tenant,
                numero_caixa=2,
                usuario_id=1,
                usuario_nome="Teste",
                data_abertura=datetime(2026, 9, 5, 8),
                status="aberto",
                valor_abertura=130,
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


def test_novo_pagamento_apos_reabertura_nao_liquida_repasse_antigo_da_operadora(
    cenario,
):
    """Reproduz os valores da divergência observada na Loja 1."""
    cenario.db.add(
        FormaPagamento(
            id=3,
            tenant_id=cenario.tenant,
            nome="Cartão de débito",
            tipo="cartao_debito",
            prazo_dias=1,
            ativo=True,
            user_id=1,
        )
    )
    cenario.db.add(
        VendaPagamento(
            venda_id=1,
            tenant_id=cenario.tenant,
            forma_pagamento_id=3,
            forma_pagamento="Cartão de débito",
            valor=Decimal("38.90"),
        )
    )
    conta_cartao = ContaReceber(
        tenant_id=cenario.tenant,
        venda_id=1,
        forma_pagamento_id=3,
        descricao="Repasse cartão",
        dre_subcategoria_id=1,
        canal="loja_fisica",
        valor_original=Decimal("38.90"),
        valor_final=Decimal("38.90"),
        valor_recebido=0,
        status="pendente",
        user_id=1,
        data_emissao=date.today(),
        data_vencimento=date.today(),
    )
    cenario.db.add(conta_cartao)
    cenario.venda.total = Decimal("95.80")
    cenario.venda.subtotal = Decimal("95.80")
    cenario.db.commit()
    cenario.finalizar(56.90)
    assert conta_cartao.status == "pendente"
    assert conta_cartao.valor_recebido == 0
    assert cenario.db.query(func.sum(ContaReceber.valor_final)).scalar() == Decimal(
        "95.80"
    )
    assert cenario.db.query(func.sum(Recebimento.valor_recebido)).scalar() == Decimal(
        "56.90"
    )


@pytest.mark.parametrize("tipo", ["cartao_debito", "cartao_credito"])
def test_devolucao_permite_cartao_pago_com_repasse_ainda_pendente(cenario, tipo):
    from app.vendas.devolucoes_routes import _validar_recebiveis_liquidados

    forma = cenario.db.get(FormaPagamento, 1)
    forma.tipo = tipo
    forma.prazo_dias = 1
    cenario.db.add(
        VendaPagamento(
            venda_id=1,
            tenant_id=cenario.tenant,
            forma_pagamento_id=1,
            forma_pagamento="Cartão",
            valor=135,
        )
    )
    cenario.db.add(
        ContaReceber(
            tenant_id=cenario.tenant,
            venda_id=1,
            forma_pagamento_id=1,
            descricao="Repasse cartão",
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
    cenario.db.flush()
    _validar_recebiveis_liquidados(cenario.db, 1, cenario.tenant)
    assert cenario.db.query(ContaReceber).one().valor_recebido == 0

    forma.tipo = "crediario"
    cenario.db.flush()
    with pytest.raises(HTTPException) as erro:
        _validar_recebiveis_liquidados(cenario.db, 1, cenario.tenant)
    assert erro.value.status_code == 409

    forma.tipo = tipo
    cenario.db.query(VendaPagamento).one().status = "estornado"
    cenario.db.flush()
    with pytest.raises(HTTPException) as erro:
        _validar_recebiveis_liquidados(cenario.db, 1, cenario.tenant)
    assert erro.value.status_code == 409


def _conta_repasse_pendente(cenario, *, forma_id=1, valor="135"):
    conta = ContaReceber(
        tenant_id=cenario.tenant,
        venda_id=cenario.venda.id,
        forma_pagamento_id=forma_id,
        descricao="Repasse de cartao ainda pendente",
        dre_subcategoria_id=1,
        canal="loja_fisica",
        valor_original=Decimal(valor),
        valor_final=Decimal(valor),
        valor_recebido=Decimal("0"),
        status="pendente",
        user_id=1,
        data_emissao=date.today(),
        data_vencimento=date.today(),
    )
    cenario.db.add(conta)
    return conta


def _assert_devolucao_exige_conciliacao(cenario):
    from app.vendas.devolucoes_routes import _validar_recebiveis_liquidados

    with pytest.raises(HTTPException) as erro:
        _validar_recebiveis_liquidados(cenario.db, cenario.venda.id, cenario.tenant)
    assert erro.value.status_code == 409
    assert "recebivel em aberto" in erro.value.detail


@pytest.mark.parametrize("tipo", ["cartao_debito", "cartao_credito"])
@pytest.mark.parametrize("pago", ["0", "134.99"])
def test_devolucao_bloqueia_repasse_sem_pagamento_integral_no_cartao(
    cenario, tipo, pago
):
    cenario.db.get(FormaPagamento, 1).tipo = tipo
    conta = _conta_repasse_pendente(cenario)
    cenario.db.add(
        VendaPagamento(
            tenant_id=cenario.tenant,
            venda_id=cenario.venda.id,
            forma_pagamento_id=1,
            forma_pagamento="Cartao",
            valor=Decimal(pago),
            status="confirmado",
        )
    )
    cenario.db.flush()

    _assert_devolucao_exige_conciliacao(cenario)

    assert conta.status == "pendente"
    assert conta.valor_recebido == 0


@pytest.mark.parametrize(
    "status_crediario,recebido", [("pendente", "0"), ("parcial", "10")]
)
def test_devolucao_bloqueia_venda_mista_com_crediario_ainda_aberto(
    cenario, status_crediario, recebido
):
    cenario.db.get(FormaPagamento, 1).tipo = "cartao_credito"
    cenario.db.get(FormaPagamento, 2).tipo = "crediario"
    _conta_repasse_pendente(cenario, valor="100")
    conta_crediario = _conta_repasse_pendente(cenario, forma_id=2, valor="35")
    conta_crediario.status = status_crediario
    conta_crediario.valor_recebido = Decimal(recebido)
    cenario.db.add_all(
        [
            VendaPagamento(
                tenant_id=cenario.tenant,
                venda_id=cenario.venda.id,
                forma_pagamento_id=1,
                forma_pagamento="Cartao",
                valor=Decimal("100"),
                status="confirmado",
            ),
            VendaPagamento(
                tenant_id=cenario.tenant,
                venda_id=cenario.venda.id,
                forma_pagamento_id=2,
                forma_pagamento="Crediario",
                valor=Decimal("35"),
                status="confirmado",
            ),
        ]
    )
    cenario.db.flush()

    _assert_devolucao_exige_conciliacao(cenario)

    assert conta_crediario.valor_recebido == Decimal(recebido)
    assert conta_crediario.status == status_crediario


def test_devolucao_nao_usa_pagamento_cartao_de_outra_venda(cenario):
    cenario.db.get(FormaPagamento, 1).tipo = "cartao_credito"
    _conta_repasse_pendente(cenario)
    outra_venda = Venda(
        tenant_id=cenario.tenant,
        numero_venda="OUTRA-VENDA",
        user_id=1,
        vendedor_id=1,
        subtotal=135,
        total=135,
        status="finalizada",
    )
    cenario.db.add(outra_venda)
    cenario.db.flush()
    cenario.db.add(
        VendaPagamento(
            tenant_id=cenario.tenant,
            venda_id=outra_venda.id,
            forma_pagamento_id=1,
            forma_pagamento="Cartao",
            valor=135,
            status="confirmado",
        )
    )
    cenario.db.flush()

    _assert_devolucao_exige_conciliacao(cenario)


def test_devolucao_nao_usa_pagamento_cartao_de_outro_tenant(cenario, tenant_context):
    cenario.db.get(FormaPagamento, 1).tipo = "cartao_credito"
    _conta_repasse_pendente(cenario)
    cenario.db.flush()
    outro_tenant = uuid4()
    tenant_context(outro_tenant)
    # Simula um vinculo legado inconsistente; o filtro explicito deve rejeita-lo.
    cenario.db.add(
        VendaPagamento(
            tenant_id=outro_tenant,
            venda_id=cenario.venda.id,
            forma_pagamento_id=1,
            forma_pagamento="Cartao",
            valor=135,
            status="confirmado",
        )
    )
    cenario.db.flush()
    tenant_context(cenario.tenant)

    _assert_devolucao_exige_conciliacao(cenario)

    assert cenario.db.query(VendaPagamento).count() == 0


def test_devolucao_nao_aceita_forma_cartao_cadastrada_em_outro_tenant(
    cenario, tenant_context
):
    outro_tenant = uuid4()
    tenant_context(outro_tenant)
    forma_alheia = FormaPagamento(
        tenant_id=outro_tenant,
        nome="Cartao de outra empresa",
        tipo="cartao_credito",
        prazo_dias=1,
        ativo=True,
        user_id=1,
    )
    cenario.db.add(forma_alheia)
    cenario.db.flush()
    forma_id = forma_alheia.id
    tenant_context(cenario.tenant)
    _conta_repasse_pendente(cenario, forma_id=forma_id)
    cenario.db.add(
        VendaPagamento(
            tenant_id=cenario.tenant,
            venda_id=cenario.venda.id,
            forma_pagamento_id=forma_id,
            forma_pagamento="Cartao",
            valor=135,
            status="confirmado",
        )
    )
    cenario.db.flush()

    _assert_devolucao_exige_conciliacao(cenario)


def test_pagamento_retroativo_corrige_caixa_fechado_sem_mudar_caixa_atual(cenario):
    momento = datetime(2026, 9, 4, 15, 30)
    cenario.venda.total = Decimal("30")
    cenario.venda.subtotal = Decimal("30")
    cenario.db.query(LancamentoManual).filter_by(id=1).one().valor = Decimal("30")
    cenario.db.commit()

    finalizacao.finalizar_venda(
        venda_id=1,
        pagamentos=[
            {"forma_pagamento": "Dinheiro", "forma_pagamento_id": 2, "valor": 30}
        ],
        user_id=1,
        user_nome="Teste",
        tenant_id=cenario.tenant,
        db=cenario.db,
        caixa_id=1,
        data_ocorrencia=momento,
        motivo_revisao="Recebido e esquecido",
        processar_baixa_estoque_item=lambda **kw: [],
    )

    pagamento = cenario.db.query(VendaPagamento).one()
    movimento = cenario.db.query(MovimentacaoCaixa).one()
    recebimento = cenario.db.query(Recebimento).one()
    caixa_anterior = cenario.db.get(Caixa, 1)
    caixa_atual = cenario.db.get(Caixa, 2)
    assert pagamento.data_pagamento == momento
    assert movimento.caixa_id == 1
    assert movimento.data_movimento == momento
    assert recebimento.data_recebimento == momento.date()
    assert caixa_anterior.status == "fechado"
    assert caixa_anterior.valor_esperado == 130
    assert caixa_anterior.diferenca == 0
    assert caixa_atual.status == "aberto"
    assert caixa_atual.valor_abertura == 130


def test_pagamento_normal_em_dinheiro_mantem_data_automatica(cenario):
    finalizacao.finalizar_venda(
        venda_id=1,
        pagamentos=[
            {"forma_pagamento": "Dinheiro", "forma_pagamento_id": 2, "valor": 135}
        ],
        user_id=1,
        user_nome="Teste",
        tenant_id=cenario.tenant,
        db=cenario.db,
        processar_baixa_estoque_item=lambda **kw: [],
    )
    movimento = cenario.db.query(MovimentacaoCaixa).one()
    assert movimento.data_movimento is not None


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
