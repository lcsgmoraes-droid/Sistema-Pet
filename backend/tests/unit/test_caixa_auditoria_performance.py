"""Orçamento de consultas da auditoria com sessão fria e contratos preservados."""

from collections import Counter
from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable

from app.caixa.auditoria import assinatura_item
from app.caixa.auditoria_routes import obter_auditoria_caixa
from app.caixa_models import Caixa, MovimentacaoCaixa
from app.caixa_routes import listar_vendas_caixa, obter_resumo_caixa
from app.empresa_config_geral_models import EmpresaConfigGeral
from app.financeiro_models import ContaReceber
from app.models import AuditLog
from app.models_cadastros import Cliente
from app.produtos_models import Produto
from app.vendas_models import Venda, VendaItem, VendaPagamento


@pytest.fixture
def auditoria_engine_memoria():
    """Não usa banco local, variáveis de conexão nem dados de homologação."""
    engine = create_engine("sqlite://")
    models = (
        Caixa,
        MovimentacaoCaixa,
        Venda,
        VendaPagamento,
        VendaItem,
        AuditLog,
        EmpresaConfigGeral,
        ContaReceber,
        Cliente,
        Produto,
    )
    with engine.begin() as connection:
        for model in models:
            connection.execute(
                CreateTable(model.__table__, include_foreign_key_constraints=[])
            )
    try:
        yield engine
    finally:
        engine.dispose()


def _criar_vendas(engine, tenant_id, quantidade):
    usuario = SimpleNamespace(id=91, nome="Operador fictício")
    esperados = []
    with Session(engine) as seed:
        caixa = Caixa(
            tenant_id=tenant_id,
            numero_caixa=1,
            usuario_id=usuario.id,
            usuario_nome=usuario.nome,
            status="fechado",
            valor_abertura=0,
            data_abertura=datetime(2026, 10, 9, 8),
            data_fechamento=datetime(2026, 10, 9, 20),
        )
        seed.add(caixa)
        seed.flush()
        caixa_id = caixa.id
        for indice in range(quantidade):
            cliente_nome = f"Cliente fictício {indice}"
            produto_nome = f"Produto fictício {indice}"
            cliente = Cliente(
                tenant_id=tenant_id, user_id=usuario.id, nome=cliente_nome
            )
            produto = Produto(
                tenant_id=tenant_id,
                user_id=usuario.id,
                codigo=f"MEM-{indice}",
                nome=produto_nome,
            )
            seed.add_all([cliente, produto])
            seed.flush()
            instante = datetime(2026, 10, 9, 10) + timedelta(minutes=indice)
            venda = Venda(
                tenant_id=tenant_id,
                numero_venda=f"MEM-VENDA-{indice}",
                cliente_id=cliente.id,
                vendedor_id=usuario.id,
                user_id=usuario.id,
                caixa_id=caixa_id,
                subtotal=Decimal("10.00"),
                total=Decimal("10.00"),
                status="finalizada",
                canal="loja_fisica",
                data_venda=instante,
            )
            seed.add(venda)
            seed.flush()
            item = VendaItem(
                tenant_id=tenant_id,
                venda_id=venda.id,
                produto_id=produto.id,
                tipo="produto",
                quantidade=1,
                preco_unitario=Decimal("10.00"),
                subtotal=Decimal("10.00"),
            )
            pagamento = VendaPagamento(
                tenant_id=tenant_id,
                venda_id=venda.id,
                caixa_id=caixa_id,
                forma_pagamento="PIX",
                valor=Decimal("10.00"),
                status="pendente",
                data_pagamento=instante,
            )
            seed.add_all([item, pagamento])
            seed.flush()
            esperados.append(
                {
                    "id": venda.id,
                    "venda_id": venda.id,
                    "numero_venda": venda.numero_venda,
                    "cliente_nome": cliente_nome,
                    "total": 10.0,
                    "valor_nesta_forma": 10.0,
                    "data_venda": "2026-10-09",
                    "status": "finalizada",
                    "caixa_origem_id": caixa_id,
                    "recebimentos": [
                        {
                            "id": pagamento.id,
                            "tipo": "pagamento",
                            "forma_pagamento": "PIX",
                            "valor": 10.0,
                            "data_recebimento": instante.isoformat(),
                        }
                    ],
                    "pagamentos": [pagamento.to_dict()],
                    "itens": [
                        {
                            "id": item.id,
                            "produto_nome": produto_nome,
                            "quantidade": 1.0,
                            "subtotal": 10.0,
                        }
                    ],
                    "hora_venda": instante.strftime("%H:%M"),
                }
            )
        seed.commit()
    return caixa_id, usuario, list(reversed(esperados))


@pytest.mark.parametrize("quantidade", [1, 30])
def test_listagem_auditoria_tem_consultas_limitadas_e_preserva_contrato(
    auditoria_engine_memoria, tenant_context, quantidade
):
    engine = auditoria_engine_memoria
    tenant_id = uuid4()
    tenant_context(tenant_id)
    caixa_id, usuario, esperados = _criar_vendas(engine, tenant_id, quantidade)
    selects = []

    def contar_select(_conn, _cursor, statement, _params, _context, _executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            selects.append(statement)

    event.listen(engine, "before_cursor_execute", contar_select)
    try:
        # Uma sessão nova impede que objetos da preparação escondam consultas lazy.
        with Session(engine) as leitura:
            resultado = listar_vendas_caixa(
                caixa_id,
                db=leitura,
                current_user_and_tenant=(usuario, tenant_id),
            )
    finally:
        event.remove(engine, "before_cursor_execute", contar_select)

    assert resultado == esperados
    assert [assinatura_item(item) for item in resultado] == [
        assinatura_item(item) for item in esperados
    ]
    tabelas = Counter(
        statement.partition("\nFROM ")[2].split()[0] for statement in selects
    )
    assert len(selects) <= 10, (
        f"{quantidade} vendas geraram {len(selects)} SELECTs: {dict(tabelas)}"
    )
    assert not any("FROM contas_receber" in statement for statement in selects), (
        "A auditoria não utiliza contas a receber; não deve carregá-las automaticamente."
    )


@pytest.mark.parametrize("quantidade", [1, 30])
def test_auditoria_completa_tem_consultas_limitadas_e_preserva_assinaturas(
    auditoria_engine_memoria, tenant_context, quantidade
):
    engine = auditoria_engine_memoria
    tenant_id = uuid4()
    tenant_context(tenant_id)
    caixa_id, usuario, esperados = _criar_vendas(engine, tenant_id, quantidade)
    selects = []

    def contar_select(_conn, _cursor, statement, _params, _context, _executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            selects.append(statement)

    event.listen(engine, "before_cursor_execute", contar_select)
    try:
        with Session(engine) as leitura:
            resultado = obter_auditoria_caixa(
                caixa_id,
                db=leitura,
                current_user_and_tenant=(usuario, tenant_id),
            )
    finally:
        event.remove(engine, "before_cursor_execute", contar_select)

    def com_conferencia(item):
        return {
            **item,
            "assinatura": assinatura_item(item),
            "conferencia": None,
            "conferido": False,
        }

    assert resultado["vendas"] == [com_conferencia(item) for item in esperados]
    pagamentos_esperados = [
        {
            **venda["pagamentos"][0],
            "venda_id": venda["id"],
            "venda_numero": venda["numero_venda"],
            "data_movimento": venda["recebimentos"][0]["data_recebimento"],
            "tipo": "recebimento",
            "descricao": f"Recebimento da venda {venda['numero_venda']}",
            "natureza": "entrada",
        }
        for venda in esperados
    ]
    assert resultado["pagamentos"] == [
        com_conferencia(item) for item in pagamentos_esperados
    ]
    assert resultado["resumo"]["total_vendido"] == quantidade * 10
    assert resultado["resumo"]["total_recebido"] == quantidade * 10
    assert resultado["movimentacoes"] == []
    assert resultado["espelhos_pagamentos"] == []
    assert resultado["historico"] == []
    assert "movimentacoes" not in resultado["resumo"]["caixa"]
    tabelas = Counter(
        statement.partition("\nFROM ")[2].split()[0] for statement in selects
    )
    assert len(selects) <= 30, (
        f"Auditoria de {quantidade} vendas gerou {len(selects)} SELECTs: {dict(tabelas)}"
    )
    assert not any("FROM contas_receber" in statement for statement in selects), (
        "A leitura dos pagamentos do caixa não deve carregar contas a receber."
    )


def test_resumo_compacto_preserva_valores_e_evitaria_movimentos_duplicados(
    auditoria_engine_memoria, tenant_context
):
    engine = auditoria_engine_memoria
    tenant_id = uuid4()
    tenant_context(tenant_id)
    caixa_id, usuario, esperados = _criar_vendas(engine, tenant_id, 1)
    with Session(engine) as seed:
        seed.add(
            MovimentacaoCaixa(
                tenant_id=tenant_id,
                caixa_id=caixa_id,
                tipo="suprimento",
                forma_pagamento="Dinheiro",
                valor=5,
                usuario_id=usuario.id,
                usuario_nome=usuario.nome,
                data_movimento=datetime(2026, 10, 9, 9),
            )
        )
        seed.commit()

    auth = (usuario, tenant_id)
    with Session(engine) as leitura:
        completo = obter_resumo_caixa(
            caixa_id, db=leitura, current_user_and_tenant=auth
        )
    with Session(engine) as leitura:
        compacto = obter_resumo_caixa(
            caixa_id, db=leitura, current_user_and_tenant=auth, compact=True
        )
    with Session(engine) as leitura:
        auditoria = obter_auditoria_caixa(
            caixa_id, db=leitura, current_user_and_tenant=auth
        )

    # Default completo permanece compatível; compact omite a chave, não os valores.
    movimentos_completos = completo["caixa"].pop("movimentacoes")
    assert len(movimentos_completos) == 1
    assert movimentos_completos[0]["valor"] == 5
    assert "movimentacoes" not in compacto["caixa"]
    assert completo == compacto == auditoria["resumo"]
    assert compacto["total_recebido"] == compacto["total_vendido"] == 10
    assert compacto["totais"]["suprimentos"] == compacto["totais"]["saldo_atual"] == 5
    assert len(auditoria["movimentacoes"]) == 1
    assert auditoria["movimentacoes"][0]["id"] == movimentos_completos[0]["id"]
    assert auditoria["vendas"][0]["pagamentos"] == esperados[0]["pagamentos"]
    assert auditoria["vendas"][0]["assinatura"] == assinatura_item(esperados[0])
