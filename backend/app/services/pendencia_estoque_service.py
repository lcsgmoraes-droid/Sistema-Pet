"""
Serviço de Notificação de Pendências de Estoque
Verifica e notifica clientes quando produtos entram no estoque
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
from typing import List, Dict
import logging

from app.pendencia_estoque_models import PendenciaEstoque
from app.produtos_models import Produto
from app.clientes_models import Cliente

logger = logging.getLogger(__name__)


def verificar_e_notificar_pendencias(
    db: Session,
    tenant_id: str,
    produto_id: int,
    quantidade_entrada: float
) -> Dict:
    """
    Verifica se há pendências para um produto que acabou de entrar no estoque
    e envia notificação via WhatsApp para os clientes.
    
    Args:
        db: Sessão do banco
        tenant_id: ID do tenant
        produto_id: ID do produto que entrou no estoque
        quantidade_entrada: Quantidade que entrou
    
    Returns:
        Dict com resumo das notificações enviadas
    """
    logger.info(f"🔔 Verificando pendências para produto {produto_id} (qtd: {quantidade_entrada})")
    
    # Buscar produto
    produto = db.query(Produto).filter(
        and_(
            Produto.id == produto_id,
            Produto.tenant_id == tenant_id
        )
    ).first()
    
    if not produto:
        logger.warning(f"❌ Produto {produto_id} não encontrado")
        return {"sucesso": False, "erro": "Produto não encontrado"}
    
    # Buscar pendências ativas ordenadas por prioridade e data
    pendencias = db.query(PendenciaEstoque).filter(
        and_(
            PendenciaEstoque.tenant_id == tenant_id,
            PendenciaEstoque.produto_id == produto_id,
            PendenciaEstoque.status == 'pendente'
        )
    ).order_by(
        PendenciaEstoque.prioridade.desc(),
        PendenciaEstoque.data_registro.asc()
    ).all()
    
    if not pendencias:
        logger.info(f"✅ Nenhuma pendência ativa para produto {produto.nome}")
        return {
            "sucesso": True,
            "produto_id": produto_id,
            "produto_nome": produto.nome,
            "pendencias_encontradas": 0,
            "notificacoes_enviadas": 0
        }
    
    logger.info(f"📋 Encontradas {len(pendencias)} pendências para notificar")
    
    notificacoes_enviadas = 0
    notificacoes_falhas = 0
    
    for pendencia in pendencias:
        try:
            # Buscar cliente
            cliente = pendencia.cliente
            
            if not cliente:
                logger.warning(f"❌ Cliente não encontrado para pendência {pendencia.id}")
                continue
            
            # Verificar se cliente tem WhatsApp
            telefone = cliente.celular or cliente.telefone
            if not telefone:
                logger.warning(f"❌ Cliente {cliente.nome} não tem telefone cadastrado")
                pendencia.status = 'finalizado'
                pendencia.data_finalizacao = datetime.utcnow()
                pendencia.motivo_cancelamento = "Cliente sem telefone cadastrado"
                continue
            
            # Montar mensagem
            mensagem = montar_mensagem_whatsapp(
                cliente_nome=cliente.nome,
                produto_nome=produto.nome,
                produto_codigo=produto.codigo,
                quantidade=pendencia.quantidade_desejada,
                valor=produto.preco_venda
            )
            
            # Enviar WhatsApp
            sucesso = enviar_whatsapp_pendencia(
                db=db,
                tenant_id=tenant_id,
                cliente_id=cliente.id,
                telefone=telefone,
                mensagem=mensagem
            )
            
            if sucesso:
                # Atualizar pendência
                pendencia.status = 'notificado'
                pendencia.data_notificacao = datetime.utcnow()
                pendencia.whatsapp_enviado = True
                notificacoes_enviadas += 1
                logger.info(f"✅ WhatsApp enviado para {cliente.nome}")
            else:
                notificacoes_falhas += 1
                logger.error(f"❌ Falha ao enviar WhatsApp para {cliente.nome}")
        
        except Exception as e:
            logger.error(f"❌ Erro ao processar pendência {pendencia.id}: {str(e)}")
            notificacoes_falhas += 1
            continue
    
    db.commit()
    
    logger.info(
        f"✅ Notificações concluídas: {notificacoes_enviadas} enviadas, "
        f"{notificacoes_falhas} falhas"
    )
    
    return {
        "sucesso": True,
        "produto_id": produto_id,
        "produto_nome": produto.nome,
        "pendencias_encontradas": len(pendencias),
        "notificacoes_enviadas": notificacoes_enviadas,
        "notificacoes_falhas": notificacoes_falhas
    }


def montar_mensagem_whatsapp(
    cliente_nome: str,
    produto_nome: str,
    produto_codigo: str,
    quantidade: float,
    valor: float
) -> str:
    """
    Monta a mensagem de WhatsApp para notificação de produto disponível.
    """
    mensagem = f"""🎉 *Boa notícia, {cliente_nome}!*

O produto que você aguardava chegou! 📦

*Produto:* {produto_nome}
*Código:* {produto_codigo}
*Quantidade disponível:* {quantidade}
*Valor:* R$ {valor:.2f}

✅ O produto já está disponível em nossa loja!

Venha garantir o seu antes que acabe! 😊

_Esta é uma notificação automática do nosso sistema de lista de espera._"""
    
    return mensagem


def enviar_whatsapp_pendencia(
    db: Session,
    tenant_id: str,
    cliente_id: int,
    telefone: str,
    mensagem: str
) -> bool:
    """
    Envia mensagem de WhatsApp para o cliente.
    
    Args:
        db: Sessão do banco
        tenant_id: ID do tenant
        cliente_id: ID do cliente
        telefone: Telefone do cliente
        mensagem: Mensagem a enviar
    
    Returns:
        True se enviado com sucesso, False caso contrário
    """
    try:
        # Importar serviço de WhatsApp
        from app.whatsapp.whatsapp_service import enviar_mensagem_texto
        
        # Enviar mensagem
        resultado = enviar_mensagem_texto(
            db=db,
            tenant_id=tenant_id,
            cliente_id=cliente_id,
            telefone=telefone,
            mensagem=mensagem,
            tipo_mensagem="notificacao_pendencia"
        )
        
        return resultado.get("sucesso", False)
    
    except Exception as e:
        logger.error(f"❌ Erro ao enviar WhatsApp: {str(e)}")
        return False


def marcar_pendencia_finalizada(
    db: Session,
    pendencia_id: int,
    venda_id: int
) -> bool:
    """
    Marca uma pendência como finalizada quando o cliente efetua a compra.
    
    Args:
        db: Sessão do banco
        pendencia_id: ID da pendência
        venda_id: ID da venda que finalizou a pendência
    
    Returns:
        True se atualizado com sucesso
    """
    try:
        pendencia = db.query(PendenciaEstoque).filter(
            PendenciaEstoque.id == pendencia_id
        ).first()
        
        if not pendencia:
            return False
        
        pendencia.status = 'finalizado'
        pendencia.data_finalizacao = datetime.utcnow()
        pendencia.venda_id = venda_id
        
        db.commit()
        
        logger.info(f"✅ Pendência {pendencia_id} finalizada com venda {venda_id}")
        return True
    
    except Exception as e:
        logger.error(f"❌ Erro ao finalizar pendência: {str(e)}")
        db.rollback()
        return False
