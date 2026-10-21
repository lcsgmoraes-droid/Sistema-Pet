"""Mesmo banco DEV descartável alimenta caixa, dashboard e app gestor."""

import json
import os
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import Enum
from sqlalchemy.schema import CreateTable

from app.caixa_models import MovimentacaoCaixa
from app.caixa.auditoria_routes import obter_auditoria_caixa
from app.caixa_routes import obter_resumo_caixa
from app.dashboard_routes import obter_entradas_saidas_por_dia, obter_resumo_dashboard
from app.db import Base
from app.financeiro_models import ContaPagar, ContaReceber, FormaPagamento, Recebimento
from app.routes.app_mobile_gestor_routes import (
    GestorContaResumo,
    GestorDREResumo,
    GestorFluxoDiaResumo,
    obter_resumo_gestor_mobile,
)
from app.vendas_devolucoes_models import VendaDevolucao
from app.vendas_models import Venda, VendaPagamento
from tests.unit.test_caixa_recebimentos_auditoria import caixa_session, recebimentos  # noqa: F401


@pytest.fixture
def cenario(request, monkeypatch):
    caso = request.getfixturevalue("recebimentos")
    tabelas = [
        ContaPagar.__table__,
        FormaPagamento.__table__,
        Recebimento.__table__,
        VendaDevolucao.__table__,
    ]
    engine = caso.db.get_bind()
    if engine.dialect.name == "postgresql":
        # A fixture cria um schema UUID descartável. Não depender nem escrever
        # em users/clientes/categorias do banco DEV público para testar valores.
        for tabela in tabelas:
            for coluna in tabela.columns:
                if isinstance(coluna.type, Enum):
                    coluna.type.create(engine, checkfirst=True)
            with engine.begin() as conn:
                conn.execute(CreateTable(tabela, include_foreign_key_constraints=[]))
    else:
        Base.metadata.create_all(engine, tables=tabelas)

    def agora():
        return datetime(2026, 10, 9, 18)

    monkeypatch.setattr("app.services.faturamento_service.now_brasilia", agora)
    monkeypatch.setattr("app.dashboard_routes.now_brasilia", agora)
    monkeypatch.setattr("app.routes.app_mobile_gestor_routes.now_brasilia", agora)
    tenant = caso.auth[1]
    nova = Venda(
        tenant_id=tenant,
        numero_venda="202610090001",
        user_id=91,
        vendedor_id=91,
        caixa_id=caso.atual.id,
        subtotal=100,
        total=105,
        desconto_valor=10,
        taxa_entrega=15,
        status="baixa_parcial",
        data_venda=datetime(2026, 10, 9, 10),
        canal="loja_fisica",
    )
    aberta = Venda(
        tenant_id=tenant,
        numero_venda="202610090002",
        user_id=91,
        vendedor_id=91,
        caixa_id=None,
        subtotal=20,
        total=20,
        status="aberta",
        data_venda=datetime(2026, 10, 9, 11),
        canal="loja_fisica",
    )
    devolvida = Venda(
        tenant_id=tenant,
        numero_venda="202610090003",
        user_id=91,
        vendedor_id=91,
        caixa_id=caso.atual.id,
        subtotal=100,
        total=100,
        status="finalizada_devolucao",
        data_venda=datetime(2026, 10, 9, 13),
        canal="loja_fisica",
    )
    cancelada = Venda(
        tenant_id=tenant,
        numero_venda="202610090004",
        user_id=91,
        vendedor_id=91,
        caixa_id=caso.atual.id,
        subtotal=999,
        total=999,
        status="cancelada",
        data_venda=datetime(2026, 10, 9, 14),
        canal="loja_fisica",
    )
    caso.db.add_all([nova, aberta, devolvida, cancelada])
    caso.db.flush()
    for valor, forma, forma_id in [
        (40, "Dinheiro", 1),
        (10, "PIX", 2),
        (5, "Cashback", 3),
        (50, "Crediário", 4),
    ]:
        caso.db.add(
            VendaPagamento(
                tenant_id=tenant,
                venda_id=nova.id,
                caixa_id=caso.atual.id,
                forma_pagamento=forma,
                forma_pagamento_id=forma_id,
                valor=valor,
                status="confirmado",
                data_pagamento=datetime(2026, 10, 9, 10),
            )
        )
    caso.db.add(
        VendaPagamento(
            tenant_id=tenant,
            venda_id=devolvida.id,
            caixa_id=caso.atual.id,
            forma_pagamento="PIX",
            valor=100,
            status="confirmado",
            data_pagamento=datetime(2026, 10, 9, 13),
        )
    )
    caso.db.add(
        ContaReceber(
            tenant_id=tenant,
            venda_id=nova.id,
            descricao="Crediário da venda",
            forma_pagamento_id=4,
            valor_original=50,
            valor_final=50,
            valor_recebido=0,
            dre_subcategoria_id=1,
            canal="loja_fisica",
            user_id=91,
            data_emissao=date(2026, 10, 9),
            data_vencimento=date(2026, 11, 9),
            status="pendente",
        )
    )
    caso.db.add_all(
        [
            MovimentacaoCaixa(
                tenant_id=tenant,
                caixa_id=caso.atual.id,
                venda_id=nova.id,
                tipo="venda",
                forma_pagamento="Dinheiro",
                valor=40,
                usuario_id=91,
                usuario_nome="Operador DEV",
                data_movimento=datetime(2026, 10, 9, 10),
            ),
            MovimentacaoCaixa(
                tenant_id=tenant,
                caixa_id=caso.atual.id,
                venda_id=devolvida.id,
                tipo="devolucao",
                forma_pagamento="Dinheiro",
                valor=25,
                usuario_id=91,
                usuario_nome="Operador DEV",
                data_movimento=datetime(2026, 10, 9, 14),
            ),
            VendaDevolucao(
                tenant_id=tenant,
                venda_id=devolvida.id,
                user_id=91,
                chave_operacao=str(uuid4()),
                requisicao_hash="dev",
                resposta={},
                data_competencia=date(2026, 10, 9),
                canal="loja_fisica",
                status_original_venda="finalizada",
                forma_estorno="dinheiro",
                motivo="Teste DEV",
                valor_devolvido=25,
                custo_produtos_estornado=0,
                custo_servicos_estornado=0,
                custo_pendente=False,
                itens=[],
            ),
        ]
    )
    caso.db.flush()
    # Outro tenant e limites 00h não podem ser incorporados por conveniência.
    caso.db.execute(
        Venda.__table__.insert(),
        [
            {
                "tenant_id": uuid4(),
                "numero_venda": "OUTRA-EMPRESA",
                "user_id": 91,
                "vendedor_id": 91,
                "total": 99999,
                "subtotal": 99999,
                "status": "finalizada",
                "data_venda": datetime(2026, 10, 9, 10),
                "canal": "loja_fisica",
            },
            {
                "tenant_id": tenant,
                "numero_venda": "CANCELADO",
                "user_id": 91,
                "vendedor_id": 91,
                "total": 99999,
                "subtotal": 99999,
                "status": "cancelado",
                "data_venda": datetime(2026, 10, 9, 10),
                "canal": "loja_fisica",
            },
            {
                "tenant_id": tenant,
                "numero_venda": "AMANHA",
                "user_id": 91,
                "vendedor_id": 91,
                "total": 500,
                "subtotal": 500,
                "status": "finalizada",
                "data_venda": datetime(2026, 10, 10, 0),
                "canal": "loja_fisica",
            },
        ],
    )
    caso.db.expire_all()
    return caso


@pytest.mark.asyncio
async def test_superficies_compartilham_calculo_e_explicitam_empresa_versus_caixa(
    cenario, monkeypatch
):
    caso = cenario
    dashboard = await obter_resumo_dashboard(1, caso.db, caso.auth)
    grafico = await obter_entradas_saidas_por_dia(1, caso.db, caso.auth)
    caixa = obter_resumo_caixa(caso.atual.id, caso.db, caso.auth, compact=True)
    # Os blocos bancários independentes são irrelevantes a esta prova comercial;
    # autenticação/perfil têm seus testes próprios. A seleção ORM de vendas e
    # composição do endpoint mobile permanece real.
    monkeypatch.setattr(
        "app.routes.app_mobile_gestor_routes._get_gestor_tenant_or_403",
        lambda *_: caso.auth[1],
    )
    monkeypatch.setattr(
        "app.routes.app_mobile_gestor_routes._resumo_fluxo_hoje",
        lambda *_: GestorFluxoDiaResumo(data=date(2026, 10, 9)),
    )
    monkeypatch.setattr(
        "app.routes.app_mobile_gestor_routes._resumo_dre",
        lambda *_: GestorDREResumo(periodo="10/2026", criterio="competencia_do_mes"),
    )
    monkeypatch.setattr(
        "app.routes.app_mobile_gestor_routes._resumir_contas",
        lambda *_args, **_kwargs: GestorContaResumo(),
    )
    mobile_model = obter_resumo_gestor_mobile(
        date(2026, 10, 9), date(2026, 10, 9), caso.auth[0], caso.db
    )
    mobile = mobile_model.model_dump(mode="json")
    assert dashboard["composicao_vendas"] == mobile["vendas"]["composicao"]
    assert dashboard["composicao_vendas"]["escopo"] == "empresa"
    vendas = caixa["vendas_periodo"]
    assert vendas["escopo"] == "caixa"
    assert vendas["caixa_id"] == caso.atual.id
    assert vendas["criterio"] == "origem_caixa_e_data_venda"
    assert (
        sum(Decimal(str(dia["entradas"])) for dia in grafico)
        == Decimal(str(dashboard["fluxo_periodo"]["entradas"]))
        == Decimal("125")
    )
    assert dashboard["vendas_periodo"]["quantidade"] == 3
    assert vendas["quantidade"] == 2
    assert vendas["faturamento_bruto"] == 200
    assert vendas["descontos"] == 10
    assert vendas["devolucoes"] == 25
    assert vendas["faturamento_liquido"] == 165
    assert vendas["taxa_entrega"] == 15
    assert vendas["total_vendas"] == 180
    assert vendas["valor_pago"] == 125
    assert vendas["creditos_utilizados"] == 5
    assert vendas["crediario_receber"] == 50
    assert vendas["em_aberto"] == 0
    # A venda sem caixa continua no painel/app, mas nao no caixa auditado.
    assert dashboard["composicao_vendas"]["em_aberto"] == 20
    assert mobile["vendas"]["faturamento_liquido"] == 185
    assert (
        dashboard["vendas_periodo"]["ticket_medio"]
        == mobile["vendas"]["ticket_medio"]
        == 61.67
    )
    recebido = caixa["composicao_recebimentos"]
    assert recebido["vendas_periodo"] == 150
    assert recebido["vendas_anteriores"] == 60
    assert recebido["devolucoes"] == 25
    assert recebido["total_recebido"] == 185
    assert recebido["creditos_utilizados"] == 5
    assert sum(
        Decimal(str(forma["total"]))
        for forma in recebido["por_forma_pagamento"].values()
    ) == Decimal("185")
    assert not {"Cashback", "Crediário"} & set(recebido["por_forma_pagamento"])
    assert caso.db.get(Venda, caso.venda.id).caixa_id == caso.original.id
    assert caso.db.get(Venda, caso.venda.id).data_venda == datetime(2026, 10, 8, 10)
    destino = os.environ.get("FATURAMENTO_DEV_SNAPSHOT")
    if destino:
        path = Path(destino).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "dashboard": dashboard,
                    "caixa": caixa,
                    "mobile": mobile,
                    "entradas_saidas": grafico,
                    "auditoria": obter_auditoria_caixa(
                        caso.atual.id, caso.db, caso.auth
                    ),
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )


def test_caixa_fechado_preserva_periodo_civil_original(cenario, monkeypatch):
    caso = cenario
    caso.atual.status = "fechado"
    caso.atual.data_fechamento = datetime(2026, 10, 9, 19)
    caso.atual.fechamento_em = datetime(2026, 10, 9, 19)
    caso.db.flush()
    monkeypatch.setattr(
        "app.services.faturamento_service.now_brasilia",
        lambda: datetime(2026, 10, 20, 18),
    )
    resultado = obter_resumo_caixa(caso.atual.id, caso.db, caso.auth, compact=True)
    assert resultado["vendas_periodo"]["data_inicio"] == "2026-10-09"
    assert resultado["vendas_periodo"]["data_fim"] == "2026-10-09"
    assert resultado["vendas_periodo"]["faturamento_liquido"] == 165


def test_auditoria_separa_tres_antigas_beneficios_e_origem_com_datas_fixas(
    cenario, monkeypatch
):
    caso = cenario
    tenant = caso.auth[1]
    antigas = []
    for numero, dia, total in [("ANTIGA-2", 7, 15), ("ANTIGA-3", 8, 20)]:
        venda = Venda(
            tenant_id=tenant,
            numero_venda=numero,
            user_id=91,
            vendedor_id=91,
            caixa_id=caso.atual.id,
            subtotal=total,
            total=total,
            status="finalizada",
            data_venda=datetime(2026, 10, dia, 10),
            canal="loja_fisica",
        )
        caso.db.add(venda)
        antigas.append(venda)
    outra_origem = Venda(
        tenant_id=tenant,
        numero_venda="OUTRO-CAIXA-HOJE",
        user_id=91,
        vendedor_id=91,
        caixa_id=caso.original.id,
        subtotal=15,
        total=15,
        status="finalizada",
        data_venda=datetime(2026, 10, 9, 15),
        canal="loja_fisica",
    )
    caso.db.add(outra_origem)
    caso.db.flush()
    cancelada = (
        caso.db.query(Venda)
        .filter(Venda.tenant_id == tenant, Venda.numero_venda == "202610090004")
        .one()
    )
    for venda, valor, forma, status in [
        (antigas[0], 12, "PIX", "confirmado"),
        (antigas[0], 3, "Credito Cliente", "confirmado"),
        (antigas[1], 18, "Cartao de credito", "confirmado"),
        (antigas[1], 2, "Cashback", "confirmado"),
        (outra_origem, 15, "PIX", "confirmado"),
        (cancelada, 30, "PIX", "confirmado"),
        (cancelada, 999, "PIX", "estornado"),
    ]:
        caso.db.add(
            VendaPagamento(
                tenant_id=tenant,
                venda_id=venda.id,
                caixa_id=caso.atual.id,
                forma_pagamento=forma,
                valor=valor,
                status=status,
                data_pagamento=datetime(2026, 10, 9, 16),
            )
        )
    # Espelho eletronico deve continuar no extrato, sem duplicar o recebimento.
    caso.db.add(
        MovimentacaoCaixa(
            tenant_id=tenant,
            caixa_id=caso.atual.id,
            venda_id=antigas[0].id,
            tipo="venda",
            categoria="venda",
            descricao=f"Baixa venda #{antigas[0].id} - teste DEV",
            forma_pagamento="PIX",
            valor=12,
            usuario_id=91,
            usuario_nome="Operador DEV",
            data_movimento=datetime(2026, 10, 9, 16),
        )
    )
    outro_tenant = uuid4()
    id_outra_empresa = caso.db.execute(
        Venda.__table__.insert().returning(Venda.id),
        {
            "tenant_id": outro_tenant,
            "numero_venda": "OUTRO-TENANT-CAIXA",
            "user_id": 91,
            "vendedor_id": 91,
            "caixa_id": caso.atual.id,
            "total": 99999,
            "subtotal": 99999,
            "status": "finalizada",
            "data_venda": datetime(2026, 10, 9, 10),
            "canal": "loja_fisica",
        },
    ).scalar_one()
    caso.db.execute(
        VendaPagamento.__table__.insert(),
        {
            "tenant_id": outro_tenant,
            "venda_id": id_outra_empresa,
            "caixa_id": caso.atual.id,
            "forma_pagamento": "PIX",
            "valor": 99999,
            "status": "confirmado",
            "data_pagamento": datetime(2026, 10, 9, 10),
        },
    )
    caso.atual.status = "fechado"
    caso.atual.fechamento_em = datetime(2026, 10, 9, 19)
    caso.atual.data_fechamento = datetime(2026, 10, 9, 19)
    caso.db.flush()
    monkeypatch.setattr(
        "app.services.faturamento_service.now_brasilia",
        lambda: datetime(2026, 10, 20, 18),
    )

    auditoria = obter_auditoria_caixa(caso.atual.id, caso.db, caso.auth)
    resumo = obter_resumo_caixa(caso.atual.id, caso.db, caso.auth, compact=True)
    assert auditoria["resumo"]["vendas_periodo"] == resumo["vendas_periodo"]
    assert (
        auditoria["resumo"]["composicao_recebimentos"]
        == resumo["composicao_recebimentos"]
    )
    vendas = auditoria["resumo"]["vendas_periodo"]
    recebido = auditoria["resumo"]["composicao_recebimentos"]
    for bloco in (vendas, recebido):
        assert bloco["escopo"] == "caixa"
        assert bloco["caixa_id"] == caso.atual.id
        assert bloco["numero_caixa"] == caso.atual.numero_caixa
        assert bloco["data_inicio"] == bloco["data_fim"] == "2026-10-09"
    ids_vendas = {item["venda_id"] for item in vendas["detalhes"]}
    assert vendas["quantidade"] == 2
    assert vendas["faturamento_liquido"] == 165
    assert vendas["creditos_utilizados"] == 5
    assert vendas["crediario_receber"] == 50
    assert not ids_vendas & {
        caso.venda.id,
        antigas[0].id,
        antigas[1].id,
        outra_origem.id,
        cancelada.id,
        id_outra_empresa,
    }
    assert recebido["vendas_periodo"] == 195
    assert recebido["vendas_anteriores"] == 90
    assert recebido["devolucoes"] == 25
    assert recebido["total_recebido"] == 260
    assert recebido["creditos_utilizados"] == 10
    assert sum(
        Decimal(str(item["total"])) for item in recebido["por_forma_pagamento"].values()
    ) == Decimal("260")
    assert not {"Credito Cliente", "Cashback", "Crediário"} & set(
        recebido["por_forma_pagamento"]
    )
    assert {
        item["venda_id"]
        for item in recebido["detalhes"]
        if item["data_venda"][:10] < "2026-10-09"
    } == {caso.venda.id, antigas[0].id, antigas[1].id}
    assert all(item["venda_id"] != id_outra_empresa for item in recebido["detalhes"])
    # Recebimento efetivo de venda depois cancelada continua rastreavel;
    # pagamento estornado, beneficios e plano nao viram dinheiro novo.
    assert any(item["venda_id"] == cancelada.id for item in recebido["detalhes"])
    assert len(auditoria["espelhos_pagamentos"]) == 1
    assert len(recebido["detalhes_creditos"]) == 3
