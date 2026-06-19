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
from unittest.mock import MagicMock, patch
from decimal import Decimal

from app.vendas.service import VendaService
from app.domain.events import VendaCriada, VendaFinalizada, VendaCancelada


# ============================================================
# TESTES: CRIAR VENDA
# ============================================================


class TestCriarVenda:
    """Testes para VendaService.criar_venda()"""

    def test_criar_venda_simples_sucesso(
        self, mock_db_session, mock_event_dispatcher, fake_venda_data, fake_venda_model
    ):
        """
        CENÁRIO: Criar uma venda simples com 1 item
        ESPERA:
        - Venda criada com sucesso
        - Evento VendaCriada publicado
        - Commit executado
        """
        # ARRANGE
        with (
            patch("app.vendas_models.Venda") as MockVenda,
            patch("app.vendas_models.VendaItem"),
            patch("app.financeiro_models.ContaReceber"),
            patch("app.financeiro_models.LancamentoManual"),
            patch("app.financeiro_models.CategoriaFinanceira"),
            patch("app.audit_log.log_action"),
        ):
            # Configurar mock de Venda
            MockVenda.return_value = fake_venda_model

            # Configurar categoria financeira existente
            categoria_mock = MagicMock()
            categoria_mock.id = 1
            categoria_mock.nome = "Receitas de Vendas"
            mock_db_session.query.return_value.filter.return_value.first.return_value = categoria_mock

            # ACT
            resultado = VendaService.criar_venda(
                payload=fake_venda_data, user_id=1, db=mock_db_session
            )

            # ASSERT
            assert resultado is not None
            assert resultado["id"] == 100
            assert resultado["numero_venda"] == "202601230001"
            assert resultado["status"] == "aberta"

            # Verificar que commit foi chamado
            mock_db_session.commit.assert_called_once()

            # Verificar que evento foi publicado
            assert len(mock_event_dispatcher.eventos_publicados) == 1
            evento = mock_event_dispatcher.eventos_publicados[0]
            assert isinstance(evento, VendaCriada)
            assert evento.venda_id == 100
            assert evento.numero_venda == "202601230001"
            assert evento.total == 100.0
            assert evento.quantidade_itens == 1

    def test_criar_venda_com_multiplos_itens(
        self, mock_db_session, mock_event_dispatcher, fake_venda_model
    ):
        """
        CENÁRIO: Criar venda com múltiplos itens
        ESPERA: Todos os itens criados e total calculado corretamente
        """
        # ARRANGE
        payload = {
            "cliente_id": 1,
            "itens": [
                {
                    "produto_id": 10,
                    "quantidade": 2,
                    "preco_unitario": 50,
                    "subtotal": 100,
                },
                {
                    "produto_id": 20,
                    "quantidade": 1,
                    "preco_unitario": 30,
                    "subtotal": 30,
                },
                {
                    "produto_id": 30,
                    "quantidade": 3,
                    "preco_unitario": 20,
                    "subtotal": 60,
                },
            ],
            "taxa_entrega": 10,
        }

        with (
            patch("app.vendas_models.Venda") as MockVenda,
            patch("app.vendas_models.VendaItem"),
            patch("app.financeiro_models.ContaReceber"),
            patch("app.financeiro_models.LancamentoManual"),
            patch("app.financeiro_models.CategoriaFinanceira"),
            patch("app.audit_log.log_action"),
        ):
            fake_venda_model.total = Decimal("200.00")
            MockVenda.return_value = fake_venda_model

            categoria_mock = MagicMock()
            categoria_mock.id = 1
            mock_db_session.query.return_value.filter.return_value.first.return_value = categoria_mock

            # ACT
            resultado = VendaService.criar_venda(
                payload=payload, user_id=1, db=mock_db_session
            )

            # ASSERT
            assert resultado is not None
            evento = mock_event_dispatcher.eventos_publicados[0]
            assert isinstance(evento, VendaCriada)
            assert evento.quantidade_itens == 3

    def test_criar_venda_com_taxa_entrega(
        self, mock_db_session, mock_event_dispatcher, fake_venda_model
    ):
        """
        CENÁRIO: Criar venda com taxa de entrega
        ESPERA: Taxa incluída no total e metadados do evento
        """
        # ARRANGE
        payload = {
            "cliente_id": 1,
            "itens": [
                {
                    "produto_id": 10,
                    "quantidade": 1,
                    "preco_unitario": 100,
                    "subtotal": 100,
                }
            ],
            "taxa_entrega": 15.50,
            "tem_entrega": True,
        }

        with (
            patch("app.vendas_models.Venda") as MockVenda,
            patch("app.vendas_models.VendaItem"),
            patch("app.financeiro_models.ContaReceber"),
            patch("app.financeiro_models.LancamentoManual"),
            patch("app.financeiro_models.CategoriaFinanceira"),
            patch("app.audit_log.log_action"),
        ):
            fake_venda_model.taxa_entrega = Decimal("15.50")
            fake_venda_model.tem_entrega = True
            fake_venda_model.total = Decimal("115.50")
            MockVenda.return_value = fake_venda_model

            categoria_mock = MagicMock()
            categoria_mock.id = 1
            mock_db_session.query.return_value.filter.return_value.first.return_value = categoria_mock

            # ACT
            VendaService.criar_venda(payload=payload, user_id=1, db=mock_db_session)

            # ASSERT
            evento = mock_event_dispatcher.eventos_publicados[0]
            assert evento.tem_entrega is True
            assert evento.metadados["taxa_entrega"] == pytest.approx(15.50)


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
        fake_pagamentos,
        make_query_mock,
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
        with (
            patch("app.vendas_models.Venda") as MockVenda,
            patch("app.vendas_models.VendaPagamento") as MockPagamento,
            patch("app.vendas_models.VendaItem"),
            patch("app.financeiro.ContasReceberService"),
        ):
            # Configurar venda existente
            fake_venda_model.status = "aberta"

            def side_effect_query(model):
                if model is MockVenda:
                    return make_query_mock(first=fake_venda_model)
                if model is MockPagamento:
                    return make_query_mock(all_=[])
                return make_query_mock()

            mock_db_session.query.side_effect = side_effect_query

            # ACT
            VendaService.finalizar_venda(
                venda_id=100,
                pagamentos=fake_pagamentos,
                user_id=1,
                user_nome="Usuário Teste",
                tenant_id="00000000-0000-0000-0000-000000000001",
                db=mock_db_session,
            )

            # ASSERT
            assert fake_venda_model.status == "finalizada"
            assert fake_venda_model.data_finalizacao is not None

            # Venda aberta ja baixa estoque na criacao; finalizar nao baixa de novo.
            mock_estoque_service.baixar_estoque.assert_not_called()

            # Verificar movimentação de caixa
            mock_caixa_service.registrar_movimentacao_venda.assert_called_once()

            # Verificar commit
            mock_db_session.commit.assert_called()

            # Verificar evento
            assert len(mock_event_dispatcher.eventos_publicados) > 0
            evento = [
                e
                for e in mock_event_dispatcher.eventos_publicados
                if isinstance(e, VendaFinalizada)
            ]
            assert len(evento) > 0
            assert evento[0].venda_id == 100
            assert evento[0].status == "finalizada"

    def test_finalizar_venda_pagamento_parcial(
        self,
        mock_db_session,
        mock_caixa_service,
        mock_estoque_service,
        mock_event_dispatcher,
        fake_venda_model,
        make_query_mock,
    ):
        """
        CENÁRIO: Finalizar venda com pagamento parcial
        ESPERA: Status 'baixa_parcial' e lançamento previsto para saldo
        """
        # ARRANGE
        with (
            patch("app.vendas_models.Venda") as MockVenda,
            patch("app.vendas_models.VendaPagamento") as MockPagamento,
            patch("app.vendas_models.VendaItem"),
            patch("app.financeiro_models.LancamentoManual") as MockLancamento,
            patch("app.financeiro_models.CategoriaFinanceira"),
            patch("app.financeiro.ContasReceberService"),
        ):
            fake_venda_model.status = "aberta"
            fake_venda_model.total = Decimal("100.00")

            def side_effect_query(model):
                if model is MockVenda:
                    return make_query_mock(first=fake_venda_model)
                if model is MockPagamento:
                    return make_query_mock(all_=[])
                return make_query_mock(first=MagicMock())

            mock_db_session.query.side_effect = side_effect_query

            pagamentos = [
                {"forma_pagamento": "Dinheiro", "valor": 50.00, "numero_parcelas": 1}
            ]

            # ACT
            VendaService.finalizar_venda(
                venda_id=100,
                pagamentos=pagamentos,
                user_id=1,
                user_nome="Usuário Teste",
                tenant_id="00000000-0000-0000-0000-000000000001",
                db=mock_db_session,
            )

            # ASSERT
            assert fake_venda_model.status == "baixa_parcial"

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
        fake_venda_model,
        make_query_mock,
    ):
        """
        CENÁRIO: Cancelar uma venda aberta
        ESPERA:
        - Status alterado para 'cancelada'
        - Estoque estornado
        - Evento VendaCancelada publicado
        """
        # ARRANGE
        with (
            patch("app.vendas_models.Venda") as MockVenda,
            patch("app.vendas_models.VendaItem") as MockItem,
            patch("app.financeiro_models.ContaReceber"),
            patch("app.caixa_models.MovimentacaoCaixa"),
            patch("app.financeiro_models.MovimentacaoFinanceira"),
            patch("app.audit_log.log_action"),
            patch("app.comissoes_estorno.estornar_comissoes_venda") as mock_estorno,
        ):
            fake_venda_model.status = "aberta"

            # Configurar itens
            item_mock = MagicMock()
            item_mock.produto_id = 10
            item_mock.quantidade = 2

            def side_effect_query(*models):
                model = models[0] if len(models) == 1 else None
                if model is MockVenda:
                    return make_query_mock(first=fake_venda_model)
                if model is MockItem:
                    return make_query_mock(all_=[item_mock])
                return make_query_mock()

            mock_db_session.query.side_effect = side_effect_query

            # Configurar estorno de comissões
            mock_estorno.return_value = {
                "success": True,
                "comissoes_estornadas": 1,
                "valor_estornado": 10.00,
            }

            # ACT
            VendaService.cancelar_venda(
                venda_id=100,
                motivo="Cliente desistiu",
                user_id=1,
                tenant_id="00000000-0000-0000-0000-000000000001",
                db=mock_db_session,
            )

            # ASSERT
            assert fake_venda_model.status == "cancelada"
            assert fake_venda_model.motivo_cancelamento == "Cliente desistiu"
            assert fake_venda_model.data_cancelamento is not None

            # Verificar estorno de estoque
            mock_estoque_service.estornar_estoque.assert_called()

            # Verificar commit
            mock_db_session.commit.assert_called()

            # Verificar evento
            eventos = [
                e
                for e in mock_event_dispatcher.eventos_publicados
                if isinstance(e, VendaCancelada)
            ]
            assert len(eventos) > 0
            evento = eventos[0]
            assert evento.venda_id == 100
            assert evento.motivo == "Cliente desistiu"

    def test_cancelar_venda_finalizada_estorna_tudo(
        self,
        mock_db_session,
        mock_estoque_service,
        mock_event_dispatcher,
        fake_venda_model,
        make_query_mock,
    ):
        """
        CENÁRIO: Cancelar venda já finalizada
        ESPERA: Estorno completo de estoque, contas, movimentações
        """
        # ARRANGE
        with (
            patch("app.vendas_models.Venda") as MockVenda,
            patch("app.vendas_models.VendaItem") as MockItem,
            patch("app.financeiro_models.ContaReceber") as MockConta,
            patch("app.caixa_models.MovimentacaoCaixa") as MockMovCaixa,
            patch("app.financeiro_models.MovimentacaoFinanceira"),
            patch("app.audit_log.log_action"),
            patch("app.comissoes_estorno.estornar_comissoes_venda"),
        ):
            fake_venda_model.status = "finalizada"

            # Itens
            item_mock = MagicMock()
            item_mock.produto_id = 10
            item_mock.quantidade = 2

            # Conta receber
            conta_mock = MagicMock()
            conta_mock.status = "recebido"

            # Lançamento
            lanc_mock = MagicMock()
            lanc_mock.status = "realizado"

            # Movimentação caixa
            mov_caixa = MagicMock()

            def side_effect_query(*models):
                model = models[0] if len(models) == 1 else None
                if model is MockVenda:
                    return make_query_mock(first=fake_venda_model)
                if model is MockItem:
                    return make_query_mock(all_=[item_mock])
                if model is MockConta:
                    return make_query_mock(all_=[conta_mock])
                if getattr(model, "__name__", "") == "LancamentoManual":
                    return make_query_mock(all_=[lanc_mock])
                if model is MockMovCaixa:
                    return make_query_mock(all_=[mov_caixa])
                return make_query_mock()

            mock_db_session.query.side_effect = side_effect_query

            # ACT
            resultado = VendaService.cancelar_venda(
                venda_id=100,
                motivo="Erro operacional",
                user_id=1,
                tenant_id="00000000-0000-0000-0000-000000000001",
                db=mock_db_session,
            )

            # ASSERT
            assert resultado["estornos"]["itens_estornados"] == 1
            assert resultado["estornos"]["contas_canceladas"] == 1
            assert resultado["estornos"]["lancamentos_cancelados"] == 1
            assert resultado["estornos"]["movimentacoes_removidas"] == 1


# ============================================================
# TESTES: VALIDAÇÕES GERAIS
# ============================================================


class TestValidacoesGerais:
    """Testes de validações do VendaService"""

    def test_criar_venda_sem_itens_retorna_erro(
        self, mock_db_session, mock_event_dispatcher
    ):
        """
        CENÁRIO: Tentar criar venda sem itens
        ESPERA: HTTPException com código 400
        """
        from fastapi import HTTPException

        payload = {"cliente_id": 1, "itens": []}

        # ACT & ASSERT
        with pytest.raises(HTTPException) as exc_info:
            VendaService.criar_venda(payload=payload, user_id=1, db=mock_db_session)

        assert exc_info.value.status_code == 400
        assert "pelo menos um item" in str(exc_info.value.detail).lower()

    def test_cancelar_venda_ja_cancelada_retorna_erro(
        self, mock_db_session, fake_venda_model
    ):
        """
        CENÁRIO: Tentar cancelar venda já cancelada
        ESPERA: HTTPException com código 400
        """
        from fastapi import HTTPException

        with patch("app.vendas_models.Venda"):
            fake_venda_model.status = "cancelada"
            mock_db_session.query.return_value.filter_by.return_value.first.return_value = fake_venda_model

            # ACT & ASSERT
            with pytest.raises(HTTPException) as exc_info:
                VendaService.cancelar_venda(
                    venda_id=100,
                    motivo="Teste",
                    user_id=1,
                    tenant_id="00000000-0000-0000-0000-000000000001",
                    db=mock_db_session,
                )

            assert exc_info.value.status_code == 400
            assert "já está cancelada" in str(exc_info.value.detail).lower()
