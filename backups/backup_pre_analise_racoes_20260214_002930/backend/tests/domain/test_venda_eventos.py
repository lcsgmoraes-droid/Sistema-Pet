"""
Testes de Domínio - Eventos de Vendas
======================================

Testes focados em validar a emissão e processamento de eventos de domínio.
"""

import pytest
from unittest.mock import MagicMock, patch, call
from decimal import Decimal
from datetime import datetime

from app.vendas.service import VendaService
from app.domain.events import VendaCriada, VendaFinalizada, VendaCancelada


# ============================================================
# TESTES: EMISSÃO DE EVENTOS - VendaCriada
# ============================================================


class TestEventoVendaCriada:
    """Testes de emissão do evento VendaCriada"""
    
    def test_evento_venda_criada_eh_emitido(
        self,
        mock_db_session,
        mock_event_dispatcher,
        fake_venda_data,
        fake_venda_model
    ):
        """
        CENÁRIO: Criar uma venda
        ESPERA: Evento VendaCriada emitido com dados corretos
        """
        # ARRANGE
        with patch('app.vendas.service.Venda') as MockVenda, \
             patch('app.vendas.service.VendaItem'), \
             patch('app.vendas.service.ContaReceber'), \
             patch('app.vendas.service.LancamentoManual'), \
             patch('app.vendas.service.CategoriaFinanceira'), \
             patch('app.vendas.service.log_action'):
            
            MockVenda.return_value = fake_venda_model
            
            categoria_mock = MagicMock()
            categoria_mock.id = 1
            mock_db_session.query.return_value.filter.return_value.first.return_value = categoria_mock
            
            # ACT
            VendaService.criar_venda(
                payload=fake_venda_data,
                user_id=1,
                db=mock_db_session
            )
            
            # ASSERT
            eventos = mock_event_dispatcher.eventos_publicados
            assert len(eventos) == 1
            
            evento = eventos[0]
            assert isinstance(evento, VendaCriada)
            assert evento.venda_id == 100
            assert evento.numero_venda == '202601230001'
            assert evento.user_id == 1
            assert evento.total == 100.0
            assert evento.quantidade_itens == 1
    
    def test_evento_venda_criada_inclui_metadados(
        self,
        mock_db_session,
        mock_event_dispatcher,
        fake_venda_model
    ):
        """
        CENÁRIO: Criar venda com taxa de entrega
        ESPERA: Evento inclui metadados com taxa e subtotal
        """
        # ARRANGE
        payload = {
            'cliente_id': 1,
            'itens': [
                {'produto_id': 10, 'quantidade': 2, 'preco_unitario': 50, 'subtotal': 100}
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
            assert evento.metadados is not None
            assert evento.metadados['taxa_entrega'] == 15.50
            assert evento.metadados['subtotal'] == 100.0
    
    def test_evento_venda_criada_emitido_apos_commit(
        self,
        mock_db_session,
        mock_event_dispatcher,
        fake_venda_data,
        fake_venda_model
    ):
        """
        CENÁRIO: Criar venda
        ESPERA: Evento emitido APÓS commit (não antes)
        """
        # ARRANGE
        with patch('app.vendas.service.Venda') as MockVenda, \
             patch('app.vendas.service.VendaItem'), \
             patch('app.vendas.service.ContaReceber'), \
             patch('app.vendas.service.LancamentoManual'), \
             patch('app.vendas.service.CategoriaFinanceira'), \
             patch('app.vendas.service.log_action'):
            
            MockVenda.return_value = fake_venda_model
            
            categoria_mock = MagicMock()
            categoria_mock.id = 1
            mock_db_session.query.return_value.filter.return_value.first.return_value = categoria_mock
            
            # Rastrear ordem de chamadas
            call_order = []
            
            def track_commit():
                call_order.append('commit')
            
            def track_publish(event):
                call_order.append('publish')
                mock_event_dispatcher.eventos_publicados.append(event)
            
            mock_db_session.commit.side_effect = track_commit
            
            with patch('app.domain.events.publish_event', side_effect=track_publish):
                # ACT
                VendaService.criar_venda(
                    payload=fake_venda_data,
                    user_id=1,
                    db=mock_db_session
                )
            
            # ASSERT
            assert call_order == ['commit', 'publish']
    
    def test_erro_em_evento_nao_aborta_criacao_venda(
        self,
        mock_db_session,
        fake_venda_data,
        fake_venda_model
    ):
        """
        CENÁRIO: Erro ao publicar evento VendaCriada
        ESPERA: Venda criada com sucesso mesmo assim
        """
        # ARRANGE
        with patch('app.vendas.service.Venda') as MockVenda, \
             patch('app.vendas.service.VendaItem'), \
             patch('app.vendas.service.ContaReceber'), \
             patch('app.vendas.service.LancamentoManual'), \
             patch('app.vendas.service.CategoriaFinanceira'), \
             patch('app.vendas.service.log_action'), \
             patch('app.domain.events.publish_event') as mock_publish:
            
            MockVenda.return_value = fake_venda_model
            
            categoria_mock = MagicMock()
            categoria_mock.id = 1
            mock_db_session.query.return_value.filter.return_value.first.return_value = categoria_mock
            
            # Forçar erro ao publicar evento
            mock_publish.side_effect = Exception('Erro no dispatcher')
            
            # ACT
            resultado = VendaService.criar_venda(
                payload=fake_venda_data,
                user_id=1,
                db=mock_db_session
            )
            
            # ASSERT
            assert resultado is not None
            assert resultado['id'] == 100
            mock_db_session.rollback.assert_not_called()


# ============================================================
# TESTES: EMISSÃO DE EVENTOS - VendaFinalizada
# ============================================================


class TestEventoVendaFinalizada:
    """Testes de emissão do evento VendaFinalizada"""
    
    def test_evento_venda_finalizada_eh_emitido(
        self,
        mock_db_session,
        mock_caixa_service,
        mock_estoque_service,
        mock_event_dispatcher,
        fake_venda_model,
        fake_pagamentos
    ):
        """
        CENÁRIO: Finalizar uma venda
        ESPERA: Evento VendaFinalizada emitido
        """
        # ARRANGE
        with patch('app.vendas.service.Venda'), \
             patch('app.vendas.service.VendaPagamento'), \
             patch('app.vendas.service.VendaItem') as MockItem, \
             patch('app.financeiro.ContasReceberService'):
            
            fake_venda_model.status = 'aberta'
            mock_db_session.query.return_value.filter_by.return_value.first.return_value = fake_venda_model
            
            item_mock = MagicMock()
            item_mock.produto_id = 10
            item_mock.quantidade = 2
            mock_db_session.query(MockItem).filter_by.return_value.all.return_value = [item_mock]
            
            # Simular publish_event
            eventos_publicados = []
            
            def track_publish(event):
                eventos_publicados.append(event)
            
            with patch('app.domain.events.publish_event', side_effect=track_publish):
                # ACT
                VendaService.finalizar_venda(
                    venda_id=100,
                    pagamentos=fake_pagamentos,
                    user_id=1,
                    user_nome='Usuário Teste',
                    db=mock_db_session
                )
            
            # ASSERT
            eventos_finalizadas = [e for e in eventos_publicados if isinstance(e, VendaFinalizada)]
            assert len(eventos_finalizadas) > 0
            
            evento = eventos_finalizadas[0]
            assert evento.venda_id == 100
            assert evento.status == 'finalizada'
            assert evento.user_id == 1
    
    def test_evento_venda_finalizada_inclui_formas_pagamento(
        self,
        mock_db_session,
        mock_caixa_service,
        mock_estoque_service,
        fake_venda_model
    ):
        """
        CENÁRIO: Finalizar venda com múltiplas formas de pagamento
        ESPERA: Evento inclui lista de formas de pagamento
        """
        # ARRANGE
        pagamentos = [
            {'forma_pagamento': 'Dinheiro', 'valor': 50.00, 'numero_parcelas': 1},
            {'forma_pagamento': 'PIX', 'valor': 30.00, 'numero_parcelas': 1},
            {'forma_pagamento': 'Cartão Débito', 'valor': 20.00, 'numero_parcelas': 1}
        ]
        
        with patch('app.vendas.service.Venda'), \
             patch('app.vendas.service.VendaPagamento'), \
             patch('app.vendas.service.VendaItem'), \
             patch('app.financeiro.ContasReceberService'):
            
            fake_venda_model.status = 'aberta'
            mock_db_session.query.return_value.filter_by.return_value.first.return_value = fake_venda_model
            
            item_mock = MagicMock()
            item_mock.produto_id = 10
            mock_db_session.query.return_value.filter_by.return_value.all.return_value = [item_mock]
            
            eventos_publicados = []
            
            with patch('app.domain.events.publish_event', side_effect=lambda e: eventos_publicados.append(e)):
                # ACT
                VendaService.finalizar_venda(
                    venda_id=100,
                    pagamentos=pagamentos,
                    user_id=1,
                    user_nome='Teste',
                    db=mock_db_session
                )
            
            # ASSERT
            evento = [e for e in eventos_publicados if isinstance(e, VendaFinalizada)][0]
            assert len(evento.formas_pagamento) == 3
            assert 'Dinheiro' in evento.formas_pagamento
            assert 'PIX' in evento.formas_pagamento


# ============================================================
# TESTES: EMISSÃO DE EVENTOS - VendaCancelada
# ============================================================


class TestEventoVendaCancelada:
    """Testes de emissão do evento VendaCancelada"""
    
    def test_evento_venda_cancelada_eh_emitido(
        self,
        mock_db_session,
        mock_estoque_service,
        fake_venda_model
    ):
        """
        CENÁRIO: Cancelar uma venda
        ESPERA: Evento VendaCancelada emitido
        """
        # ARRANGE
        with patch('app.vendas.service.Venda'), \
             patch('app.vendas.service.VendaItem'), \
             patch('app.vendas.service.ContaReceber'), \
             patch('app.vendas.service.LancamentoManual'), \
             patch('app.vendas.service.MovimentacaoCaixa'), \
             patch('app.vendas.service.MovimentacaoFinanceira'), \
             patch('app.vendas.service.log_action'), \
             patch('app.comissoes_estorno.estornar_comissoes_venda'):
            
            fake_venda_model.status = 'aberta'
            mock_db_session.query.return_value.filter_by.return_value.first.return_value = fake_venda_model
            
            item_mock = MagicMock()
            item_mock.produto_id = 10
            item_mock.quantidade = 2
            mock_db_session.query.return_value.filter_by.return_value.all.return_value = [item_mock]
            
            eventos_publicados = []
            
            with patch('app.domain.events.publish_event', side_effect=lambda e: eventos_publicados.append(e)):
                # ACT
                VendaService.cancelar_venda(
                    venda_id=100,
                    motivo='Cliente desistiu',
                    user_id=1,
                    db=mock_db_session
                )
            
            # ASSERT
            eventos_canceladas = [e for e in eventos_publicados if isinstance(e, VendaCancelada)]
            assert len(eventos_canceladas) > 0
            
            evento = eventos_canceladas[0]
            assert evento.venda_id == 100
            assert evento.motivo == 'Cliente desistiu'
            assert evento.user_id == 1
    
    def test_evento_venda_cancelada_inclui_metadados_estornos(
        self,
        mock_db_session,
        mock_estoque_service,
        fake_venda_model
    ):
        """
        CENÁRIO: Cancelar venda com vários estornos
        ESPERA: Evento inclui metadados com contagem de estornos
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
            
            # 2 itens
            item_mock1 = MagicMock()
            item_mock1.produto_id = 10
            item_mock2 = MagicMock()
            item_mock2.produto_id = 20
            
            # 1 conta
            conta_mock = MagicMock()
            conta_mock.status = 'pendente'
            
            # 1 lançamento
            lanc_mock = MagicMock()
            lanc_mock.status = 'previsto'
            
            # 1 movimentação caixa
            mov_caixa = MagicMock()
            
            def side_effect_query(model):
                query_mock = MagicMock()
                if model == MockItem:
                    query_mock.filter_by.return_value.all.return_value = [item_mock1, item_mock2]
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
            
            eventos_publicados = []
            
            with patch('app.domain.events.publish_event', side_effect=lambda e: eventos_publicados.append(e)):
                # ACT
                VendaService.cancelar_venda(
                    venda_id=100,
                    motivo='Erro operacional',
                    user_id=1,
                    db=mock_db_session
                )
            
            # ASSERT
            evento = [e for e in eventos_publicados if isinstance(e, VendaCancelada)][0]
            assert evento.itens_estornados == 2
            assert evento.contas_canceladas == 1
            assert evento.metadados is not None
            assert evento.metadados['lancamentos_cancelados'] == 1
            assert evento.metadados['movimentacoes_caixa_removidas'] == 1
    
    def test_erro_em_evento_cancelamento_nao_aborta_cancelamento(
        self,
        mock_db_session,
        mock_estoque_service,
        fake_venda_model
    ):
        """
        CENÁRIO: Erro ao publicar evento VendaCancelada
        ESPERA: Cancelamento completo mesmo assim
        """
        # ARRANGE
        with patch('app.vendas.service.Venda'), \
             patch('app.vendas.service.VendaItem'), \
             patch('app.vendas.service.ContaReceber'), \
             patch('app.vendas.service.LancamentoManual'), \
             patch('app.vendas.service.MovimentacaoCaixa'), \
             patch('app.vendas.service.MovimentacaoFinanceira'), \
             patch('app.vendas.service.log_action'), \
             patch('app.comissoes_estorno.estornar_comissoes_venda'), \
             patch('app.domain.events.publish_event') as mock_publish:
            
            fake_venda_model.status = 'aberta'
            mock_db_session.query.return_value.filter_by.return_value.first.return_value = fake_venda_model
            
            item_mock = MagicMock()
            item_mock.produto_id = 10
            mock_db_session.query.return_value.filter_by.return_value.all.return_value = [item_mock]
            
            # Forçar erro ao publicar evento
            mock_publish.side_effect = Exception('Erro no dispatcher')
            
            # ACT
            resultado = VendaService.cancelar_venda(
                venda_id=100,
                motivo='Teste',
                user_id=1,
                db=mock_db_session
            )
            
            # ASSERT
            assert resultado is not None
            assert fake_venda_model.status == 'cancelada'
            mock_db_session.rollback.assert_not_called()


# ============================================================
# TESTES: HANDLERS DE EVENTOS (Simulação)
# ============================================================


class TestHandlersEventos:
    """Testes de handlers de eventos (simulação)"""
    
    def test_handler_pode_ser_registrado_e_chamado(self):
        """
        CENÁRIO: Registrar handler para VendaCriada
        ESPERA: Handler é chamado quando evento é publicado
        """
        from app.domain.events.dispatcher import EventDispatcher
        
        # ARRANGE
        dispatcher = EventDispatcher()
        
        handler_chamado = []
        
        def meu_handler(evento: VendaCriada):
            handler_chamado.append(evento)
        
        dispatcher.subscribe(VendaCriada, meu_handler)
        
        # ACT
        evento = VendaCriada(
            venda_id=100,
            numero_venda='202601230001',
            user_id=1,
            cliente_id=None,
            funcionario_id=None,
            total=100.0,
            quantidade_itens=1,
            tem_entrega=False
        )
        
        dispatcher.publish(evento)
        
        # ASSERT
        assert len(handler_chamado) == 1
        assert handler_chamado[0] == evento
    
    def test_erro_em_handler_nao_impede_outros_handlers(self):
        """
        CENÁRIO: Handler com erro não impede outros handlers
        ESPERA: Todos os handlers executam independentemente
        """
        from app.domain.events.dispatcher import EventDispatcher
        
        # ARRANGE
        dispatcher = EventDispatcher()
        
        handlers_executados = []
        
        def handler_com_erro(evento):
            handlers_executados.append('handler1')
            raise Exception('Erro proposital')
        
        def handler_normal(evento):
            handlers_executados.append('handler2')
        
        dispatcher.subscribe(VendaCriada, handler_com_erro)
        dispatcher.subscribe(VendaCriada, handler_normal)
        
        # ACT
        evento = VendaCriada(
            venda_id=100,
            numero_venda='202601230001',
            user_id=1,
            cliente_id=None,
            funcionario_id=None,
            total=100.0,
            quantidade_itens=1,
            tem_entrega=False
        )
        
        dispatcher.publish(evento)
        
        # ASSERT
        assert 'handler1' in handlers_executados
        assert 'handler2' in handlers_executados
    
    def test_multiplos_handlers_sao_executados_em_ordem(self):
        """
        CENÁRIO: Registrar múltiplos handlers
        ESPERA: Todos executados em ordem de registro
        """
        from app.domain.events.dispatcher import EventDispatcher
        
        # ARRANGE
        dispatcher = EventDispatcher()
        
        ordem = []
        
        def handler1(evento):
            ordem.append(1)
        
        def handler2(evento):
            ordem.append(2)
        
        def handler3(evento):
            ordem.append(3)
        
        dispatcher.subscribe(VendaCriada, handler1)
        dispatcher.subscribe(VendaCriada, handler2)
        dispatcher.subscribe(VendaCriada, handler3)
        
        # ACT
        evento = VendaCriada(
            venda_id=100,
            numero_venda='202601230001',
            user_id=1,
            cliente_id=None,
            funcionario_id=None,
            total=100.0,
            quantidade_itens=1,
            tem_entrega=False
        )
        
        dispatcher.publish(evento)
        
        # ASSERT
        assert ordem == [1, 2, 3]
