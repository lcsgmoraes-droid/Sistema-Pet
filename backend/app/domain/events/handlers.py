"""
Event Handlers - Manipuladores de Eventos de Domínio
=====================================================

Contém handlers que reagem aos eventos publicados.

PRINCÍPIOS:
- Handlers são SIDE EFFECTS (não afetam transação principal)
- Handlers são ISOLADOS (erro em um não afeta outros)
- Handlers NÃO contêm lógica de negócio core
- Handlers devem ser RÁPIDOS (evitar operações longas)

TIPOS DE HANDLERS:
- LogEventHandler: Logs estruturados
- AuditoriaEventHandler: Persiste eventos no banco
- IAEventHandler: Placeholder para IA futura
"""

import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from .base import DomainEvent
from .venda_events import VendaCriada, VendaFinalizada, VendaCancelada

logger = logging.getLogger(__name__)


# ============================================================================
# LOG EVENT HANDLER
# ============================================================================

class LogEventHandler:
    """
    Handler que registra eventos em logs estruturados.
    
    Útil para:
    - Debugging
    - Monitoramento
    - Análise de fluxo
    - Troubleshooting
    """
    
    @staticmethod
    def on_venda_criada(event: VendaCriada) -> None:
        """Loga criação de venda"""
        logger.info(
            f"🆕 [EVENTO] VendaCriada: "
            f"#{event.numero_venda} | "
            f"Total: R$ {event.total:.2f} | "
            f"Itens: {event.quantidade_itens} | "
            f"Cliente: {event.cliente_id or 'Avulso'} | "
            f"Entrega: {'Sim' if event.tem_entrega else 'Não'}"
        )
    
    @staticmethod
    def on_venda_finalizada(event: VendaFinalizada) -> None:
        """Loga finalização de venda"""
        status_emoji = "✅" if event.status == "finalizada" else "📊"
        logger.info(
            f"{status_emoji} [EVENTO] VendaFinalizada: "
            f"#{event.numero_venda} | "
            f"Total: R$ {event.total:.2f} | "
            f"Pago: R$ {event.total_pago:.2f} | "
            f"Status: {event.status} | "
            f"Formas: {', '.join(event.formas_pagamento)} | "
            f"Vendedor: {event.user_nome}"
        )
    
    @staticmethod
    def on_venda_cancelada(event: VendaCancelada) -> None:
        """Loga cancelamento de venda"""
        logger.warning(
            f"❌ [EVENTO] VendaCancelada: "
            f"#{event.numero_venda} | "
            f"Total: R$ {event.total:.2f} | "
            f"Motivo: {event.motivo} | "
            f"Status anterior: {event.status_anterior} | "
            f"Estornos: {event.itens_estornados} itens"
        )


# ============================================================================
# AUDITORIA EVENT HANDLER
# ============================================================================

class AuditoriaEventHandler:
    """
    Handler que persiste eventos no banco de dados.
    
    Salva uma cópia de cada evento em uma tabela de auditoria,
    permitindo rastreamento completo e análises posteriores.
    
    IMPORTANTE: Este handler precisa de uma sessão do banco.
    """
    
    def __init__(self, db_session_factory: Optional[callable] = None):
        """
        Inicializa o handler com factory de sessões do banco.
        
        Args:
            db_session_factory: Função que retorna uma Session do SQLAlchemy
        """
        self.db_session_factory = db_session_factory
    
    def _save_event(self, event: DomainEvent, categoria: str, detalhes: str) -> None:
        """
        Salva evento no banco de dados (tabela audit_log).
        
        Args:
            event: Evento de domínio
            categoria: Categoria do evento (venda_criada, etc)
            detalhes: Detalhes adicionais em texto
        """
        if not self.db_session_factory:
            logger.debug("⚠️  DB session factory não configurada, pulando persistência")
            return
        
        try:
            from app.audit_log import log_action
            
            # Obter sessão do banco
            db = self.db_session_factory()
            
            # Extrair user_id do evento (todos eventos de venda têm)
            user_id = getattr(event, 'user_id', None)
            venda_id = getattr(event, 'venda_id', None)
            
            if user_id and venda_id:
                log_action(
                    db=db,
                    user_id=user_id,
                    action='EVENT',
                    entity_type='vendas',
                    entity_id=venda_id,
                    details=f"[{categoria}] {detalhes}"
                )
                db.commit()
                logger.debug(f"💾 Evento {categoria} persistido no banco (venda_id={venda_id})")
            
        except Exception as e:
            logger.error(f"❌ Erro ao persistir evento {categoria}: {str(e)}", exc_info=True)
            # Não re-raise: erro na auditoria não deve afetar fluxo
    
    def on_venda_criada(self, event: VendaCriada) -> None:
        """Persiste evento de venda criada"""
        detalhes = (
            f"Venda {event.numero_venda} criada | "
            f"Total: R$ {event.total:.2f} | "
            f"Itens: {event.quantidade_itens}"
        )
        self._save_event(event, 'venda_criada', detalhes)
    
    def on_venda_finalizada(self, event: VendaFinalizada) -> None:
        """Persiste evento de venda finalizada"""
        detalhes = (
            f"Venda {event.numero_venda} finalizada | "
            f"Total: R$ {event.total:.2f} | "
            f"Pago: R$ {event.total_pago:.2f} | "
            f"Status: {event.status}"
        )
        self._save_event(event, 'venda_finalizada', detalhes)
    
    def on_venda_cancelada(self, event: VendaCancelada) -> None:
        """Persiste evento de venda cancelada"""
        detalhes = (
            f"Venda {event.numero_venda} cancelada | "
            f"Motivo: {event.motivo} | "
            f"Estornos: {event.itens_estornados} itens"
        )
        self._save_event(event, 'venda_cancelada', detalhes)


# ============================================================================
# IA EVENT HANDLER (PLACEHOLDER PARA FUTURO)
# ============================================================================

class IAEventHandler:
    """
    Placeholder para handlers de IA futura.
    
    Casos de uso futuros:
    - Análise preditiva de vendas
    - Recomendação de produtos
    - Detecção de anomalias
    - Previsão de demanda
    - Análise de comportamento
    """
    
    @staticmethod
    def on_venda_criada(event: VendaCriada) -> None:
        """Placeholder: Análise de IA ao criar venda"""
        logger.debug(f"🤖 [IA] VendaCriada processada (placeholder)")
        # TODO: Implementar análise de IA
        # - Recomendar produtos complementares
        # - Prever probabilidade de finalização
        # - Sugerir upsell/cross-sell
    
    @staticmethod
    def on_venda_finalizada(event: VendaFinalizada) -> None:
        """Placeholder: Análise de IA ao finalizar venda"""
        logger.debug(f"🤖 [IA] VendaFinalizada processada (placeholder)")
        # TODO: Implementar análise de IA
        # - Atualizar modelo de previsão de vendas
        # - Analisar padrões de compra do cliente
        # - Atualizar scoring de clientes
    
    @staticmethod
    def on_venda_cancelada(event: VendaCancelada) -> None:
        """Placeholder: Análise de IA ao cancelar venda"""
        logger.debug(f"🤖 [IA] VendaCancelada processada (placeholder)")
        # TODO: Implementar análise de IA
        # - Detectar padrões de cancelamento
        # - Identificar problemas operacionais
        # - Alertar sobre cancelamentos anômalos


# ============================================================================
# NOTIFICAÇÃO EVENT HANDLER (PLACEHOLDER PARA FUTURO)
# ============================================================================

class NotificacaoEventHandler:
    """
    Placeholder para sistema de notificações futuro.
    
    Casos de uso futuros:
    - Enviar e-mail para cliente
    - Enviar SMS/WhatsApp
    - Notificações push
    - Integração com CRM
    """
    
    @staticmethod
    def on_venda_finalizada(event: VendaFinalizada) -> None:
        """Placeholder: Enviar notificação de venda finalizada"""
        logger.debug(f"📧 [NOTIFICAÇÃO] Venda {event.numero_venda} finalizada (placeholder)")
        # TODO: Implementar notificações
        # - Enviar e-mail de confirmação
        # - Enviar comprovante por WhatsApp
        # - Atualizar CRM
    
    @staticmethod
    def on_venda_cancelada(event: VendaCancelada) -> None:
        """Placeholder: Enviar notificação de cancelamento"""
        logger.debug(f"📧 [NOTIFICAÇÃO] Venda {event.numero_venda} cancelada (placeholder)")
        # TODO: Implementar notificações
        # - Enviar e-mail de cancelamento
        # - Notificar gestão


# ============================================================================
# INTEGRAÇÃO EVENT HANDLER (PLACEHOLDER PARA FUTURO)
# ============================================================================

class IntegracaoEventHandler:
    """
    Placeholder para integrações com sistemas externos.
    
    Casos de uso futuros:
    - ERP
    - Sistema de delivery
    - Nota fiscal eletrônica
    - Marketplace
    """
    
    @staticmethod
    def on_venda_finalizada(event: VendaFinalizada) -> None:
        """Placeholder: Integrar com sistemas externos"""
        logger.debug(f"🔗 [INTEGRAÇÃO] Venda {event.numero_venda} finalizada (placeholder)")
        # TODO: Implementar integrações
        # - Enviar para ERP
        # - Disparar emissão de NF-e
        # - Criar ordem de separação no WMS
