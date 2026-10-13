import json
import os
from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import Enum, create_engine
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, CreateTable, DropSchema

from app.caixa.auditoria_routes import (
    ConferenciaItemSchema,
    conferir_item_caixa,
    obter_auditoria_caixa,
)
from app.caixa_routes import (
    ReabrirCaixaSchema,
    listar_vendas_caixa,
    obter_resumo_caixa,
    reabrir_caixa,
)
from app.caixa_models import Caixa, MovimentacaoCaixa
from app.db import Base
from app.empresa_config_geral_models import EmpresaConfigGeral
from app.financeiro_models import ContaReceber
from app.models import AuditLog
from app import produtos_models  # noqa: F401 - resolve relacionamentos da venda
from app.vendas_models import Venda, VendaItem, VendaPagamento


@pytest.fixture
def caixa_session():
    pg_url = os.environ.get("TEST_RECEBIVEIS_POSTGRES_URL")
    schema = "test_caixa_" + uuid4().hex
    engine = create_engine(pg_url or "sqlite://")
    tables = [
        Caixa.__table__,
        MovimentacaoCaixa.__table__,
        Venda.__table__,
        VendaPagamento.__table__,
        VendaItem.__table__,
        AuditLog.__table__,
        EmpresaConfigGeral.__table__,
        ContaReceber.__table__,
    ]
    if pg_url:
        assert engine.url.host in {"127.0.0.1", "localhost"}
        with engine.begin() as conn:
            conn.execute(CreateSchema(schema))
        engine.dispose()
        engine = create_engine(
            pg_url, connect_args={"options": f"-csearch_path={schema}"}
        )
        for table in tables:
            for coluna in table.columns:
                if isinstance(coluna.type, Enum):
                    coluna.type.create(engine, checkfirst=True)
            with engine.begin() as conn:
                conn.execute(CreateTable(table, include_foreign_key_constraints=[]))
    else:
        Base.metadata.create_all(engine, tables=tables)
    try:
        with Session(engine, expire_on_commit=False) as db:
            yield db
    finally:
        if pg_url:
            assert schema.startswith("test_caixa_") and len(schema) == 43
            with engine.begin() as conn:
                conn.execute(DropSchema(schema, cascade=True))
        engine.dispose()


@pytest.fixture
def recebimentos(caixa_session, tenant_context):
    db_session = caixa_session
    tenant_id = uuid4()
    tenant_context(tenant_id)
    usuario = SimpleNamespace(id=91, nome="Operador", email="operador@example.test")
    original = Caixa(
        tenant_id=tenant_id,
        numero_caixa=1,
        usuario_id=usuario.id,
        usuario_nome=usuario.nome,
        status="fechado",
        valor_abertura=100,
        data_abertura=datetime(2026, 10, 8, 8),
        data_fechamento=datetime(2026, 10, 8, 20),
        valor_informado=100,
        valor_esperado=100,
    )
    atual = Caixa(
        tenant_id=tenant_id,
        numero_caixa=2,
        usuario_id=usuario.id,
        usuario_nome=usuario.nome,
        status="aberto",
        valor_abertura=100,
        data_abertura=datetime(2026, 10, 9, 8),
    )
    db_session.add_all([original, atual])
    db_session.flush()
    venda = Venda(
        tenant_id=tenant_id,
        numero_venda="V-ANTIGA",
        vendedor_id=usuario.id,
        user_id=usuario.id,
        caixa_id=original.id,
        subtotal=90,
        total=90,
        status="finalizada",
        data_venda=datetime(2026, 10, 8, 10),
        canal="loja_fisica",
    )
    db_session.add(venda)
    db_session.flush()
    pagamentos = [
        VendaPagamento(
            tenant_id=tenant_id,
            venda_id=venda.id,
            caixa_id=original.id,
            forma_pagamento="PIX",
            valor=30,
            data_pagamento=datetime(2026, 10, 8, 10),
        ),
        VendaPagamento(
            tenant_id=tenant_id,
            venda_id=venda.id,
            caixa_id=atual.id,
            forma_pagamento="PIX",
            valor=40,
            data_pagamento=datetime(2026, 10, 9, 12),
        ),
        VendaPagamento(
            tenant_id=tenant_id,
            venda_id=venda.id,
            caixa_id=atual.id,
            forma_pagamento="Dinheiro",
            valor=20,
            data_pagamento=datetime(2026, 10, 9, 12),
        ),
    ]
    movimento = MovimentacaoCaixa(
        tenant_id=tenant_id,
        caixa_id=atual.id,
        tipo="venda",
        valor=20,
        forma_pagamento="Dinheiro",
        venda_id=venda.id,
        usuario_id=usuario.id,
        usuario_nome=usuario.nome,
        data_movimento=datetime(2026, 10, 9, 12),
    )
    db_session.add_all([*pagamentos, movimento])
    db_session.flush()
    return SimpleNamespace(
        db=db_session,
        auth=(usuario, tenant_id),
        venda=venda,
        original=original,
        atual=atual,
        pagamentos=pagamentos,
        movimento=movimento,
    )


def test_venda_antiga_recebida_hoje_aparece_so_no_caixa_recebedor(recebimentos):
    caso = recebimentos
    atual = obter_resumo_caixa(
        caso.atual.id, db=caso.db, current_user_and_tenant=caso.auth
    )
    original = obter_resumo_caixa(
        caso.original.id, db=caso.db, current_user_and_tenant=caso.auth
    )

    assert atual["total_recebido"] == 60
    assert atual["total_vendido"] == 0
    assert atual["totais"]["saldo_atual"] == 120
    assert atual["recebimentos_por_forma_pagamento"]["PIX"]["total"] == 40
    assert original["total_recebido"] == 30
    assert original["total_vendido"] == 90
    assert caso.venda.caixa_id == caso.original.id

    detalhes = listar_vendas_caixa(
        caso.atual.id,
        forma_pagamento="PIX",
        db=caso.db,
        current_user_and_tenant=caso.auth,
    )
    assert len(detalhes) == 1
    assert detalhes[0]["venda_id"] == caso.venda.id
    assert detalhes[0]["data_venda"] == "2026-10-08"
    assert detalhes[0]["data_recebimento"].startswith("2026-10-09")


def test_pagamentos_zerados_historicos_nao_contam_no_fechamento(recebimentos):
    caso = recebimentos
    for _ in range(2):
        caso.db.add(
            VendaPagamento(
                tenant_id=caso.auth[1],
                venda_id=caso.venda.id,
                caixa_id=caso.atual.id,
                forma_pagamento="PIX",
                valor=0,
                data_pagamento=datetime(2026, 10, 9, 13),
            )
        )
    caso.db.flush()

    resumo = obter_resumo_caixa(
        caso.atual.id, db=caso.db, current_user_and_tenant=caso.auth
    )
    detalhes = listar_vendas_caixa(
        caso.atual.id,
        forma_pagamento="PIX",
        db=caso.db,
        current_user_and_tenant=caso.auth,
    )

    assert resumo["recebimentos_por_forma_pagamento"]["PIX"]["quantidade"] == 1
    assert resumo["recebimentos_por_forma_pagamento"]["PIX"]["total"] == 40
    assert [item["valor_nesta_forma"] for item in detalhes] == [40]
    assert caso.db.query(VendaPagamento).filter_by(venda_id=caso.venda.id).count() == 5


@pytest.mark.parametrize("status", ["aberta", "cancelada"])
def test_recebimentos_continuam_auditaveis_quando_status_venda_muda(
    recebimentos, status
):
    caso = recebimentos
    caso.venda.status = status
    caso.db.flush()
    resumo = obter_resumo_caixa(
        caso.atual.id, db=caso.db, current_user_and_tenant=caso.auth
    )
    assert resumo["total_recebido"] == 60
    auditoria = obter_auditoria_caixa(
        caso.atual.id, db=caso.db, current_user_and_tenant=caso.auth
    )
    assert auditoria["vendas"][0]["valor_nesta_forma"] == 60
    assert len(auditoria["movimentacoes"]) == 1
    assert len(auditoria["pagamentos"]) == 1


def test_pagamento_estornado_nao_compoe_resumo(recebimentos):
    caso = recebimentos
    caso.pagamentos[1].status = "estornado"
    caso.db.flush()
    resumo = obter_resumo_caixa(
        caso.atual.id, db=caso.db, current_user_and_tenant=caso.auth
    )
    assert resumo["total_recebido"] == 20
    assert "PIX" not in resumo["recebimentos_por_forma_pagamento"]


def test_auditoria_reune_espelho_pix_legado_mas_preserva_extrato(recebimentos):
    caso = recebimentos
    espelho = MovimentacaoCaixa(
        tenant_id=caso.auth[1],
        caixa_id=caso.atual.id,
        tipo="venda",
        categoria="venda",
        descricao=f"Baixa venda #{caso.venda.id} - Cliente avulso",
        forma_pagamento="PIX",
        valor=40,
        venda_id=caso.venda.id,
        usuario_id=caso.auth[0].id,
        usuario_nome=caso.auth[0].nome,
        data_movimento=datetime(2026, 10, 9, 12, 0, 0, 500000),
    )
    caso.db.add(espelho)
    caso.db.flush()
    auditoria = obter_auditoria_caixa(
        caso.atual.id, db=caso.db, current_user_and_tenant=caso.auth
    )
    assert len(auditoria["movimentacoes"]) == 1
    assert len(auditoria["pagamentos"]) == 1
    assert auditoria["espelhos_pagamentos"][0]["id"] == espelho.id
    assert auditoria["espelhos_pagamentos"][0]["pagamento_id"] == caso.pagamentos[1].id
    assert auditoria["resumo"]["total_recebido"] == 60
    assert (
        caso.db.query(MovimentacaoCaixa).filter_by(caixa_id=caso.atual.id).count() == 2
    )


def test_movimento_eletronico_sem_espelho_comprovado_continua_na_auditoria(
    recebimentos,
):
    caso = recebimentos
    caso.db.add(
        MovimentacaoCaixa(
            tenant_id=caso.auth[1],
            caixa_id=caso.atual.id,
            tipo="venda",
            categoria="venda",
            descricao=f"Baixa venda #{caso.venda.id} - Cliente avulso",
            forma_pagamento="PIX",
            valor=41,
            venda_id=caso.venda.id,
            usuario_id=caso.auth[0].id,
            usuario_nome=caso.auth[0].nome,
            data_movimento=datetime(2026, 10, 9, 12),
        )
    )
    caso.db.flush()
    auditoria = obter_auditoria_caixa(
        caso.atual.id, db=caso.db, current_user_and_tenant=caso.auth
    )
    assert len(auditoria["movimentacoes"]) == 2
    assert auditoria["espelhos_pagamentos"] == []


def test_conferencia_persiste_e_mudanca_exige_nova_conferencia(recebimentos):
    caso = recebimentos
    auditoria = obter_auditoria_caixa(
        caso.atual.id, db=caso.db, current_user_and_tenant=caso.auth
    )
    pagamento = auditoria["pagamentos"][0]
    conferir_item_caixa(
        caso.atual.id,
        ConferenciaItemSchema(
            tipo_item="pagamento",
            item_id=pagamento["id"],
            conferido=True,
            assinatura=pagamento["assinatura"],
        ),
        db=caso.db,
        current_user_and_tenant=caso.auth,
    )
    revisado = obter_auditoria_caixa(
        caso.atual.id, db=caso.db, current_user_and_tenant=caso.auth
    )
    assert revisado["pagamentos"][0]["conferido"]
    caso.pagamentos[1].valor = 35
    caso.db.flush()
    atualizado = obter_auditoria_caixa(
        caso.atual.id, db=caso.db, current_user_and_tenant=caso.auth
    )
    assert not atualizado["pagamentos"][0]["conferido"]
    with pytest.raises(HTTPException) as erro:
        conferir_item_caixa(
            caso.atual.id,
            ConferenciaItemSchema(
                tipo_item="pagamento",
                item_id=pagamento["id"],
                conferido=True,
                assinatura=pagamento["assinatura"],
            ),
            db=caso.db,
            current_user_and_tenant=caso.auth,
        )
    assert erro.value.status_code == 409


def test_reabertura_preserva_fechamento_completo_e_justificativa(recebimentos):
    caso = recebimentos
    caso.atual.status = "fechado"
    caso.atual.data_fechamento = datetime(2026, 10, 9, 20)
    caso.atual.valor_esperado = 120
    caso.atual.valor_informado = 119
    caso.atual.diferenca = -1
    caso.atual.usuario_fechamento_id = caso.auth[0].id
    caso.db.flush()
    resultado = reabrir_caixa(
        caso.atual.id,
        ReabrirCaixaSchema(motivo="Recontagem dos valores de caixa"),
        db=caso.db,
        current_user_and_tenant=caso.auth,
    )
    assert resultado["status"] == "aberto"
    assert resultado["data_fechamento"] is None
    evento = (
        caso.db.query(AuditLog)
        .filter_by(action="caixa_reaberto", entity_id=caso.atual.id)
        .one()
    )
    anterior = json.loads(evento.old_value)
    assert anterior["resumo"]["caixa"]["valor_informado"] == 119
    assert anterior["resumo"]["caixa"]["diferenca"] == -1
    assert anterior["resumo"]["total_recebido"] == 60
    assert anterior["vendas"][0]["venda_id"] == caso.venda.id
    assert evento.details == "Recontagem dos valores de caixa"


def test_reabertura_nao_cria_segundo_caixa_ativo(recebimentos):
    caso = recebimentos
    with pytest.raises(HTTPException) as erro:
        reabrir_caixa(
            caso.original.id,
            ReabrirCaixaSchema(motivo="Recontagem dos valores de caixa"),
            db=caso.db,
            current_user_and_tenant=caso.auth,
        )
    assert erro.value.status_code == 400
    assert caso.original.status == "fechado"


def test_caixa_antigo_reaberto_nao_absorve_recebimento_legado_ambiguo(recebimentos):
    caso = recebimentos
    caso.atual.status = "fechado"
    caso.atual.data_fechamento = datetime(2026, 10, 9, 20)
    caso.atual.valor_informado = 120
    caso.db.add_all(
        [
            Caixa(
                tenant_id=caso.auth[1],
                numero_caixa=3,
                usuario_id=92,
                usuario_nome="Outro operador",
                status="fechado",
                valor_abertura=0,
                data_abertura=datetime(2026, 10, 9, 8),
                data_fechamento=datetime(2026, 10, 9, 20),
                valor_informado=0,
            ),
            VendaPagamento(
                tenant_id=caso.auth[1],
                venda_id=caso.venda.id,
                caixa_id=None,
                forma_pagamento="PIX",
                valor=12,
                data_pagamento=datetime(2026, 10, 9, 15),
            ),
        ]
    )
    caso.db.flush()
    reabrir_caixa(
        caso.original.id,
        ReabrirCaixaSchema(motivo="Conferência do caixa anterior"),
        db=caso.db,
        current_user_and_tenant=caso.auth,
    )
    resumo = obter_resumo_caixa(
        caso.original.id, db=caso.db, current_user_and_tenant=caso.auth
    )
    assert resumo["total_recebido"] == 30
    detalhes = listar_vendas_caixa(
        caso.original.id,
        forma_pagamento="PIX",
        db=caso.db,
        current_user_and_tenant=caso.auth,
    )
    assert [item["valor_nesta_forma"] for item in detalhes] == [30]


def test_auditoria_nao_expoe_caixa_de_outro_usuario_ou_empresa(recebimentos):
    caso = recebimentos
    for auth in [
        (
            SimpleNamespace(id=92, nome="Outro", email="outro@example.test"),
            caso.auth[1],
        ),
        (caso.auth[0], uuid4()),
    ]:
        with pytest.raises(HTTPException) as erro:
            obter_auditoria_caixa(
                caso.atual.id, db=caso.db, current_user_and_tenant=auth
            )
        assert erro.value.status_code == 404


def test_auditoria_legada_exibe_29_pagamentos_sem_inferir_caixa(
    caixa_session, tenant_context
):
    db = caixa_session
    tenant_id = uuid4()
    tenant_context(tenant_id)
    usuario = SimpleNamespace(id=91, nome="Operador", email="operador@example.test")
    alvo = Caixa(
        tenant_id=tenant_id,
        numero_caixa=227,
        usuario_id=usuario.id,
        usuario_nome=usuario.nome,
        status="fechado",
        valor_abertura=100,
        data_abertura=datetime(2026, 10, 8, 9, 14),
        data_fechamento=datetime(2026, 10, 8, 18, 32),
    )
    sobreposto = Caixa(
        tenant_id=tenant_id,
        numero_caixa=11,
        usuario_id=92,
        usuario_nome="Outro operador",
        status="aberto",
        valor_abertura=0,
        data_abertura=datetime(2026, 3, 10, 8),
    )
    db.add_all([alvo, sobreposto])
    db.flush()
    formas = {
        "Dinheiro": [64.44] * 6 + [64.46],
        "Cartão de crédito": [113.79] * 7 + [113.82],
        "Cartão de débito": [140.52] * 5,
        "PIX": [131.68] * 8 + [131.73],
    }
    for forma, valores in formas.items():
        for valor in valores:
            venda = Venda(
                tenant_id=tenant_id,
                numero_venda=f"LG-{uuid4().hex[:12]}",
                vendedor_id=usuario.id,
                user_id=usuario.id,
                caixa_id=alvo.id,
                subtotal=valor,
                total=valor,
                status="finalizada",
                data_venda=datetime(2026, 10, 8, 10),
                canal="loja_fisica",
            )
            db.add(venda)
            db.flush()
            db.add(
                VendaPagamento(
                    tenant_id=tenant_id,
                    venda_id=venda.id,
                    caixa_id=None,
                    forma_pagamento=forma,
                    valor=valor,
                    status="pendente",
                    data_pagamento=datetime(2026, 10, 8, 10),
                )
            )
            if forma == "Dinheiro":
                db.add(
                    MovimentacaoCaixa(
                        tenant_id=tenant_id,
                        caixa_id=alvo.id,
                        venda_id=venda.id,
                        tipo="venda",
                        forma_pagamento=forma,
                        valor=valor,
                        usuario_id=usuario.id,
                        usuario_nome=usuario.nome,
                        data_movimento=datetime(2026, 10, 8, 10),
                    )
                )
    db.flush()
    auditoria = obter_auditoria_caixa(
        alvo.id, db=db, current_user_and_tenant=(usuario, tenant_id)
    )
    resumo = auditoria["resumo"]
    assert len(auditoria["vendas"]) == 29
    assert all(len(venda["pagamentos"]) == 1 for venda in auditoria["vendas"])
    assert all(
        venda["pagamentos"][0]["caixa_id"] is None
        and venda["pagamentos"][0]["status"] == "pendente"
        for venda in auditoria["vendas"]
    )
    assert resumo["total_vendido"] == 3249.22
    assert resumo["total_recebido"] == 451.10
    assert resumo["totais"]["saldo_atual"] == 551.10
    assert auditoria["pagamentos"] == []
    assert len(auditoria["movimentacoes"]) == 7
    esperados = {
        "Dinheiro": (7, 451.10),
        "Cartão de crédito": (8, 910.35),
        "Cartão de débito": (5, 702.60),
        "PIX": (9, 1185.17),
    }
    for forma, (quantidade, total) in esperados.items():
        assert resumo["pagamentos_vendas_por_forma_pagamento"][forma] == {
            "quantidade": quantidade,
            "total": total,
            "tipo_contagem": "pagamento",
        }
    assert resumo["pagamentos_vendas_sem_caixa"] == {
        "quantidade": 29,
        "total": 3249.22,
        "por_forma_pagamento": resumo["pagamentos_vendas_por_forma_pagamento"],
    }
    assert (
        db.query(VendaPagamento).filter(VendaPagamento.caixa_id.is_(None)).count() == 29
    )


def test_composicao_mista_nao_confunde_recebimento_em_outro_dia(recebimentos):
    caso = recebimentos
    original = obter_auditoria_caixa(
        caso.original.id, db=caso.db, current_user_and_tenant=caso.auth
    )
    atual = obter_auditoria_caixa(
        caso.atual.id, db=caso.db, current_user_and_tenant=caso.auth
    )
    assert [item["id"] for item in original["vendas"][0]["pagamentos"]] == [
        pagamento.id for pagamento in caso.pagamentos
    ]
    assert original["vendas"][0]["pagamentos"] == atual["vendas"][0]["pagamentos"]
    assert (
        original["resumo"]["pagamentos_vendas_por_forma_pagamento"]["PIX"]["total"]
        == 70
    )
    assert (
        original["resumo"]["pagamentos_vendas_por_forma_pagamento"]["Dinheiro"]["total"]
        == 20
    )
    assert original["resumo"]["total_recebido"] == 30
    assert atual["resumo"]["pagamentos_vendas_por_forma_pagamento"] == {}
    assert atual["resumo"]["pagamentos_vendas_sem_caixa"]["total"] == 0
    assert atual["resumo"]["total_recebido"] == 60
    assert original["vendas"][0]["valor_nesta_forma"] == 30
    assert atual["vendas"][0]["valor_nesta_forma"] == 60


@pytest.mark.parametrize(
    "status", [" Estornado ", "RECUSADO", " Cancelado ", "CANCELADA"]
)
def test_status_excluido_normalizado_continua_no_historico_sem_somar(
    recebimentos, status
):
    caso = recebimentos
    caso.pagamentos[1].status = status
    caso.db.flush()
    original = obter_auditoria_caixa(
        caso.original.id, db=caso.db, current_user_and_tenant=caso.auth
    )
    atual = obter_auditoria_caixa(
        caso.atual.id, db=caso.db, current_user_and_tenant=caso.auth
    )
    assert len(original["vendas"][0]["pagamentos"]) == 3
    assert original["vendas"][0]["pagamentos"][1]["status"] == status
    assert (
        original["resumo"]["pagamentos_vendas_por_forma_pagamento"]["PIX"]["total"]
        == 30
    )
    assert atual["resumo"]["total_recebido"] == 20
    assert atual["pagamentos"] == []


def test_pagamentos_com_tenant_incorreto_nao_entram_na_venda_ou_resumo(recebimentos):
    caso = recebimentos
    # Simula uma associação legada inconsistente; o guard ORM já recusa novos
    # registros assim, mas a leitura precisa proteger também bancos existentes.
    caso.db.execute(
        VendaPagamento.__table__.insert().values(
            tenant_id=uuid4(),
            venda_id=caso.venda.id,
            caixa_id=caso.original.id,
            forma_pagamento="PIX",
            valor=999,
            data_pagamento=datetime(2026, 10, 8, 10),
        )
    )
    auditoria = obter_auditoria_caixa(
        caso.original.id, db=caso.db, current_user_and_tenant=caso.auth
    )
    assert len(auditoria["vendas"][0]["pagamentos"]) == 3
    assert (
        auditoria["resumo"]["pagamentos_vendas_por_forma_pagamento"]["PIX"]["total"]
        == 70
    )
    assert auditoria["resumo"]["total_recebido"] == 30


def test_pagamento_em_outro_caixa_invalida_conferencia_da_venda(recebimentos):
    caso = recebimentos
    auditoria = obter_auditoria_caixa(
        caso.original.id, db=caso.db, current_user_and_tenant=caso.auth
    )
    venda = auditoria["vendas"][0]
    dados = ConferenciaItemSchema(
        tipo_item="venda",
        item_id=venda["id"],
        conferido=True,
        assinatura=venda["assinatura"],
    )
    conferir_item_caixa(
        caso.original.id, dados, db=caso.db, current_user_and_tenant=caso.auth
    )
    revisada = obter_auditoria_caixa(
        caso.original.id, db=caso.db, current_user_and_tenant=caso.auth
    )
    assert revisada["vendas"][0]["conferido"]
    caso.pagamentos[1].valor = 35
    caso.db.flush()
    atualizada = obter_auditoria_caixa(
        caso.original.id, db=caso.db, current_user_and_tenant=caso.auth
    )
    assert atualizada["resumo"]["total_recebido"] == 30
    assert not atualizada["vendas"][0]["conferido"]
    with pytest.raises(HTTPException) as erro:
        conferir_item_caixa(
            caso.original.id, dados, db=caso.db, current_user_and_tenant=caso.auth
        )
    assert erro.value.status_code == 409


def test_composicao_inclui_planos_a_prazo_sem_contar_como_recebimento(recebimentos):
    caso = recebimentos
    venda = Venda(
        tenant_id=caso.auth[1],
        numero_venda="MISTA-A-PRAZO",
        vendedor_id=caso.auth[0].id,
        user_id=caso.auth[0].id,
        caixa_id=caso.atual.id,
        subtotal=120,
        total=120,
        status="baixa_parcial",
        data_venda=datetime(2026, 10, 9, 12),
        canal="loja_fisica",
    )
    caso.db.add(venda)
    caso.db.flush()
    for forma, valor, caixa_id in [
        ("Crediário", 70, caso.atual.id),
        ("Boleto", 20, None),
        ("PIX", 30, caso.atual.id),
    ]:
        caso.db.add(
            VendaPagamento(
                tenant_id=caso.auth[1],
                venda_id=venda.id,
                caixa_id=caixa_id,
                forma_pagamento=forma,
                valor=valor,
                status="pendente",
                data_pagamento=datetime(2026, 10, 9, 12),
            )
        )
    caso.db.flush()
    auditoria = obter_auditoria_caixa(
        caso.atual.id, db=caso.db, current_user_and_tenant=caso.auth
    )
    resumo = auditoria["resumo"]
    item = next(item for item in auditoria["vendas"] if item["id"] == venda.id)
    assert len(item["pagamentos"]) == 3
    assert item["valor_nesta_forma"] == 30
    assert [recebimento["forma_pagamento"] for recebimento in item["recebimentos"]] == [
        "PIX"
    ]
    assert all(
        pagamento["forma_pagamento"] == "PIX" for pagamento in auditoria["pagamentos"]
    )
    assert set(resumo["pagamentos_vendas_por_forma_pagamento"]) == {
        "Crediário",
        "Boleto",
        "PIX",
    }
    assert resumo["total_vendido"] == 120
    assert resumo["total_recebido"] == 90
    assert set(resumo["recebimentos_por_forma_pagamento"]) == {"Dinheiro", "PIX"}
    assert resumo["pagamentos_vendas_sem_caixa"]["total"] == 20
    plano = next(
        pagamento
        for pagamento in item["pagamentos"]
        if pagamento["forma_pagamento"] == "Crediário"
    )
    with pytest.raises(HTTPException) as erro:
        conferir_item_caixa(
            caso.atual.id,
            ConferenciaItemSchema(
                tipo_item="pagamento",
                item_id=plano["id"],
                conferido=True,
                assinatura="0" * 64,
            ),
            db=caso.db,
            current_user_and_tenant=caso.auth,
        )
    assert erro.value.status_code == 404


@pytest.mark.parametrize("primeiro", ["recebimento", "fechamento"])
def test_fechamento_e_recebimento_serializam_mesmo_caixa_no_postgres(
    recebimentos, monkeypatch, primeiro
):
    caso = recebimentos
    if caso.db.bind.dialect.name != "postgresql":
        pytest.skip(
            "Executar com TEST_RECEBIVEIS_POSTGRES_URL local para verificar locks reais"
        )
    import asyncio
    import time
    from concurrent.futures import ThreadPoolExecutor
    from queue import Queue
    from threading import Event
    from sqlalchemy import text
    from app import caixa_routes
    from app.caixa.service import CaixaService
    from app.tenancy.context import tenant_context as contexto

    entrou, liberar = Event(), Event()
    pid_segundo = Queue()
    caso.db.commit()
    registrar = caixa_routes.registrar_evento_caixa

    def registrar_com_pausa(db, **kwargs):
        if primeiro == "fechamento":
            entrou.set()
            assert liberar.wait(5)
        return registrar(db, **kwargs)

    monkeypatch.setattr(caixa_routes, "registrar_evento_caixa", registrar_com_pausa)

    def receber(segundo=False):
        with (
            contexto(caso.auth[1]),
            Session(caso.db.bind, expire_on_commit=False) as db,
        ):
            if segundo:
                caixa_em_cache = db.get(Caixa, caso.atual.id)
                assert caixa_em_cache.status == "aberto"
                pid_segundo.put(db.execute(text("SELECT pg_backend_pid()")).scalar())
            try:
                CaixaService.validar_caixa_aberto(
                    user_id=caso.auth[0].id,
                    tenant_id=caso.auth[1],
                    caixa_id=caso.atual.id,
                    db=db,
                )
                if primeiro == "recebimento":
                    entrou.set()
                    assert liberar.wait(5)
                CaixaService.registrar_movimentacao_venda(
                    caixa_id=caso.atual.id,
                    venda_id=caso.venda.id,
                    venda_numero=caso.venda.numero_venda,
                    valor=7,
                    user_id=caso.auth[0].id,
                    user_nome=caso.auth[0].nome,
                    tenant_id=caso.auth[1],
                    db=db,
                )
                db.commit()
                return 200
            except HTTPException as exc:
                db.rollback()
                return exc.status_code

    def fechar(segundo=False):
        with (
            contexto(caso.auth[1]),
            Session(caso.db.bind, expire_on_commit=False) as db,
        ):
            if segundo:
                caixa_em_cache = db.get(Caixa, caso.atual.id)
                assert caixa_em_cache.status == "aberto"
                pid_segundo.put(db.execute(text("SELECT pg_backend_pid()")).scalar())
            return asyncio.run(
                caixa_routes.fechar_caixa.__wrapped__(
                    caixa_id=caso.atual.id,
                    dados=caixa_routes.FecharCaixaSchema(
                        valor_informado=127 if primeiro == "recebimento" else 120,
                    ),
                    request=None,
                    db=db,
                    current_user_and_tenant=caso.auth,
                )
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        primeira = pool.submit(receber if primeiro == "recebimento" else fechar)
        assert entrou.wait(3)
        segunda = pool.submit(fechar if primeiro == "recebimento" else receber, True)
        try:
            pid = pid_segundo.get(timeout=3)
            bloqueado = False
            with caso.db.bind.connect() as conn:
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
            assert bloqueado, "A segunda operação precisa aguardar a transação do caixa"
        finally:
            liberar.set()
        resultado_primeiro = primeira.result(timeout=5)
        resultado_segundo = segunda.result(timeout=5)
        if primeiro == "recebimento":
            assert resultado_primeiro == 200
            assert resultado_segundo["valor_esperado"] == 127
        else:
            assert resultado_primeiro["valor_esperado"] == 120
            assert resultado_segundo == 400
    caso.db.expire_all()
    assert caso.atual.status == "fechado"
    evento = (
        caso.db.query(AuditLog)
        .filter_by(
            action="caixa_fechado",
            entity_id=caso.atual.id,
        )
        .one()
    )
    snapshot = json.loads(evento.new_value)["resumo"]
    assert snapshot["totais"]["saldo_atual"] == (
        127 if primeiro == "recebimento" else 120
    )
