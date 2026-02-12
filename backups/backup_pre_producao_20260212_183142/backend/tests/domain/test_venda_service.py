"""
Testes de Domínio - VendaService (Casos Felizes)
=================================================

Testes das operações principais do VendaService:
- criar_venda
- finalizar_venda
- cancelar_venda

SEM usar FastAPI, rotas ou banco real.
Foco em REGRAS DE NEGÓCIO e EVENTOS DE DOMÍNIO.
"""

import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime, date, timedelta
from decimal import Decimal

from app.vendas.service import VendaService
from app.domain.events import VendaCriada, VendaFinalizada, VendaCancelada


# ============================================================
# TESTES: CRIAR VENDA
# ============================================================


class TestCriarVenda:
    """Testes para VendaService.criar_venda()"""
    
    def test_criar_venda_simples_sucesso(
        self,
        mock_db_session,
        mock_event_dispatcher,
        fake_venda_data,
        fake_venda_model
    ):
        """
        CENÁRIO: Criar uma venda simples com 1 item
        ESPERA: 
        - Venda criada com sucesso
        - Evento VendaCriada publicado
        - Commit executado
        """
        # ARRANGE
        with patch('app.vendas.service.Venda') as MockVenda, \
             patch('app.vendas.service.VendaItem') as MockVendaItem, \
             patch('app.vendas.service.ContaReceber') as MockContaReceber, \
             patch('app.vendas.service.LancamentoManual') as MockLancamento, \
             patch('app.vendas.service.CategoriaFinanceira') as MockCategoria, \
             patch('app.vendas.service.log_action'):
            
            # Configurar mock de Venda
            MockVenda.return_value = fake_venda_model
            
            # Configurar categoria financeira existente
            categoria_mock = MagicMock()
            categoria_mock.id = 1
            categoria_mock.nome = 'Receitas de Vendas'
            mock_db_session.query.return_value.filter.return_value.first.return_value = categoria_mock
            
            # ACT
            resultado = VendaService.criar_venda(
                payload=fake_venda_data,
                user_id=1,
                db=mock_db_session
            )
            
            # ASSERT
            assert resultado is not None
            assert resultado['id'] == 100
            assert resultado['numero_venda'] == '202601230001'
            assert resultado['status'] == 'aberta'
            
            # Verificar que commit foi chamado
            mock_db_session.commit.assert_called_once()
            
            # Verificar que evento foi publicado
            assert len(mock_event_dispatcher.eventos_publicados) == 1
            evento = mock_event_dispatcher.eventos_publicados[0]
            assert isinstance(evento, VendaCriada)
            assert evento.venda_id == 100
            assert evento.numero_venda == '202601230001'
            assert evento.total == 100.0
            assert evento.quantidade_itens == 1
    
    def test_criar_venda_com_multiplos_itens(
        self,
        mock_db_session,
        mock_event_dispatcher,
        fake_venda_model
    ):
        """
        CENÁRIO: Criar venda com múltiplos itens
        ESPERA: Todos os itens criados e total calculado corretamente
        """
        # ARRANGE
        payload = {
            'cliente_id': 1,
            'itens': [
                {'produto_id': 10, 'quantidade': 2, 'preco_unitario': 50, 'subtotal': 100},
                {'produto_id': 20, 'quantidade': 1, 'preco_unitario': 30, 'subtotal': 30},
                {'produto_id': 30, 'quantidade': 3, 'preco_unitario': 20, 'subtotal': 60}
            ],
            'taxa_entrega': 10
        }
        
        with patch('app.vendas.service.Venda') as MockVenda, \
             patch('app.vendas.service.VendaItem'), \
             patch('app.vendas.service.ContaReceber'), \
             patch('app.vendas.service.LancamentoManual'), \
             patch('app.vendas.service.CategoriaFinanceira'), \
             patch('app.vendas.service.log_action'):
            
            fake_venda_model.total = Decimal('200.00')
            MockVenda.return_value = fake_venda_model
            
            categoria_mock = MagicMock()
            categoria_mock.id = 1
            mock_db_session.query.return_value.filter.return_value.first.return_value = categoria_mock
            
            # ACT
            resultado = VendaService.criar_venda(
                payload=payload,
                user_id=1,
                db=mock_db_session
            )
            
            # ASSERT
            assert resultado is not None
            evento = mock_event_dispatcher.eventos_publicados[0]
            assert isinstance(evento, VendaCriada)
            assert evento.quantidade_itens == 3
    
    def test_criar_venda_com_taxa_entrega(
        self,
        mock_db_session,
        mock_event_dispatcher,
        fake_venda_model
    ):
        """
        CENÁRIO: Criar venda com taxa de entrega
        ESPERA: Taxa incluída no total e metadados do evento
        """
        # ARRANGE
        payload = {
            'cliente_id': 1,
            'itens': [
                {'produto_id': 10, 'quantidade': 1, 'preco_unitario': 100, 'subtotal': 100}
            ],
            'taxa_entrega': 15.50,
            'tem_entrega': True
        }
        
        with patch('app.vendas.service.Venda') as MockVenda, \
             patch('app.vendas.service.VendaItem'), \
             patch('app.vendas.service.ContaReceber'), \
             patch('app.vendas.service.LancamentoManual'), \
             patch('app.vendas.service.CategoriaFinanceira'), \
             patch('app.vendas.service.log_action'):
            
            fake_venda_model.taxa_entrega = Decimal('15.50')
            fake_venda_model.tem_entrega = True
            fake_venda_model.total = Decimal('115.50')
            MockVenda.return_value = fake_venda_model
            
            categoria_mock = MagicMock()
            categoria_mock.id = 1
            mock_db_session.query.return_value.filter.return_value.first.return_value = categoria_mock
            
            # ACT
            VendaService.criar_venda(
                payload=payload,
                user_id=1,
                db=mock_db_session
            )
            
            # ASSERT
            evento = mock_event_dispatcher.eventos_publicados[0]
            assert evento.tem_entrega is True
            assert evento.metadados['taxa_entrega'] == 15.50


# ============================================================
# TESTES: FINALIZAR VENDA
# ============================================================


class TestFinalizarVenda:
    """Testes para VendaService.finalizar_venda()"""
    
    def test_finalizar_venda_pagamento_completo_dinheiro(
        self,
        mock_db_session,
        mock_caixa_service,
        mock_estoque_service,
        mock_event_dispatcher,
        fake_venda_model,
        fake_pagamentos
    ):
        """
        CENÁRIO: Finalizar venda com pagamento completo em dinheiro
        ESPERA:
        - Status alterado para 'finalizada'
        - Estoque baixado
        - Caixa movimentado
        - Evento VendaFinalizada publicado
        """
        # ARRANGE
        with patch('app.vendas.service.Venda') as MockVenda, \
             patch('app.vendas.service.VendaPagamento') as MockPagamento, \
             patch('app.vendas.service.VendaItem') as MockItem, \
             patch('app.financeiro.ContasReceberService') as MockContasService:
            
            # Configurar venda existente
            fake_venda_model.status = 'aberta'
            mock_db_session.query.return_value.filter_by.return_value.first.return_value = fake_venda_model
            
            # Configurar itens da venda
            item_mock = MagicMock()
            item_mock.produto_id = 10
            item_mock.quantidade = 2
            mock_db_session.query.return_value.filter_by.return_value.all.return_value = [item_mock]
            
            # Configurar pagamentos existentes (nenhum)
            mock_db_session.query(MockPagamento).filter_by.return_value.all.return_value = []
            
            # ACT
            resultado = VendaService.finalizar_venda(
                venda_id=100,
                pagamentos=fake_pagamentos,
                user_id=1,
                user_nome='Usuário Teste',
                db=mock_db_session
            )
            
            # ASSERT
            assert fake_venda_model.status == 'finalizada'
            assert fake_venda_model.data_finalizacao is not None
            
            # Verificar baixa de estoque
            mock_estoque_service.baixar_estoque.assert_called()
            
            # Verificar movimentação de caixa
            mock_caixa_service.registrar_movimentacao_venda.assert_called_once()
            
            # Verificar commit
            mock_db_session.commit.assert_called()
            
            # Verificar evento
            assert len(mock_event_dispatcher.eventos_publicados) > 0
            evento = [e for e in mock_event_dispatcher.eventos_publicados if isinstance(e, VendaFinalizada)]
            assert len(evento) > 0
            assert evento[0].venda_id == 100
            assert evento[0].status == 'finalizada'
    
    def test_finalizar_venda_pagamento_parcial(
        self,
        mock_db_session,
        mock_caixa_service,
        mock_estoque_service,
        mock_event_dispatcher,
        fake_venda_model
    ):
        """
        CENÁRIO: Finalizar venda com pagamento parcial
        ESPERA: Status 'baixa_parcial' e lançamento previsto para saldo
        """
        # ARRANGE
        with patch('app.vendas.service.Venda'), \
             patch('app.vendas.service.VendaPagamento'), \
             patch('app.vendas.service.VendaItem'), \
             patch('app.vendas.service.LancamentoManual') as MockLancamento, \
             patch('app.vendas.service.CategoriaFinanceira'), \
             patch('app.financeiro.ContasReceberService'):
            
            fake_venda_model.status = 'aberta'
            fake_venda_model.total = Decimal('100.00')
            mock_db_session.query.return_value.filter_by.return_value.first.return_value = fake_venda_model
            
            item_mock = MagicMock()
            item_mock.produto_id = 10
            item_mock.quantidade = 1
            mock_db_session.query.return_value.filter_by.return_value.all.return_value = [item_mock]
            
            pagamentos = [{'forma_pagamento': 'Dinheiro', 'valor': 50.00, 'numero_parcelas': 1}]
            
            # ACT
            VendaService.finalizar_venda(
                venda_id=100,
                pagamentos=pagamentos,
                user_id=1,
                user_nome='Usuário Teste',
                db=mock_db_session
            )
            
            # ASSERT
            assert fake_venda_model.status == 'baixa_parcial'
            
            # Verificar que lançamento previsto foi criado para saldo
            assert MockLancamento.called


# ============================================================
# TESTES: CANCELAR VENDA
# ============================================================


class TestCancelarVenda:
    """Testes para VendaService.cancelar_venda()"""
    
    def test_cancelar_venda_aberta_sucesso(
        self,
        mock_db_session,
        mock_estoque_service,
        mock_event_dispatcher,
        fake_venda_model
    ):
        """
        CENÁRIO: Cancelar uma venda aberta
        ESPERA:
        - Status alterado para 'cancelada'
        - Estoque estornado
        - Evento VendaCancelada publicado
        """
        # ARRANGE
        with patch('app.vendas.service.Venda'), \
             patch('app.vendas.service.VendaItem') as MockItem, \
             patch('app.vendas.service.ContaReceber'), \
             patch('app.vendas.service.LancamentoManual'), \
             patch('app.vendas.service.MovimentacaoCaixa'), \
             patch('app.vendas.service.MovimentacaoFinanceira'), \
             patch('app.vendas.service.log_action'), \
             patch('app.comissoes_estorno.estornar_comissoes_venda') as mock_estorno:
            
            fake_venda_model.status = 'aberta'
            mock_db_session.query.return_value.filter_by.return_value.first.return_value = fake_venda_model
            
            # Configurar itens
            item_mock = MagicMock()
            item_mock.produto_id = 10
            item_mock.quantidade = 2
            mock_db_session.query(MockItem).filter_by.return_value.all.return_value = [item_mock]
            
            # Configurar estorno de comissões
            mock_estorno.return_value = {
                'success': True,
                'comissoes_estornadas': 1,
                'valor_estornado': 10.00
            }
            
            # ACT
            resultado = VendaService.cancelar_venda(
                venda_id=100,
                motivo='Cliente desistiu',
                user_id=1,
                db=mock_db_session
            )
            
            # ASSERT
            assert fake_venda_model.status == 'cancelada'
            assert fake_venda_model.motivo_cancelamento == 'Cliente desistiu'
            assert fake_venda_model.data_cancelamento is not None
            
            # Verificar estorno de estoque
            mock_estoque_service.estornar_estoque.assert_called()
            
            # Verificar commit
            mock_db_session.commit.assert_called()
            
            # Verificar evento
            eventos = [e for e in mock_event_dispatcher.eventos_publicados if isinstance(e, VendaCancelada)]
            assert len(eventos) > 0
            evento = eventos[0]
            assert evento.venda_id == 100
            assert evento.motivo == 'Cliente desistiu'
    
    def test_cancelar_venda_finalizada_estorna_tudo(
        self,
        mock_db_session,
        mock_estoque_service,
        mock_event_dispatcher,
        fake_venda_model
    ):
        """
        CENÁRIO: Cancelar venda já finalizada
        ESPERA: Estorno completo de estoque, contas, movimentações
        """
        # ARRANGE
        with patch('app.vendas.service.Venda'), \
             patch('app.vendas.service.VendaItem') as MockItem, \
             patch('app.vendas.service.ContaReceber') as MockConta, \
             patch('app.vendas.service.LancamentoManual') as MockLanc, \
             patch('app.vendas.service.MovimentacaoCaixa') as MockMovCaixa, \
             patch('app.vendas.service.MovimentacaoFinanceira'), \
             patch('app.vendas.service.log_action'), \
             patch('app.comissoes_estorno.estornar_comissoes_venda'):
            
            fake_venda_model.status = 'finalizada'
            mock_db_session.query.return_value.filter_by.return_value.first.return_value = fake_venda_model
            
            # Itens
            item_mock = MagicMock()
            item_mock.produto_id = 10
            item_mock.quantidade = 2
            
            # Conta receber
            conta_mock = MagicMock()
            conta_mock.status = 'recebido'
            
            # Lançamento
            lanc_mock = MagicMock()
            lanc_mock.status = 'realizado'
            
            # Movimentação caixa
            mov_caixa = MagicMock()
            
            # Configurar queries
            def side_effect_query(model):
                query_mock = MagicMock()
                if model == MockItem:
                    query_mock.filter_by.return_value.all.return_value = [item_mock]
                elif model == MockConta:
                    query_mock.filter_by.return_value.all.return_value = [conta_mock]
                elif model == MockLanc:
                    query_mock.filter.return_value.all.return_value = [lanc_mock]
                elif model == MockMovCaixa:
                    query_mock.filter_by.return_value.all.return_value = [mov_caixa]
                else:
                    query_mock.filter_by.return_value.all.return_value = []
                return query_mock
            
            mock_db_session.query.side_effect = side_effect_query
            
            # ACT
            resultado = VendaService.cancelar_venda(
                venda_id=100,
                motivo='Erro operacional',
                user_id=1,
                db=mock_db_session
            )
            
            # ASSERT
            assert resultado['estornos']['itens_estornados'] == 1
            assert resultado['estornos']['contas_canceladas'] == 1
            assert resultado['estornos']['lancamentos_cancelados'] == 1
            assert resultado['estornos']['movimentacoes_removidas'] == 1


# ============================================================
# TESTES: VALIDAÇÕES GERAIS
# ============================================================


class TestValidacoesGerais:
    """Testes de validações do VendaService"""
    
    def test_criar_venda_sem_itens_retorna_erro(
        self,
        mock_db_session,
        mock_event_dispatcher
    ):
        """
        CENÁRIO: Tentar criar venda sem itens
        ESPERA: HTTPException com código 400
        """
        from fastapi import HTTPException
        
        payload = {
            'cliente_id': 1,
            'itens': []
        }
        
        # ACT & ASSERT
        with pytest.raises(HTTPException) as exc_info:
            VendaService.criar_venda(
                payload=payload,
                user_id=1,
                db=mock_db_session
            )
        
        assert exc_info.value.status_code == 400
        assert 'pelo menos um item' in str(exc_info.value.detail).lower()
    
    def test_cancelar_venda_ja_cancelada_retorna_erro(
        self,
        mock_db_session,
        fake_venda_model
    ):
        """
        CENÁRIO: Tentar cancelar venda já cancelada
        ESPERA: HTTPException com código 400
        """
        from fastapi import HTTPException
        
        with patch('app.vendas.service.Venda'):
            fake_venda_model.status = 'cancelada'
            mock_db_session.query.return_value.filter_by.return_value.first.return_value = fake_venda_model
            
            # ACT & ASSERT
            with pytest.raises(HTTPException) as exc_info:
                VendaService.cancelar_venda(
                    venda_id=100,
                    motivo='Teste',
                    user_id=1,
                    db=mock_db_session
                )
            
            assert exc_info.value.status_code == 400
            assert 'já está cancelada' in str(exc_info.value.detail).lower()
