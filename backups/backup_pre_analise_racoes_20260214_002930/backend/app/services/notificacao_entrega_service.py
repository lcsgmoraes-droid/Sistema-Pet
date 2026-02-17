"""
ETAPA 10 - Service de Notificações de Entrega

⚠️ TEMPORARIAMENTE DESATIVADO - Aguardando migração para novos modelos WhatsApp IA

Dispara mensagens automáticas nos eventos:
1. Início da rota → APENAS primeiro cliente
2. Entrega OK → próximo cliente (com tempo recalculado)

Mensagem padrão única para todos os casos.
AJUSTES FINOS: Controle de duplicidade, normalização de tempo, limite de produtos.
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timedelta
from typing import Optional
import logging

# DESATIVADO - Modelos antigos de WhatsApp foram substituídos
# from app.models import WhatsAppMessage, DirecaoMensagem, StatusMensagem, Cliente
from app.models import Cliente
from app.rotas_entrega_models import RotaEntrega, RotaEntregaParada
from app.vendas_models import Venda, VendaItem
from app.services.whatsapp_service import enviar_whatsapp
from app.services.mensagem_entrega_service import montar_mensagem_entrega
from app.services.google_maps_service import calcular_tempo_estimado

logger = logging.getLogger(__name__)


def verificar_mensagem_ja_enviada(
    db: Session,
    tenant_id: int,
    cliente_id: int,
    evento_tipo: str,
    rota_id: int,
    janela_minutos: int = 5
) -> bool:
    """
    AJUSTE FINO #5 - Controle de duplicidade.
    
    ⚠️ DESATIVADO TEMPORARIAMENTE - Aguardando migração para novos modelos WhatsApp IA
    
    Verifica se mensagem similar já foi enviada recentemente.
    Evita duplicatas por retry, erro humano ou bug.
    
    Args:
        evento_tipo: "inicio_rota" ou "proximo_cliente"
        janela_minutos: Tempo para considerar duplicata (padrão: 5min)
        
    Returns:
        True se já foi enviado, False caso contrário
    """
    return False  # DESATIVADO - Retornar False para permitir envios


def enviar_mensagem_whatsapp_registro(
    db: Session,
    tenant_id: int,
    cliente_id: int,
    telefone: str,
    conteudo: str
) -> Optional[object]:  # Alterado de WhatsAppMessage para object
    """
    Registra mensagem no banco (envio manual via WhatsApp Web).
    
    ⚠️ DESATIVADO TEMPORARIAMENTE - Aguardando migração para novos modelos WhatsApp IA
    
    TODO: Quando WhatsApp Business API for integrada, fazer envio automático aqui.
    """
    logger.warning("Notificação WhatsApp desativada temporariamente - aguardando migração de modelos")
    return None  # DESATIVADO


def notificar_inicio_rota(db: Session, rota_id: int, tenant_id: int) -> int:
    """
    ETAPA 10 - EVENTO 1: Notifica APENAS o primeiro cliente ao iniciar rota.
    
    Usa mensagem padrão com:
    - Nome do cliente
    - Número do pedido
    - Lista de produtos
    - Forma de pagamento
    - Tempo estimado
    
    Returns:
        Número de mensagens enviadas (sempre 0 ou 1)
    """
    try:
        # Buscar rota
        rota = db.query(RotaEntrega).filter(
            RotaEntrega.id == rota_id,
            RotaEntrega.tenant_id == tenant_id
        ).first()
        
        if not rota:
            logger.warning(f"Rota {rota_id} não encontrada")
            return 0
        
        # Buscar PRIMEIRA parada
        primeira_parada = db.query(RotaEntregaParada).filter(
            RotaEntregaParada.rota_id == rota_id,
            RotaEntregaParada.tenant_id == tenant_id
        ).order_by(RotaEntregaParada.ordem).first()
        
        if not primeira_parada:
            logger.warning(f"Rota {rota_id} sem paradas")
            return 0
        
        # Buscar venda e cliente
        venda = db.query(Venda).filter(Venda.id == primeira_parada.venda_id).first()
        if not venda or not venda.cliente_id:
            logger.warning(f"Venda {primeira_parada.venda_id} sem cliente")
            return 0
        
        cliente = db.query(Cliente).filter(Cliente.id == venda.cliente_id).first()
        if not cliente or not cliente.celular:
            logger.warning(f"Cliente {venda.cliente_id} sem celular")
            return 0
        
        # AJUSTE FINO #5: Verificar duplicidade
        if verificar_mensagem_ja_enviada(
            db=db,
            tenant_id=tenant_id,
            cliente_id=cliente.id,
            evento_tipo="inicio_rota",
            rota_id=rota_id
        ):
            logger.info(f"Mensagem de início já enviada para cliente {cliente.id} na rota {rota_id}")
            return 0
        
        # AJUSTE FINO #3: Buscar produtos da venda (com limite)
        itens = db.query(VendaItem).filter(VendaItem.venda_id == venda.id).all()
        produtos = []
        for item in itens:
            if item.tipo == "produto" and item.produto:
                desc = f"{item.produto.nome}"
                if item.quantidade > 1:
                    desc += f" (x{int(item.quantidade)})"
                produtos.append(desc)
            elif item.tipo == "servico":
                produtos.append(item.servico_descricao or "Serviço")
        
        if not produtos:
            produtos = ["Pedido sem itens especificados"]
        
        # AJUSTE FINO #2: Calcular tempo estimado APENAS se rota foi otimizada
        minutos = None
        if primeira_parada.tempo_acumulado:
            minutos = int(primeira_parada.tempo_acumulado / 60)
        elif primeira_parada.tempo_estimado:
            minutos = int(primeira_parada.tempo_estimado / 60)
        
        # Se minutos == 0, manter None (não enviar tempo fictício)
        if minutos == 0:
            minutos = None
        
        # Montar mensagem padrão (com ou sem tempo, dependendo da otimização)
        mensagem = montar_mensagem_entrega(
            cliente_nome=cliente.nome,
            numero_pedido=str(venda.id),
            produtos=produtos,
            forma_pagamento=venda.forma_pagamento or "Não informado",
            minutos=minutos  # None se não otimizada, int se otimizada
        )
        
        # AJUSTE FINO #4: Enviar via WhatsApp (com tratamento de falha)
        try:
            enviado = enviar_whatsapp(
                telefone=cliente.celular,
                mensagem=mensagem
            )
        except Exception as e:
            # AJUSTE FINO #4: Falha no WhatsApp não bloqueia rota
            logger.error(f"Falha ao enviar WhatsApp: {e}. Continuando rota normalmente.")
            enviado = False
        
        if enviado:
            # Registrar no histórico
            enviar_mensagem_whatsapp_registro(
                db=db,
                tenant_id=tenant_id,
                cliente_id=cliente.id,
                telefone=cliente.celular,
                conteudo=mensagem
            )
            
            logger.info(f"Rota {rota_id}: Mensagem enviada para primeiro cliente ({cliente.nome})")
            return 1
        
        return 0
        
    except Exception as e:
        logger.error(f"Erro ao notificar início da rota {rota_id}: {e}")
        return 0


def notificar_proximo_cliente(db: Session, rota_id: int, parada_entregue_ordem: int, tenant_id: int) -> bool:
    """
    ETAPA 10 - EVENTO 2: Notifica próximo cliente ao marcar entrega OK.
    
    IMPORTANTE: Tempo é recalculado da POSIÇÃO ATUAL (última entrega)
    
    Args:
        parada_entregue_ordem: Ordem da parada que acabou de ser entregue
    
    Returns:
        True se mensagem foi enviada, False caso contrário
    """
    try:
        # Buscar parada que acabou de ser entregue (origem para cálculo)
        parada_atual = db.query(RotaEntregaParada).filter(
            RotaEntregaParada.rota_id == rota_id,
            RotaEntregaParada.tenant_id == tenant_id,
            RotaEntregaParada.ordem == parada_entregue_ordem
        ).first()
        
        if not parada_atual:
            logger.warning(f"Parada atual não encontrada (ordem {parada_entregue_ordem})")
            return False
        
        # Buscar próxima parada pendente
        proxima_parada = db.query(RotaEntregaParada).filter(
            RotaEntregaParada.rota_id == rota_id,
            RotaEntregaParada.tenant_id == tenant_id,
            RotaEntregaParada.ordem > parada_entregue_ordem,
            RotaEntregaParada.status == "pendente"
        ).order_by(RotaEntregaParada.ordem).first()
        
        if not proxima_parada:
            logger.info(f"Rota {rota_id}: Não há próxima parada pendente (rota finalizada)")
            return False
        
        # Buscar venda e cliente
        venda = db.query(Venda).filter(Venda.id == proxima_parada.venda_id).first()
        if not venda or not venda.cliente_id:
            logger.warning(f"Venda {proxima_parada.venda_id} sem cliente")
            return False
        
        cliente = db.query(Cliente).filter(Cliente.id == venda.cliente_id).first()
        if not cliente or not cliente.celular:
            logger.warning(f"Cliente {venda.cliente_id} sem celular")
            return False
        
        # AJUSTE FINO #5: Verificar duplicidade
        if verificar_mensagem_ja_enviada(
            db=db,
            tenant_id=tenant_id,
            cliente_id=cliente.id,
            evento_tipo="proximo_cliente",
            rota_id=rota_id
        ):
            logger.info(f"Mensagem próximo cliente já enviada para {cliente.id} na rota {rota_id}")
            return False
        
        # AJUSTE FINO #3: Buscar produtos da venda (com limite)
        itens = db.query(VendaItem).filter(VendaItem.venda_id == venda.id).all()
        produtos = []
        for item in itens:
            if item.tipo == "produto" and item.produto:
                desc = f"{item.produto.nome}"
                if item.quantidade > 1:
                    desc += f" (x{int(item.quantidade)})"
                produtos.append(desc)
            elif item.tipo == "servico":
                produtos.append(item.servico_descricao or "Serviço")
        
        if not produtos:
            produtos = ["Pedido sem itens especificados"]
        
        # AJUSTE FINO #2: Recalcular tempo da POSIÇÃO ATUAL
        origem = parada_atual.endereco
        destino = proxima_parada.endereco
        
        minutos = None  # Iniciar sem tempo (só enviar se conseguir calcular)
        
        try:
            # Tentar calcular tempo real via Google Maps
            tempo_segundos = calcular_tempo_estimado(origem, destino)
            if tempo_segundos and tempo_segundos > 0:
                minutos = max(5, int(tempo_segundos / 60))  # Mínimo 5 minutos (realista)
        except Exception as e:
            logger.warning(f"Erro ao calcular tempo real via Maps: {e}. Tentando fallback.")
            # Fallback: usar tempo da parada se disponível
            if proxima_parada.tempo_estimado and proxima_parada.tempo_estimado > 0:
                minutos = int(proxima_parada.tempo_estimado / 60)
            elif proxima_parada.tempo_acumulado and proxima_parada.tempo_acumulado > 0:
                # Calcular diferença do tempo acumulado
                tempo_diff = proxima_parada.tempo_acumulado - (parada_atual.tempo_acumulado or 0)
                if tempo_diff > 0:
                    minutos = int(tempo_diff / 60)
        
        # Se não conseguiu calcular tempo, enviar mensagem sem estimativa (mais honesto)
        if minutos and minutos == 0:
            minutos = None
        
        # Montar mensagem padrão (com ou sem tempo, dependendo do cálculo)
        mensagem = montar_mensagem_entrega(
            cliente_nome=cliente.nome,
            numero_pedido=str(venda.id),
            produtos=produtos,
            forma_pagamento=venda.forma_pagamento or "Não informado",
            minutos=minutos  # None se não calculou, int se calculou
        )
        
        # AJUSTE FINO #4: Enviar via WhatsApp (com tratamento de falha)
        try:
            enviado = enviar_whatsapp(
                telefone=cliente.celular,
                mensagem=mensagem
            )
        except Exception as e:
            # Falha no WhatsApp não bloqueia rota
            logger.error(f"Falha ao enviar WhatsApp: {e}. Continuando rota normalmente.")
            enviado = False
        
        if enviado:
            # Registrar no histórico
            enviar_mensagem_whatsapp_registro(
                db=db,
                tenant_id=tenant_id,
                cliente_id=cliente.id,
                telefone=cliente.celular,
                conteudo=mensagem
            )
            
            logger.info(f"Rota {rota_id}: Mensagem enviada para próximo cliente ({cliente.nome}), ETA: {minutos}min")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Erro ao notificar próximo cliente: {e}")
        return False
