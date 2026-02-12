"""
SINCRONIZAÇÃO BLING - Sistema Pet Shop Pro
Sincronização bidirecional de estoque entre sistema e Bling

Fluxo:
1. Venda Loja Física (PDV) → Atualiza Sistema → Envia para Bling
2. Venda Online (Bling) → Webhook → Atualiza Sistema
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import json
import asyncio

from .db import get_session
from .auth import get_current_user
from .auth.dependencies import get_current_user_and_tenant
from .models import User
from .produtos_models import Produto, ProdutoBlingSync, EstoqueMovimentacao
from .bling_integration import BlingAPI

import logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/estoque/sync", tags=["Sincronização Bling"])

# ============================================================================
# SCHEMAS
# ============================================================================

class ConfigSyncRequest(BaseModel):
    """Configurar sincronização de um produto"""
    produto_id: int
    bling_produto_id: Optional[str] = None
    sincronizar: bool = True
    estoque_compartilhado: bool = True

class SyncStatusResponse(BaseModel):
    produto_id: int
    produto_nome: str
    sku: str
    estoque_sistema: float
    estoque_bling: Optional[float]
    divergencia: Optional[float]
    sincronizado: bool
    bling_produto_id: Optional[str]
    ultima_sincronizacao: Optional[datetime]
    status: str

# ============================================================================
# CONFIGURAÇÃO DE SINCRONIZAÇÃO
# ============================================================================

@router.post("/config")
def configurar_sincronizacao(
    config: ConfigSyncRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Configurar sincronização de produto com Bling
    
    - bling_produto_id: ID do produto no Bling (ou None para buscar automaticamente)
    - sincronizar: Se TRUE, sincroniza estoque automaticamente
    - estoque_compartilhado: Se TRUE, estoque é único (loja + online)
    """
    logger.info(f"⚙️ Configurando sync - Produto {config.produto_id}")
    
    # Verificar se produto existe
    produto = db.query(Produto).filter(Produto.id == config.produto_id).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    
    # Buscar ou criar configuração
    sync = db.query(ProdutoBlingSync).filter(
        ProdutoBlingSync.produto_id == config.produto_id
    ).first()
    
    if not sync:
        sync = ProdutoBlingSync(produto_id=config.produto_id)
        db.add(sync)
    
    # Atualizar configuração
    sync.bling_produto_id = config.bling_produto_id
    sync.sincronizar = config.sincronizar
    sync.estoque_compartilhado = config.estoque_compartilhado
    sync.status = 'ativo' if config.sincronizar else 'pausado'
    sync.updated_at = datetime.utcnow()
    
    # Se não tem bling_produto_id, tentar buscar automaticamente
    if not sync.bling_produto_id and config.sincronizar:
        try:
            # Buscar no Bling por SKU ou código de barras
            bling = BlingAPI()
            resultado = bling.listar_produtos(
                codigo=produto.codigo_barras,
                sku=produto.sku
            )
            
            produtos_bling = resultado.get('data', [])
            if produtos_bling and len(produtos_bling) > 0:
                sync.bling_produto_id = str(produtos_bling[0].get('id'))
                logger.info(f"✅ Produto vinculado automaticamente: Bling ID {sync.bling_produto_id}")
            else:
                sync.status = 'erro'
                sync.erro_mensagem = "Produto não encontrado no Bling"
                logger.warning(f"⚠️ Produto não encontrado no Bling")
        except Exception as e:
            logger.error(f"❌ Erro ao buscar produto no Bling: {e}")
            sync.status = 'erro'
            sync.erro_mensagem = str(e)
    
    db.commit()
    db.refresh(sync)
    
    return {
        "message": "Sincronização configurada com sucesso",
        "produto_id": sync.produto_id,
        "bling_produto_id": sync.bling_produto_id,
        "sincronizar": sync.sincronizar,
        "status": sync.status
    }

# ============================================================================
# ENVIAR ESTOQUE PARA BLING
# ============================================================================

@router.post("/enviar/{produto_id}")
def enviar_estoque_para_bling(
    produto_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Envia estoque atual do produto para o Bling
    Usado após vendas na loja física
    """
    logger.info(f"📤 Enviando estoque para Bling - Produto {produto_id}")
    
    # Buscar produto e configuração
    produto = db.query(Produto).filter(Produto.id == produto_id).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    
    sync = db.query(ProdutoBlingSync).filter(
        ProdutoBlingSync.produto_id == produto_id
    ).first()
    
    if not sync or not sync.sincronizar:
        raise HTTPException(status_code=400, detail="Produto não configurado para sincronização")
    
    if not sync.bling_produto_id:
        raise HTTPException(status_code=400, detail="Produto não vinculado ao Bling")
    
    try:
        # Atualizar estoque no Bling
        bling = BlingAPI()
        resultado = bling.atualizar_estoque_produto(
            produto_id=sync.bling_produto_id,
            estoque_novo=produto.estoque_atual or 0
        )
        
        # Atualizar última sincronização
        sync.ultima_sincronizacao = datetime.utcnow()
        sync.status = 'ativo'
        sync.erro_mensagem = None
        db.commit()
        
        logger.info(f"✅ Estoque enviado para Bling: {produto.estoque_atual}")
        
        return {
            "message": "Estoque enviado para Bling com sucesso",
            "produto_id": produto_id,
            "bling_produto_id": sync.bling_produto_id,
            "estoque_enviado": produto.estoque_atual,
            "timestamp": sync.ultima_sincronizacao
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao enviar estoque para Bling: {e}")
        sync.status = 'erro'
        sync.erro_mensagem = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Erro ao sincronizar com Bling: {str(e)}")

# ============================================================================
# STATUS DE SINCRONIZAÇÃO
# ============================================================================

@router.get("/status", response_model=List[SyncStatusResponse])
def status_sincronizacao(
    apenas_divergencias: bool = False,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Lista status de sincronização de todos os produtos
    
    - apenas_divergencias: Se TRUE, mostra apenas produtos com divergência de estoque
    """
    logger.info(f"📊 Consultando status de sincronização")
    
    # Buscar produtos com sincronização configurada
    query = db.query(Produto, ProdutoBlingSync).join(
        ProdutoBlingSync,
        Produto.id == ProdutoBlingSync.produto_id
    ).filter(
        ProdutoBlingSync.sincronizar == True
    )
    
    resultados = []
    
    for produto, sync in query.all():
        # Consultar estoque no Bling
        estoque_bling = None
        divergencia = None
        
        if sync.bling_produto_id:
            try:
                bling = BlingAPI()
                produto_bling = bling.consultar_produto(sync.bling_produto_id)
                if produto_bling:
                    estoque_bling = float(produto_bling.get('estoques', {}).get('saldoVirtualTotal', 0))
                    divergencia = (produto.estoque_atual or 0) - estoque_bling
            except Exception as e:
                logger.error(f"❌ Erro ao consultar Bling: {e}")
        
        # Filtrar divergências se solicitado
        if apenas_divergencias and divergencia is not None and abs(divergencia) < 0.01:
            continue
        
        resultados.append(SyncStatusResponse(
            produto_id=produto.id,
            produto_nome=produto.nome,
            sku=produto.sku,
            estoque_sistema=produto.estoque_atual or 0,
            estoque_bling=estoque_bling,
            divergencia=divergencia,
            sincronizado=sync.sincronizar,
            bling_produto_id=sync.bling_produto_id,
            ultima_sincronizacao=sync.ultima_sincronizacao,
            status=sync.status
        ))
    
    logger.info(f"✅ {len(resultados)} produtos em sincronização")
    return resultados

# ============================================================================
# RECONCILIAR DIVERGÊNCIAS
# ============================================================================

@router.post("/reconciliar/{produto_id}")
def reconciliar_estoque(
    produto_id: int,
    origem: str = Query(default="sistema", description="Origem: sistema, bling ou manual"),
    valor_manual: Optional[float] = Query(default=None, description="Valor manual para ajuste"),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Reconciliar divergência de estoque
    
    Opções:
    - origem=sistema: Usa valor do sistema → envia para Bling
    - origem=bling: Busca valor do Bling → atualiza sistema
    - origem=manual: Usa valor_manual → atualiza ambos
    """
    logger.info(f"🔄 Reconciliando estoque - Produto {produto_id}, Origem: {origem}")
    
    # Buscar produto e sync
    produto = db.query(Produto).filter(Produto.id == produto_id).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    
    sync = db.query(ProdutoBlingSync).filter(
        ProdutoBlingSync.produto_id == produto_id
    ).first()
    
    if not sync or not sync.bling_produto_id:
        raise HTTPException(status_code=400, detail="Produto não configurado para sincronização")
    
    try:
        bling = BlingAPI()
        estoque_anterior = produto.estoque_atual or 0
        estoque_novo = None
        
        if origem == "sistema":
            # Usa valor do sistema
            estoque_novo = estoque_anterior
            bling.atualizar_estoque_produto(sync.bling_produto_id, estoque_novo)
            logger.info(f"✅ Sistema → Bling: {estoque_novo}")
            
        elif origem == "bling":
            # Busca valor do Bling
            produto_bling = bling.consultar_produto(sync.bling_produto_id)
            estoque_novo = float(produto_bling.get('estoques', {}).get('saldoVirtualTotal', 0))
            produto.estoque_atual = estoque_novo
            logger.info(f"✅ Bling → Sistema: {estoque_novo}")
            
        elif origem == "manual":
            if valor_manual is None:
                raise HTTPException(status_code=400, detail="valor_manual é obrigatório para origem=manual")
            estoque_novo = valor_manual
            produto.estoque_atual = estoque_novo
            bling.atualizar_estoque_produto(sync.bling_produto_id, estoque_novo)
            logger.info(f"✅ Manual → Ambos: {estoque_novo}")
            
        else:
            raise HTTPException(status_code=400, detail="origem deve ser: sistema, bling ou manual")
        
        # Registrar movimentação de ajuste
        if origem in ["bling", "manual"] and estoque_novo != estoque_anterior:
            diferenca = estoque_novo - estoque_anterior
            movimentacao = EstoqueMovimentacao(
                produto_id=produto.id,
                tipo='entrada' if diferenca > 0 else 'saida',
                motivo='ajuste_reconciliacao',
                quantidade=abs(diferenca),
                quantidade_anterior=estoque_anterior,
                quantidade_nova=estoque_novo,
                observacao=f"Reconciliação Bling - Origem: {origem}",
                user_id=current_user.id
            )
            db.add(movimentacao)
        
        # Atualizar sync
        sync.ultima_sincronizacao = datetime.utcnow()
        sync.status = 'ativo'
        sync.erro_mensagem = None
        
        db.commit()
        
        return {
            "message": "Estoque reconciliado com sucesso",
            "produto_id": produto_id,
            "estoque_anterior": estoque_anterior,
            "estoque_novo": estoque_novo,
            "diferenca": estoque_novo - estoque_anterior,
            "origem": origem
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao reconciliar: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao reconciliar: {str(e)}")

# ============================================================================
# WEBHOOK BLING
# ============================================================================

@router.post("/webhook/bling")
async def webhook_bling(
    request: Request,
    db: Session = Depends(get_session)
):
    """
    Webhook para receber notificações do Bling
    
    Eventos suportados:
    - Venda criada: Baixa estoque no sistema
    - Venda cancelada: Retorna estoque ao sistema
    """
    try:
        body = await request.json()
        logger.info(f"📥 Webhook Bling recebido: {body}")
        
        evento = body.get('topic')
        dados = body.get('data', {})
        
        if evento == 'vendas.created':
            # Venda online criada - baixar estoque
            venda_id = dados.get('id')
            itens = dados.get('itens', [])
            
            for item in itens:
                produto_bling_id = str(item.get('produtoId'))
                quantidade = float(item.get('quantidade', 0))
                
                # Buscar produto no sistema
                sync = db.query(ProdutoBlingSync).filter(
                    ProdutoBlingSync.bling_produto_id == produto_bling_id
                ).first()
                
                if sync and sync.sincronizar:
                    produto = db.query(Produto).filter(
                        Produto.id == sync.produto_id
                    ).first()
                    
                    if produto:
                        estoque_anterior = produto.estoque_atual or 0
                        produto.estoque_atual = max(0, estoque_anterior - quantidade)
                        
                        # Registrar movimentação
                        movimentacao = EstoqueMovimentacao(
                            produto_id=produto.id,
                            tipo='saida',
                            motivo='venda_online',
                            quantidade=quantidade,
                            quantidade_anterior=estoque_anterior,
                            quantidade_nova=produto.estoque_atual,
                            documento=f"BLING-{venda_id}",
                            observacao="Venda online via Bling",
                            user_id=1  # Sistema
                        )
                        db.add(movimentacao)
                        
                        # Atualizar sync
                        sync.ultima_sincronizacao = datetime.utcnow()
                        
                        logger.info(f"✅ Estoque baixado - Produto {produto.id}: {estoque_anterior} → {produto.estoque_atual}")
            
            db.commit()
            return {"status": "success", "message": "Estoque atualizado"}
            
        elif evento == 'vendas.deleted':
            # Venda cancelada - retornar estoque
            # Implementar lógica similar...
            pass
        
        return {"status": "ignored", "message": f"Evento {evento} não processado"}
        
    except Exception as e:
        logger.error(f"❌ Erro no webhook: {e}")
        return {"status": "error", "message": str(e)}

logger.info("✅ Módulo de sincronização Bling carregado")
