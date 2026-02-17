"""
Testes de Domínio - Regras de Negócio de Vendas
================================================

Testes focados em validar as REGRAS DE NEGÓCIO do domínio de vendas.
Casos de erro, validações e restrições.
"""

import pytest
from unittest.mock import MagicMock, patch
from decimal import Decimal
from datetime import datetime

from app.vendas.service import VendaService
from fastapi import HTTPException


# ============================================================
# TESTES: REGRAS DE CRIAÇÃO DE VENDA
# ============================================================


class TestRegrasCriacaoVenda:
    """Testes de regras de negócio na criação de vendas"""
    
    def test_nao_criar_venda_sem_itens(self, mock_db_session):
        """
        REGRA: Venda DEVE ter pelo menos 1 item
        ESPERA: HTTPException 400
        """
        payload = {
            'cliente_id': 1,
            'itens': []
        }
        
        with pytest.raises(HTTPException) as exc:
            VendaService.criar_venda(
                payload=payload,
                user_id=1,
                db=mock_db_session
            )
        
        assert exc.value.status_code == 400
        assert 'pelo menos um item' in exc.value.detail.lower()
    
    def test_nao_criar_venda_com_itens_none(self, mock_db_session):
        """
        REGRA: Venda DEVE ter itens válidos
        ESPERA: HTTPException 400
        """
        payload = {
            'cliente_id': 1,
            'itens': None
        }
        
        with pytest.raises(HTTPException) as exc:
            VendaService.criar_venda(
                payload=payload,
                user_id=1,
                db=mock_db_session
            )
        
        assert exc.value.status_code == 400
    
    def test_rollback_em_caso_de_erro_criacao(self, mock_db_session):
        """
        REGRA: Se houver erro, fazer rollback completo
        ESPERA: Rollback chamado
        """
        payload = {
            'cliente_id': 1,
            'itens': [
                {'produto_id': 10, 'quantidade': 1, 'preco_unitario': 100, 'subtotal': 100}
            ]
        }
        
        with patch('app.vendas.service.Venda') as MockVenda:
            # Forçar erro ao criar venda
            MockVenda.side_effect = Exception('Erro simulado')
            
            with pytest.raises(HTTPException):
                VendaService.criar_venda(
                    payload=payload,
                    user_id=1,
                    db=mock_db_session
                )
            
            # Verificar rollback
            mock_db_session.rollback.assert_called()


# ============================================================
# TESTES: REGRAS DE FINALIZAÇÃO DE VENDA
# ============================================================


class TestRegrasFinalizacaoVenda:
    """Testes de regras de negócio na finalização de vendas"""
    
    def test_nao_finalizar_venda_sem_caixa_aberto(
        self,
        mock_db_session,
        mock_caixa_service,
        fake_venda_model
    ):
        """
        REGRA: Só pode finalizar venda se houver caixa aberto
        ESPERA: HTTPException quando caixa validação falha
        """
        with patch('app.vendas.service.Venda'):
            # Configurar caixa service para lançar erro
            mock_caixa_service.validar_caixa_aberto.side_effect = HTTPException(
                status_code=400,
                detail='Nenhum caixa aberto'
            )
            
            mock_db_session.query.return_value.filter_by.return_value.first.return_value = fake_venda_model
            
            pagamentos = [{'forma_pagamento': 'Dinheiro', 'valor': 100.00}]
            
            with pytest.raises(HTTPException) as exc:
                VendaService.finalizar_venda(
                    venda_id=100,
                    pagamentos=pagamentos,
                    user_id=1,
                    user_nome='Teste',
                    db=mock_db_session
                )
            
            assert 'caixa' in exc.value.detail.lower()
    
    def test_nao_finalizar_venda_inexistente(
        self,
        mock_db_session,
        mock_caixa_service
    ):
        """
        REGRA: Venda deve existir para ser finalizada
        ESPERA: HTTPException 404
        """
        with patch('app.vendas.service.Venda'):
            # Venda não encontrada
            mock_db_session.query.return_value.filter_by.return_value.first.return_value = None
            
            pagamentos = [{'forma_pagamento': 'Dinheiro', 'valor': 100.00}]
            
            with pytest.raises(HTTPException) as exc:
                VendaService.finalizar_venda(
                    venda_id=999,
                    pagamentos=pagamentos,
                    user_id=1,
                    user_nome='Teste',
                    db=mock_db_session
                )
            
            assert exc.value.status_code == 404
    
    def test_nao_finalizar_venda_ja_finalizada(
        self,
        mock_db_session,
        mock_caixa_service,
        fake_venda_model
    ):
        """
        REGRA: Não pode finalizar venda que já está finalizada
        ESPERA: HTTPException 400
        """
        with patch('app.vendas.service.Venda'):
            fake_venda_model.status = 'finalizada'
            mock_db_session.query.return_value.filter_by.return_value.first.return_value = fake_venda_model
            
            pagamentos = [{'forma_pagamento': 'Dinheiro', 'valor': 100.00}]
            
            with pytest.raises(HTTPException) as exc:
                VendaService.finalizar_venda(
                    venda_id=100,
                    pagamentos=pagamentos,
                    user_id=1,
                    user_nome='Teste',
                    db=mock_db_session
                )
            
            assert exc.value.status_code == 400
            assert 'status' in exc.value.detail.lower()
    
    def test_nao_finalizar_venda_cancelada(
        self,
        mock_db_session,
        mock_caixa_service,
        fake_venda_model
    ):
        """
        REGRA: Não pode finalizar venda cancelada
        ESPERA: HTTPException 400
        """
        with patch('app.vendas.service.Venda'):
            fake_venda_model.status = 'cancelada'
            mock_db_session.query.return_value.filter_by.return_value.first.return_value = fake_venda_model
            
            pagamentos = [{'forma_pagamento': 'Dinheiro', 'valor': 100.00}]
            
            with pytest.raises(HTTPException) as exc:
                VendaService.finalizar_venda(
                    venda_id=100,
                    pagamentos=pagamentos,
                    user_id=1,
                    user_nome='Teste',
                    db=mock_db_session
                )
            
            assert exc.value.status_code == 400
    
    def test_nao_finalizar_venda_sem_pagamentos(
        self,
        mock_db_session,
        mock_caixa_service,
        fake_venda_model
    ):
        """
        REGRA: Deve informar pelo menos 1 forma de pagamento
        ESPERA: HTTPException 400
        """
        with patch('app.vendas.service.Venda'):
            fake_venda_model.status = 'aberta'
            mock_db_session.query.return_value.filter_by.return_value.first.return_value = fake_venda_model
            
            with pytest.raises(HTTPException) as exc:
                VendaService.finalizar_venda(
                    venda_id=100,
                    pagamentos=[],
                    user_id=1,
                    user_nome='Teste',
                    db=mock_db_session
                )
            
            assert exc.value.status_code == 400
            assert 'pagamento' in exc.value.detail.lower()
    
    def test_nao_finalizar_venda_ja_totalmente_paga(
        self,
        mock_db_session,
        mock_caixa_service,
        fake_venda_model
    ):
        """
        REGRA: Não pode pagar venda já totalmente paga
        ESPERA: HTTPException 400
        """
        with patch('app.vendas.service.Venda'), \
             patch('app.vendas.service.VendaPagamento') as MockPagamento:
            
            fake_venda_model.status = 'aberta'
            fake_venda_model.total = Decimal('100.00')
            mock_db_session.query.return_value.filter_by.return_value.first.return_value = fake_venda_model
            
            # Pagamento existente de 100
            pag_existente = MagicMock()
            pag_existente.valor = Decimal('100.00')
            mock_db_session.query(MockPagamento).filter_by.return_value.all.return_value = [pag_existente]
            
            novos_pagamentos = [{'forma_pagamento': 'Dinheiro', 'valor': 50.00}]
            
            with pytest.raises(HTTPException) as exc:
                VendaService.finalizar_venda(
                    venda_id=100,
                    pagamentos=novos_pagamentos,
                    user_id=1,
                    user_nome='Teste',
                    db=mock_db_session
                )
            
            assert exc.value.status_code == 400
            assert 'já está totalmente paga' in exc.value.detail.lower()
    
    def test_credito_cliente_requer_cliente_vinculado(
        self,
        mock_db_session,
        mock_caixa_service,
        fake_venda_model
    ):
        """
        REGRA: Crédito de cliente só pode ser usado se houver cliente vinculado
        ESPERA: HTTPException 400
        """
        with patch('app.vendas.service.Venda'), \
             patch('app.vendas.service.VendaPagamento'), \
             patch('app.vendas.service.VendaItem'):
            
            fake_venda_model.status = 'aberta'
            fake_venda_model.cliente_id = None  # SEM CLIENTE
            fake_venda_model.total = Decimal('100.00')
            mock_db_session.query.return_value.filter_by.return_value.first.return_value = fake_venda_model
            
            item_mock = MagicMock()
            item_mock.produto_id = 10
            mock_db_session.query.return_value.filter_by.return_value.all.return_value = [item_mock]
            
            pagamentos = [{'forma_pagamento': 'Crédito Cliente', 'valor': 100.00}]
            
            with pytest.raises(HTTPException) as exc:
                VendaService.finalizar_venda(
                    venda_id=100,
                    pagamentos=pagamentos,
                    user_id=1,
                    user_nome='Teste',
                    db=mock_db_session
                )
            
            assert exc.value.status_code == 400
            assert 'cliente vinculado' in exc.value.detail.lower()
    
    def test_credito_insuficiente_impede_pagamento(
        self,
        mock_db_session,
        mock_caixa_service,
        fake_venda_model,
        fake_cliente_model
    ):
        """
        REGRA: Cliente deve ter crédito suficiente
        ESPERA: HTTPException 400
        """
        with patch('app.vendas.service.Venda'), \
             patch('app.vendas.service.VendaPagamento'), \
             patch('app.vendas.service.VendaItem'), \
             patch('app.vendas.service.Cliente') as MockCliente:
            
            fake_venda_model.status = 'aberta'
            fake_venda_model.cliente_id = 1
            fake_venda_model.total = Decimal('100.00')
            
            fake_cliente_model.credito = Decimal('30.00')  # Insuficiente
            
            # Mock de query para retornar venda e cliente
            def side_effect_query(model):
                query_mock = MagicMock()
                if model.__name__ == 'Venda':
                    query_mock.filter_by.return_value.first.return_value = fake_venda_model
                elif model.__name__ == 'Cliente':
                    query_mock.filter_by.return_value.first.return_value = fake_cliente_model
                else:
                    query_mock.filter_by.return_value.all.return_value = []
                    query_mock.filter_by.return_value.first.return_value = None
                return query_mock
            
            mock_db_session.query.side_effect = side_effect_query
            
            item_mock = MagicMock()
            item_mock.produto_id = 10
            
            pagamentos = [{'forma_pagamento': 'Crédito Cliente', 'valor': 100.00}]
            
            with pytest.raises(HTTPException) as exc:
                VendaService.finalizar_venda(
                    venda_id=100,
                    pagamentos=pagamentos,
                    user_id=1,
                    user_nome='Teste',
                    db=mock_db_session
                )
            
            assert exc.value.status_code == 400
            assert 'insuficiente' in exc.value.detail.lower()


# ============================================================
# TESTES: REGRAS DE CANCELAMENTO DE VENDA
# ============================================================


class TestRegrasCancelamentoVenda:
    """Testes de regras de negócio no cancelamento de vendas"""
    
    def test_nao_cancelar_venda_inexistente(self, mock_db_session):
        """
        REGRA: Venda deve existir para ser cancelada
        ESPERA: HTTPException 404
        """
        with patch('app.vendas.service.Venda'):
            mock_db_session.query.return_value.filter_by.return_value.first.return_value = None
            
            with pytest.raises(HTTPException) as exc:
                VendaService.cancelar_venda(
                    venda_id=999,
                    motivo='Teste',
                    user_id=1,
                    db=mock_db_session
                )
            
            assert exc.value.status_code == 404
    
    def test_nao_cancelar_venda_ja_cancelada(
        self,
        mock_db_session,
        fake_venda_model
    ):
        """
        REGRA: Não pode cancelar venda já cancelada (idempotência)
        ESPERA: HTTPException 400
        """
        with patch('app.vendas.service.Venda'):
            fake_venda_model.status = 'cancelada'
            mock_db_session.query.return_value.filter_by.return_value.first.return_value = fake_venda_model
            
            with pytest.raises(HTTPException) as exc:
                VendaService.cancelar_venda(
                    venda_id=100,
                    motivo='Teste',
                    user_id=1,
                    db=mock_db_session
                )
            
            assert exc.value.status_code == 400
            assert 'já está cancelada' in exc.value.detail.lower()
    
    def test_cancelamento_falha_rollback_completo(
        self,
        mock_db_session,
        mock_estoque_service,
        fake_venda_model
    ):
        """
        REGRA: Se cancelamento falhar, fazer rollback completo
        ESPERA: Rollback chamado em caso de erro
        """
        with patch('app.vendas.service.Venda'), \
             patch('app.vendas.service.VendaItem'), \
             patch('app.vendas.service.log_action'):
            
            fake_venda_model.status = 'aberta'
            mock_db_session.query.return_value.filter_by.return_value.first.return_value = fake_venda_model
            
            item_mock = MagicMock()
            item_mock.produto_id = 10
            mock_db_session.query.return_value.filter_by.return_value.all.return_value = [item_mock]
            
            # Forçar erro no estorno de estoque
            mock_estoque_service.estornar_estoque.side_effect = Exception('Erro no estoque')
            
            with pytest.raises(HTTPException):
                VendaService.cancelar_venda(
                    venda_id=100,
                    motivo='Teste',
                    user_id=1,
                    db=mock_db_session
                )
            
            # Verificar rollback
            mock_db_session.rollback.assert_called()


# ============================================================
# TESTES: SEGURANÇA E ISOLAMENTO DE USUÁRIO
# ============================================================


class TestSegurancaIsolamentoUsuario:
    """Testes de segurança e isolamento entre usuários"""
    
    def test_nao_finalizar_venda_de_outro_usuario(
        self,
        mock_db_session,
        mock_caixa_service,
        fake_venda_model
    ):
        """
        REGRA: Usuário só pode finalizar suas próprias vendas
        ESPERA: HTTPException 404 (venda não encontrada)
        """
        with patch('app.vendas.service.Venda'):
            fake_venda_model.user_id = 1
            
            # Buscar com user_id diferente retorna None
            def side_effect_query(*args, **kwargs):
                query_mock = MagicMock()
                if kwargs.get('user_id') == 2:
                    query_mock.first.return_value = None
                else:
                    query_mock.first.return_value = fake_venda_model
                return query_mock
            
            mock_db_session.query.return_value.filter_by.side_effect = side_effect_query
            
            pagamentos = [{'forma_pagamento': 'Dinheiro', 'valor': 100.00}]
            
            with pytest.raises(HTTPException) as exc:
                VendaService.finalizar_venda(
                    venda_id=100,
                    pagamentos=pagamentos,
                    user_id=2,  # Usuário diferente
                    user_nome='Outro',
                    db=mock_db_session
                )
            
            assert exc.value.status_code == 404
    
    def test_nao_cancelar_venda_de_outro_usuario(
        self,
        mock_db_session,
        fake_venda_model
    ):
        """
        REGRA: Usuário só pode cancelar suas próprias vendas
        ESPERA: HTTPException 404
        """
        with patch('app.vendas.service.Venda'):
            fake_venda_model.user_id = 1
            
            # Buscar com user_id diferente retorna None
            mock_db_session.query.return_value.filter_by.return_value.first.return_value = None
            
            with pytest.raises(HTTPException) as exc:
                VendaService.cancelar_venda(
                    venda_id=100,
                    motivo='Teste',
                    user_id=2,  # Usuário diferente
                    db=mock_db_session
                )
            
            assert exc.value.status_code == 404
