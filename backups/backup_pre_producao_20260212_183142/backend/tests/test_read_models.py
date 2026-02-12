"""
Testes de Read Models - CQRS
==============================

Testes simples que validam a atualização de read models via eventos.

ESTRATÉGIA:
- Publicar eventos fake
- Validar que read models foram atualizados corretamente
- Usar banco em memória para isolamento
- Não depender do VendaService
"""

import pytest
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.domain.events.venda_events import VendaCriada, VendaFinalizada, VendaCancelada
from app.read_models.models import VendasResumoDiario, PerformanceParceiro, ReceitaMensal
from app.read_models.handlers import VendaReadModelHandler


# ===== FIXTURES =====

@pytest.fixture
def engine():
    """Cria engine SQLite em memória para testes"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(engine):
    """Cria sessão de banco isolada para cada teste"""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def handler(db_session):
    """Cria handler de read models para testes"""
    return VendaReadModelHandler(db_session)


# ===== TESTES DE VENDA CRIADA =====

def test_evento_venda_criada_atualiza_resumo_diario(handler, db_session):
    """
    DADO um resumo diário vazio
    QUANDO uma VendaCriada é processada
    ENTÃO o resumo deve incrementar quantidade_aberta
    """
    # Arrange
    hoje = date.today()
    evento = VendaCriada(
        venda_id=1,
        numero_venda="VEN-20260123-0001",
        user_id=1,
        cliente_id=10,
        funcionario_id=5,
        total=100.00,
        quantidade_itens=3,
        tem_entrega=False
    )
    
    # Act
    handler.on_venda_criada(evento)
    
    # Assert
    resumo = db_session.query(VendasResumoDiario).filter(
        VendasResumoDiario.data == hoje
    ).first()
    
    assert resumo is not None
    assert resumo.quantidade_aberta == 1
    assert resumo.quantidade_finalizada == 0
    assert resumo.quantidade_cancelada == 0


def test_multiplas_vendas_criadas_incrementam_contador(handler, db_session):
    """
    DADO múltiplos eventos VendaCriada
    QUANDO processados sequencialmente
    ENTÃO o contador deve incrementar corretamente
    """
    # Arrange & Act
    for i in range(1, 6):
        evento = VendaCriada(
            venda_id=i,
            numero_venda=f"VEN-20260123-000{i}",
            user_id=1,
            cliente_id=10,
            funcionario_id=5,
            total=100.00 * i,
            quantidade_itens=i,
            tem_entrega=False
        )
        handler.on_venda_criada(evento)
    
    # Assert
    hoje = date.today()
    resumo = db_session.query(VendasResumoDiario).filter(
        VendasResumoDiario.data == hoje
    ).first()
    
    assert resumo.quantidade_aberta == 5


# ===== TESTES DE VENDA FINALIZADA =====

def test_evento_venda_finalizada_atualiza_resumo_diario(handler, db_session):
    """
    DADO uma venda aberta
    QUANDO VendaFinalizada é processada
    ENTÃO resumo deve atualizar vendas finalizadas e total
    """
    # Arrange
    hoje = date.today()
    evento = VendaFinalizada(
        venda_id=1,
        numero_venda="VEN-20260123-0001",
        user_id=1,
        user_nome="João Silva",
        cliente_id=10,
        funcionario_id=5,
        total=250.50,
        total_pago=250.50,
        status="finalizada",
        formas_pagamento=["dinheiro"],
        estoque_baixado=True,
        caixa_movimentado=True,
        contas_baixadas=1
    )
    
    # Act
    handler.on_venda_finalizada(evento)
    
    # Assert
    resumo = db_session.query(VendasResumoDiario).filter(
        VendasResumoDiario.data == hoje
    ).first()
    
    assert resumo is not None
    assert resumo.quantidade_finalizada == 1
    assert float(resumo.total_vendido) == 250.50
    assert float(resumo.ticket_medio) == 250.50


def test_venda_finalizada_atualiza_performance_parceiro(handler, db_session):
    """
    DADO um funcionário sem vendas
    QUANDO VendaFinalizada com funcionario_id é processada
    ENTÃO performance do parceiro deve ser criada/atualizada
    """
    # Arrange
    hoje = date.today()
    mes_atual = date(hoje.year, hoje.month, 1)
    funcionario_id = 5
    
    evento = VendaFinalizada(
        venda_id=1,
        numero_venda="VEN-20260123-0001",
        user_id=1,
        user_nome="João Silva",
        cliente_id=10,
        funcionario_id=funcionario_id,
        total=500.00,
        total_pago=500.00,
        status="finalizada",
        formas_pagamento=["pix"],
        estoque_baixado=True,
        caixa_movimentado=True,
        contas_baixadas=1
    )
    
    # Act
    handler.on_venda_finalizada(evento)
    
    # Assert
    performance = db_session.query(PerformanceParceiro).filter(
        PerformanceParceiro.funcionario_id == funcionario_id,
        PerformanceParceiro.mes_referencia == mes_atual
    ).first()
    
    assert performance is not None
    assert performance.quantidade_vendas == 1
    assert float(performance.total_vendido) == 500.00
    assert float(performance.ticket_medio) == 500.00


def test_venda_finalizada_atualiza_receita_mensal(handler, db_session):
    """
    DADO receita mensal vazia
    QUANDO VendaFinalizada é processada
    ENTÃO receita mensal deve ser criada/atualizada
    """
    # Arrange
    hoje = date.today()
    mes_atual = date(hoje.year, hoje.month, 1)
    
    evento = VendaFinalizada(
        venda_id=1,
        numero_venda="VEN-20260123-0001",
        user_id=1,
        user_nome="João Silva",
        cliente_id=10,
        funcionario_id=None,
        total=1000.00,
        total_pago=1000.00,
        status="finalizada",
        formas_pagamento=["cartao"],
        estoque_baixado=True,
        caixa_movimentado=False,
        contas_baixadas=1
    )
    
    # Act
    handler.on_venda_finalizada(evento)
    
    # Assert
    receita = db_session.query(ReceitaMensal).filter(
        ReceitaMensal.mes_referencia == mes_atual
    ).first()
    
    assert receita is not None
    assert float(receita.receita_bruta) == 1000.00
    assert float(receita.receita_liquida) == 1000.00
    assert receita.quantidade_vendas == 1


# ===== TESTES DE VENDA CANCELADA =====

def test_evento_venda_cancelada_atualiza_resumo_diario(handler, db_session):
    """
    DADO vendas registradas
    QUANDO VendaCancelada é processada
    ENTÃO resumo deve incrementar cancelamentos
    """
    # Arrange
    hoje = date.today()
    evento = VendaCancelada(
        venda_id=1,
        numero_venda="VEN-20260123-0001",
        user_id=1,
        cliente_id=10,
        funcionario_id=5,
        motivo="Cliente desistiu",
        status_anterior="aberta",
        total=150.00,
        itens_estornados=2,
        contas_canceladas=1,
        comissoes_estornadas=False
    )
    
    # Act
    handler.on_venda_cancelada(evento)
    
    # Assert
    resumo = db_session.query(VendasResumoDiario).filter(
        VendasResumoDiario.data == hoje
    ).first()
    
    assert resumo is not None
    assert resumo.quantidade_cancelada == 1
    assert float(resumo.total_cancelado) == 150.00


def test_venda_cancelada_atualiza_performance_parceiro(handler, db_session):
    """
    DADO um funcionário com vendas
    QUANDO VendaCancelada é processada
    ENTÃO contador de cancelamentos deve incrementar
    """
    # Arrange
    hoje = date.today()
    mes_atual = date(hoje.year, hoje.month, 1)
    funcionario_id = 7
    
    evento = VendaCancelada(
        venda_id=2,
        numero_venda="VEN-20260123-0002",
        user_id=1,
        cliente_id=15,
        funcionario_id=funcionario_id,
        motivo="Erro no pedido",
        status_anterior="finalizada",
        total=300.00,
        itens_estornados=3,
        contas_canceladas=1,
        comissoes_estornadas=True
    )
    
    # Act
    handler.on_venda_cancelada(evento)
    
    # Assert
    performance = db_session.query(PerformanceParceiro).filter(
        PerformanceParceiro.funcionario_id == funcionario_id,
        PerformanceParceiro.mes_referencia == mes_atual
    ).first()
    
    assert performance is not None
    assert performance.vendas_canceladas == 1


def test_venda_cancelada_atualiza_receita_mensal(handler, db_session):
    """
    DADO receita mensal existente
    QUANDO VendaCancelada é processada
    ENTÃO receita cancelada deve incrementar
    """
    # Arrange
    hoje = date.today()
    mes_atual = date(hoje.year, hoje.month, 1)
    
    evento = VendaCancelada(
        venda_id=3,
        numero_venda="VEN-20260123-0003",
        user_id=1,
        cliente_id=20,
        funcionario_id=None,
        motivo="Produto indisponível",
        status_anterior="aberta",
        total=450.00,
        itens_estornados=0,
        contas_canceladas=0,
        comissoes_estornadas=False
    )
    
    # Act
    handler.on_venda_cancelada(evento)
    
    # Assert
    receita = db_session.query(ReceitaMensal).filter(
        ReceitaMensal.mes_referencia == mes_atual
    ).first()
    
    assert receita is not None
    assert float(receita.receita_cancelada) == 450.00
    assert receita.quantidade_cancelamentos == 1


# ===== TESTES DE FLUXO COMPLETO =====

def test_fluxo_completo_venda(handler, db_session):
    """
    DADO um fluxo completo de venda
    QUANDO eventos são processados na ordem
    ENTÃO todos os read models devem estar consistentes
    """
    # Arrange
    hoje = date.today()
    mes_atual = date(hoje.year, hoje.month, 1)
    funcionario_id = 10
    
    # 1️⃣ Criar venda
    evento_criada = VendaCriada(
        venda_id=10,
        numero_venda="VEN-20260123-0010",
        user_id=1,
        cliente_id=25,
        funcionario_id=funcionario_id,
        total=800.00,
        quantidade_itens=5,
        tem_entrega=True
    )
    handler.on_venda_criada(evento_criada)
    
    # 2️⃣ Finalizar venda
    evento_finalizada = VendaFinalizada(
        venda_id=10,
        numero_venda="VEN-20260123-0010",
        user_id=1,
        user_nome="Maria Santos",
        cliente_id=25,
        funcionario_id=funcionario_id,
        total=800.00,
        total_pago=800.00,
        status="finalizada",
        formas_pagamento=["pix"],
        estoque_baixado=True,
        caixa_movimentado=True,
        contas_baixadas=1
    )
    handler.on_venda_finalizada(evento_finalizada)
    
    # Assert - Resumo Diário
    resumo = db_session.query(VendasResumoDiario).filter(
        VendasResumoDiario.data == hoje
    ).first()
    assert resumo.quantidade_aberta == 0  # Decrementado ao finalizar
    assert resumo.quantidade_finalizada == 1
    assert float(resumo.total_vendido) == 800.00
    
    # Assert - Performance Parceiro
    performance = db_session.query(PerformanceParceiro).filter(
        PerformanceParceiro.funcionario_id == funcionario_id,
        PerformanceParceiro.mes_referencia == mes_atual
    ).first()
    assert performance.quantidade_vendas == 1
    assert float(performance.total_vendido) == 800.00
    
    # Assert - Receita Mensal
    receita = db_session.query(ReceitaMensal).filter(
        ReceitaMensal.mes_referencia == mes_atual
    ).first()
    assert float(receita.receita_bruta) == 800.00
    assert receita.quantidade_vendas == 1


def test_multiplos_funcionarios_ranking(handler, db_session):
    """
    DADO múltiplos funcionários com vendas
    QUANDO consultamos performance
    ENTÃO podemos ordenar por total vendido
    """
    # Arrange
    hoje = date.today()
    mes_atual = date(hoje.year, hoje.month, 1)
    
    vendas = [
        (1, 5, 1000.00),   # Funcionário 5: R$ 1000
        (2, 7, 1500.00),   # Funcionário 7: R$ 1500
        (3, 5, 500.00),    # Funcionário 5: R$ 1500 total
        (4, 9, 2000.00),   # Funcionário 9: R$ 2000
    ]
    
    # Act
    for venda_id, funcionario_id, total in vendas:
        evento = VendaFinalizada(
            venda_id=venda_id,
            numero_venda=f"VEN-20260123-{venda_id:04d}",
            user_id=1,
            user_nome="Vendedor",
            cliente_id=100,
            funcionario_id=funcionario_id,
            total=total,
            total_pago=total,
            status="finalizada",
            formas_pagamento=["pix"],
            estoque_baixado=True,
            caixa_movimentado=True,
            contas_baixadas=1
        )
        handler.on_venda_finalizada(evento)
    
    # Assert - Ranking
    performances = db_session.query(PerformanceParceiro).filter(
        PerformanceParceiro.mes_referencia == mes_atual
    ).order_by(PerformanceParceiro.total_vendido.desc()).all()
    
    assert len(performances) == 3  # 3 funcionários únicos
    assert performances[0].funcionario_id == 9  # 1º lugar
    assert float(performances[0].total_vendido) == 2000.00
    assert performances[1].funcionario_id == 5  # 2º lugar
    assert float(performances[1].total_vendido) == 1500.00
    assert performances[2].funcionario_id == 7  # 3º lugar
    assert float(performances[2].total_vendido) == 1500.00


# ===== TESTES DE ROBUSTEZ =====

def test_handler_nao_falha_em_caso_de_erro(handler, db_session, caplog):
    """
    DADO um handler configurado
    QUANDO ocorre erro no processamento
    ENTÃO o erro deve ser logado mas não propagado
    """
    # Arrange
    import logging
    caplog.set_level(logging.ERROR)
    
    # Forçar erro fechando a sessão
    db_session.close()
    
    evento = VendaCriada(
        venda_id=999,
        numero_venda="VEN-20260123-0999",
        user_id=1,
        cliente_id=10,
        funcionario_id=5,
        total=100.00,
        quantidade_itens=1,
        tem_entrega=False
    )
    
    # Act - Não deve lançar exceção
    handler.on_venda_criada(evento)
    
    # Assert - Erro deve ser logado
    assert "Erro ao processar VendaCriada" in caplog.text


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
