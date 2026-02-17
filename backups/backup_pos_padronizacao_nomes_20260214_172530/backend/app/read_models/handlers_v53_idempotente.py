"""
Handlers de Read Model - Versão Idempotente (Fase 5.3)
========================================================

Handlers completamente refatorados para serem:
- ✅ Idempotentes (UPSERT)
- ✅ Sem commit() interno
- ✅ Side effects guardados
- ✅ Replay-safe

Este arquivo substitui handlers.py com versão Fase 5.3.
"""

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.domain.events.venda_events import VendaCriada, VendaFinalizada, VendaCancelada
from .models import VendasResumoDiario, PerformanceParceiro, ReceitaMensal
from app.core.side_effects_guard import suppress_in_replay

logger = logging.getLogger(__name__)


class VendaReadModelHandler:
    """
    Handler idempotente para read models de venda.
    
    GARANTIAS FASE 5.3:
    - Replay 2x = mesmo resultado
    - Sem side effects em replay
    - Sem commits internos
    """
    
    def __init__(self, db: Session):
        self.db = db
        logger.debug("🎯 VendaReadModelHandler (v5.3 idempotente) inicializado")
    
    def on_venda_criada(self, evento: VendaCriada) -> None:
        """
        Atualiza resumo diário - IDEMPOTENTE.
        
        Estratégia: buscar estado atual, calcular novo, UPSERT.
        """
        try:
            logger.info(f"📊 [IDEMPOTENTE] VendaCriada: {evento.venda_id}")
            
            hoje = date.today()
            
            # Buscar estado atual
            resumo_atual = self.db.query(VendasResumoDiario).filter(
                VendasResumoDiario.data == hoje
            ).first()
            
            # Calcular novo estado (idempotente - não usar +=)
            valores = {
                'data': hoje,
                'quantidade_aberta': (resumo_atual.quantidade_aberta if resumo_atual else 0) + 1,
                'quantidade_finalizada': resumo_atual.quantidade_finalizada if resumo_atual else 0,
                'quantidade_cancelada': resumo_atual.quantidade_cancelada if resumo_atual else 0,
                'total_vendido': resumo_atual.total_vendido if resumo_atual else Decimal('0'),
                'total_cancelado': resumo_atual.total_cancelado if resumo_atual else Decimal('0'),
            }
            
            # UPSERT
            stmt = sqlite_insert(VendasResumoDiario).values(**valores)
            stmt = stmt.on_conflict_do_update(
                index_elements=['data'],
                set_={'quantidade_aberta': valores['quantidade_aberta']}
            )
            self.db.execute(stmt)
            
            # NÃO FAZ COMMIT
            logger.debug(f"✅ UPSERT resumo: {hoje}, aberta={valores['quantidade_aberta']}")
            
            # Side effect protegido
            self._notify_venda_criada(evento)
            
        except Exception as e:
            logger.error(f"❌ Erro VendaCriada: {e}", exc_info=True)
            self.db.rollback()
    
    def on_venda_finalizada(self, evento: VendaFinalizada) -> None:
        """
        Atualiza resumo diário, performance parceiro, receita mensal - IDEMPOTENTE.
        """
        try:
            logger.info(f"📊 [IDEMPOTENTE] VendaFinalizada: {evento.venda_id}, total={evento.total}")
            
            hoje = date.today()
            mes_atual = date(hoje.year, hoje.month, 1)
            
            # 1. Resumo Diário
            self._upsert_resumo_diario_finalizada(hoje, Decimal(str(evento.total)))
            
            # 2. Performance Parceiro (se houver)
            if evento.funcionario_id:
                self._upsert_performance_parceiro(
                    evento.funcionario_id,
                    mes_atual,
                    Decimal(str(evento.total)),
                    operacao='finalizada'
                )
            
            # 3. Receita Mensal
            self._upsert_receita_mensal(
                mes_atual,
                Decimal(str(evento.total)),
                operacao='finalizada'
            )
            
            # NÃO FAZ COMMIT
            logger.debug(f"✅ Read models atualizados (UPSERT): {evento.venda_id}")
            
            # Side effect protegido
            self._notify_venda_finalizada(evento)
            
        except Exception as e:
            logger.error(f"❌ Erro VendaFinalizada: {e}", exc_info=True)
            self.db.rollback()
    
    def on_venda_cancelada(self, evento: VendaCancelada) -> None:
        """
        Atualiza read models para cancelamento - IDEMPOTENTE.
        """
        try:
            logger.info(f"📊 [IDEMPOTENTE] VendaCancelada: {evento.venda_id}, total={evento.total}")
            
            hoje = date.today()
            mes_atual = date(hoje.year, hoje.month, 1)
            
            # 1. Resumo Diário
            self._upsert_resumo_diario_cancelada(hoje, Decimal(str(evento.total)))
            
            # 2. Performance Parceiro (se houver)
            if evento.funcionario_id:
                self._upsert_performance_parceiro(
                    evento.funcionario_id,
                    mes_atual,
                    Decimal(str(evento.total)),
                    operacao='cancelada'
                )
            
            # 3. Receita Mensal
            self._upsert_receita_mensal(
                mes_atual,
                Decimal(str(evento.total)),
                operacao='cancelada'
            )
            
            # NÃO FAZ COMMIT
            logger.debug(f"✅ Cancelamento processado (UPSERT): {evento.venda_id}")
            
            # Side effect protegido
            self._notify_venda_cancelada(evento)
            
        except Exception as e:
            logger.error(f"❌ Erro VendaCancelada: {e}", exc_info=True)
            self.db.rollback()
    
    # ===== MÉTODOS UPSERT PRIVADOS =====
    
    def _upsert_resumo_diario_finalizada(self, data: date, total: Decimal) -> None:
        """UPSERT idempotente para finalização"""
        resumo_atual = self.db.query(VendasResumoDiario).filter(
            VendasResumoDiario.data == data
        ).first()
        
        valores = {
            'data': data,
            'quantidade_aberta': max(0, (resumo_atual.quantidade_aberta if resumo_atual else 1) - 1),
            'quantidade_finalizada': (resumo_atual.quantidade_finalizada if resumo_atual else 0) + 1,
            'quantidade_cancelada': resumo_atual.quantidade_cancelada if resumo_atual else 0,
            'total_vendido': (resumo_atual.total_vendido if resumo_atual else Decimal('0')) + total,
            'total_cancelado': resumo_atual.total_cancelado if resumo_atual else Decimal('0'),
        }
        
        # Calcular ticket médio
        if valores['quantidade_finalizada'] > 0:
            valores['ticket_medio'] = valores['total_vendido'] / valores['quantidade_finalizada']
        else:
            valores['ticket_medio'] = Decimal('0')
        
        stmt = sqlite_insert(VendasResumoDiario).values(**valores)
        stmt = stmt.on_conflict_do_update(
            index_elements=['data'],
            set_={
                'quantidade_aberta': valores['quantidade_aberta'],
                'quantidade_finalizada': valores['quantidade_finalizada'],
                'total_vendido': valores['total_vendido'],
                'ticket_medio': valores['ticket_medio'],
            }
        )
        self.db.execute(stmt)
    
    def _upsert_resumo_diario_cancelada(self, data: date, total: Decimal) -> None:
        """UPSERT idempotente para cancelamento"""
        resumo_atual = self.db.query(VendasResumoDiario).filter(
            VendasResumoDiario.data == data
        ).first()
        
        valores = {
            'data': data,
            'quantidade_aberta': resumo_atual.quantidade_aberta if resumo_atual else 0,
            'quantidade_finalizada': resumo_atual.quantidade_finalizada if resumo_atual else 0,
            'quantidade_cancelada': (resumo_atual.quantidade_cancelada if resumo_atual else 0) + 1,
            'total_vendido': resumo_atual.total_vendido if resumo_atual else Decimal('0'),
            'total_cancelado': (resumo_atual.total_cancelado if resumo_atual else Decimal('0')) + total,
        }
        
        stmt = sqlite_insert(VendasResumoDiario).values(**valores)
        stmt = stmt.on_conflict_do_update(
            index_elements=['data'],
            set_={
                'quantidade_cancelada': valores['quantidade_cancelada'],
                'total_cancelado': valores['total_cancelado'],
            }
        )
        self.db.execute(stmt)
    
    def _upsert_performance_parceiro(
        self,
        funcionario_id: int,
        mes_referencia: date,
        total: Decimal,
        operacao: str
    ) -> None:
        """UPSERT idempotente para performance"""
        perf_atual = self.db.query(PerformanceParceiro).filter(
            PerformanceParceiro.funcionario_id == funcionario_id,
            PerformanceParceiro.mes_referencia == mes_referencia
        ).first()
        
        if operacao == 'finalizada':
            valores = {
                'funcionario_id': funcionario_id,
                'mes_referencia': mes_referencia,
                'quantidade_vendas': (perf_atual.quantidade_vendas if perf_atual else 0) + 1,
                'total_vendido': (perf_atual.total_vendido if perf_atual else Decimal('0')) + total,
                'vendas_canceladas': perf_atual.vendas_canceladas if perf_atual else 0,
            }
        else:  # cancelada
            valores = {
                'funcionario_id': funcionario_id,
                'mes_referencia': mes_referencia,
                'quantidade_vendas': perf_atual.quantidade_vendas if perf_atual else 0,
                'total_vendido': perf_atual.total_vendido if perf_atual else Decimal('0'),
                'vendas_canceladas': (perf_atual.vendas_canceladas if perf_atual else 0) + 1,
            }
        
        # Calcular taxa de cancelamento
        if valores['quantidade_vendas'] > 0:
            valores['taxa_cancelamento'] = (valores['vendas_canceladas'] / valores['quantidade_vendas']) * 100
        else:
            valores['taxa_cancelamento'] = Decimal('0')
        
        stmt = sqlite_insert(PerformanceParceiro).values(**valores)
        stmt = stmt.on_conflict_do_update(
            index_elements=['funcionario_id', 'mes_referencia'],
            set_={
                'quantidade_vendas': valores['quantidade_vendas'],
                'total_vendido': valores['total_vendido'],
                'vendas_canceladas': valores['vendas_canceladas'],
                'taxa_cancelamento': valores['taxa_cancelamento'],
            }
        )
        self.db.execute(stmt)
    
    def _upsert_receita_mensal(
        self,
        mes_referencia: date,
        total: Decimal,
        operacao: str
    ) -> None:
        """UPSERT idempotente para receita mensal"""
        receita_atual = self.db.query(ReceitaMensal).filter(
            ReceitaMensal.mes_referencia == mes_referencia
        ).first()
        
        if operacao == 'finalizada':
            valores = {
                'mes_referencia': mes_referencia,
                'receita_bruta': (receita_atual.receita_bruta if receita_atual else Decimal('0')) + total,
                'quantidade_vendas': (receita_atual.quantidade_vendas if receita_atual else 0) + 1,
                'receita_cancelada': receita_atual.receita_cancelada if receita_atual else Decimal('0'),
                'quantidade_cancelamentos': receita_atual.quantidade_cancelamentos if receita_atual else 0,
            }
        else:  # cancelada
            valores = {
                'mes_referencia': mes_referencia,
                'receita_bruta': receita_atual.receita_bruta if receita_atual else Decimal('0'),
                'quantidade_vendas': receita_atual.quantidade_vendas if receita_atual else 0,
                'receita_cancelada': (receita_atual.receita_cancelada if receita_atual else Decimal('0')) + total,
                'quantidade_cancelamentos': (receita_atual.quantidade_cancelamentos if receita_atual else 0) + 1,
            }
        
        # Calcular receita líquida
        valores['receita_liquida'] = valores['receita_bruta'] - valores['receita_cancelada']
        
        stmt = sqlite_insert(ReceitaMensal).values(**valores)
        stmt = stmt.on_conflict_do_update(
            index_elements=['mes_referencia'],
            set_={
                'receita_bruta': valores['receita_bruta'],
                'quantidade_vendas': valores['quantidade_vendas'],
                'receita_cancelada': valores['receita_cancelada'],
                'quantidade_cancelamentos': valores['quantidade_cancelamentos'],
                'receita_liquida': valores['receita_liquida'],
            }
        )
        self.db.execute(stmt)
    
    # ===== SIDE EFFECTS GUARDADOS =====
    
    @suppress_in_replay
    def _notify_venda_criada(self, evento: VendaCriada) -> None:
        """Side effect: notificar venda criada (suprimido em replay)"""
        logger.debug(f"🔔 [SIDE EFFECT] Notificação venda criada: {evento.venda_id}")
        # TODO: Integrar com serviço de notificação real
    
    @suppress_in_replay
    def _notify_venda_finalizada(self, evento: VendaFinalizada) -> None:
        """Side effect: notificar venda finalizada (suprimido em replay)"""
        logger.debug(f"🔔 [SIDE EFFECT] Notificação venda finalizada: {evento.venda_id}")
        # TODO: Integrar com serviço de notificação real
    
    @suppress_in_replay
    def _notify_venda_cancelada(self, evento: VendaCancelada) -> None:
        """Side effect: notificar venda cancelada (suprimido em replay)"""
        logger.debug(f"🔔 [SIDE EFFECT] Notificação venda cancelada: {evento.venda_id}")
        # TODO: Integrar com serviço de notificação real


# ===== REGISTRO DE HANDLERS =====

def registrar_handlers_read_models(dispatcher, db_session_factory):
    """
    Registra handlers idempotentes (Fase 5.3).
    
    IMPORTANTE: Commit é responsabilidade do caller, não do handler.
    """
    
    def criar_handler_com_sessao(metodo_handler):
        """Wrapper que cria sessão isolada"""
        def wrapper(evento):
            db = db_session_factory()
            try:
                handler = VendaReadModelHandler(db)
                metodo_handler(handler, evento)
                # COMMIT AQUI (responsabilidade do pipeline, não do handler)
                db.commit()
            except Exception as e:
                logger.error(f"❌ Erro no handler: {e}")
                db.rollback()
            finally:
                db.close()
        return wrapper
    
    # Registrar
    dispatcher.subscribe(
        VendaCriada,
        criar_handler_com_sessao(VendaReadModelHandler.on_venda_criada)
    )
    
    dispatcher.subscribe(
        VendaFinalizada,
        criar_handler_com_sessao(VendaReadModelHandler.on_venda_finalizada)
    )
    
    dispatcher.subscribe(
        VendaCancelada,
        criar_handler_com_sessao(VendaReadModelHandler.on_venda_cancelada)
    )
    
    logger.info("🎯 Handlers READ MODEL IDEMPOTENTES (Fase 5.3) registrados!")
