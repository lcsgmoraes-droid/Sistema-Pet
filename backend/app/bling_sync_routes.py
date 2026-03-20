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
from datetime import UTC, datetime
from pydantic import BaseModel, Field
import json
import asyncio
import threading
import re
import time

from .db import get_session
from .auth import get_current_user
from .auth.dependencies import get_current_user_and_tenant
from .models import User
from .produtos_models import Produto, ProdutoBlingSync, ProdutoBlingSyncQueue, EstoqueMovimentacao
from .bling_integration import BlingAPI
from .services.bling_sync_service import BlingSyncService

import logging
logger = logging.getLogger(__name__)


PRODUTO_NAO_ENCONTRADO = "Produto não encontrado"


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _buscar_item_bling_para_vinculo(bling: BlingAPI, codigo_busca: str, nome_busca: str) -> Optional[dict]:
    resultado = None
    if codigo_busca:
        resultado = bling.listar_produtos(codigo=codigo_busca, limite=50)

    itens = (resultado or {}).get("data", [])

    if not itens and nome_busca:
        resultado = bling.listar_produtos(nome=nome_busca, limite=50)
        itens = (resultado or {}).get("data", [])

    if not itens:
        return None

    codigo_local = codigo_busca.lower()
    for item in itens:
        codigo_item = str(item.get("codigo") or item.get("sku") or "").strip().lower()
        if codigo_local and codigo_item == codigo_local:
            return item

    return itens[0]


def _normalizar_termo_busca(valor: Optional[str]) -> str:
    return (valor or "").strip()


def _limpar_texto_busca(valor: str) -> str:
    return re.sub(r"\s+", " ", valor).strip()


def _extrair_lista_produtos_bling(resultado: Optional[dict]) -> list[dict]:
    itens = (resultado or {}).get("data", [])
    produtos: list[dict] = []
    for item in itens:
        if isinstance(item, dict) and isinstance(item.get("produto"), dict):
            produtos.append(item.get("produto") or {})
        elif isinstance(item, dict):
            produtos.append(item)
    return produtos


def _buscar_produtos_bling_por_termo(bling: BlingAPI, termo: str, pagina: int, limite: int) -> list[dict]:
    termo_limpo = _limpar_texto_busca(termo)
    if not termo_limpo:
        return _extrair_lista_produtos_bling(bling.listar_produtos(pagina=pagina, limite=limite))

    resultados: list[dict] = []
    vistos: set[str] = set()

    consultas = [
        {"codigo": termo_limpo, "pagina": pagina, "limite": limite},
        {"sku": termo_limpo, "pagina": pagina, "limite": limite},
        {"nome": termo_limpo, "pagina": pagina, "limite": limite},
    ]

    for params in consultas:
        try:
            itens = _extrair_lista_produtos_bling(bling.listar_produtos(**params))
        except Exception:
            # Tenta as outras estratégias de busca para reduzir falhas por filtro específico.
            continue

        for item in itens:
            item_id = str(item.get("id") or "").strip()
            if not item_id or item_id in vistos:
                continue
            vistos.add(item_id)
            resultados.append(item)

    return resultados


def _buscar_item_bling_com_retry(bling: BlingAPI, codigo_busca: str, nome_busca: str) -> Optional[dict]:
    ultima_falha = None
    for tentativa in range(3):
        try:
            return _buscar_item_bling_para_vinculo(bling, codigo_busca, nome_busca)
        except Exception as e:
            ultima_falha = e
            msg = str(e)
            if "429" in msg or "TOO_MANY_REQUESTS" in msg:
                time.sleep(0.8 + tentativa * 0.6)
                continue
            raise

    if ultima_falha:
        raise ultima_falha
    return None


def _upsert_sync_vinculo(
    db: Session,
    tenant_id,
    produto: Produto,
    bling_produto_id: str,
) -> None:
    sync = db.query(ProdutoBlingSync).filter(
        ProdutoBlingSync.produto_id == produto.id,
        ProdutoBlingSync.tenant_id == tenant_id
    ).first()

    if not sync:
        sync = ProdutoBlingSync(tenant_id=produto.tenant_id, produto_id=produto.id)
        db.add(sync)

    sync.bling_produto_id = bling_produto_id
    sync.sincronizar = True
    sync.status = "ativo"
    sync.erro_mensagem = None
    sync.updated_at = utc_now()


router = APIRouter(prefix="/estoque/sync", tags=["Sincronização Bling"])

_reconciliacao_geral_lock = threading.Lock()
_reconciliacao_geral_estado = {
    "running": False,
    "started_at": None,
    "finished_at": None,
    "result": None,
}


def _executar_reconciliacao_geral_em_background(limit: Optional[int]) -> None:
    try:
        resultado = BlingSyncService.reconcile_all_products(limit=limit)
        with _reconciliacao_geral_lock:
            _reconciliacao_geral_estado["result"] = {
                "ok": True,
                **resultado,
            }
    except Exception as error:
        logger.exception("❌ Erro na reconciliação geral em background")
        with _reconciliacao_geral_lock:
            _reconciliacao_geral_estado["result"] = {
                "ok": False,
                "erro": str(error),
            }
    finally:
        with _reconciliacao_geral_lock:
            _reconciliacao_geral_estado["running"] = False
            _reconciliacao_geral_estado["finished_at"] = utc_now()

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
    ultima_tentativa_sync: Optional[datetime] = None
    proxima_tentativa_sync: Optional[datetime] = None
    ultima_conferencia_bling: Optional[datetime] = None
    ultima_sincronizacao_sucesso: Optional[datetime] = None
    ultimo_estoque_bling: Optional[float] = None
    tentativas_sync: int = 0
    ultimo_erro: Optional[str] = None
    queue_id: Optional[int] = None
    queue_status: Optional[str] = None


class VincularProdutoRequest(BaseModel):
    produto_id: int
    bling_id: str


class ReconciliarBatchRequest(BaseModel):
    limit: int = Field(default=100, ge=1, le=1000)
    minutes: int = Field(default=30, ge=5, le=1440)

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
        raise HTTPException(status_code=404, detail=PRODUTO_NAO_ENCONTRADO)
    
    # Buscar ou criar configuração
    sync = db.query(ProdutoBlingSync).filter(
        ProdutoBlingSync.produto_id == config.produto_id
    ).first()
    
    if not sync:
        sync = ProdutoBlingSync(tenant_id=produto.tenant_id, produto_id=config.produto_id)
        db.add(sync)
    
    # Atualizar configuração
    sync.bling_produto_id = config.bling_produto_id
    sync.sincronizar = config.sincronizar
    sync.estoque_compartilhado = config.estoque_compartilhado
    sync.status = 'ativo' if config.sincronizar else 'pausado'
    sync.updated_at = utc_now()
    
    # Se não tem bling_produto_id, tentar buscar automaticamente
    if not sync.bling_produto_id and config.sincronizar:
        try:
            # Buscar no Bling por SKU ou código de barras
            bling = BlingAPI()
            resultado = bling.listar_produtos(
                codigo=produto.codigo_barras,
                sku=produto.codigo
            )
            
            produtos_bling = resultado.get('data', [])
            if produtos_bling and len(produtos_bling) > 0:
                sync.bling_produto_id = str(produtos_bling[0].get('id'))
                logger.info(f"✅ Produto vinculado automaticamente: Bling ID {sync.bling_produto_id}")
            else:
                sync.status = 'erro'
                sync.erro_mensagem = "Produto não encontrado no Bling"
                logger.warning("⚠️ Produto não encontrado no Bling")
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


@router.post("/vincular")
def vincular_produto_bling(
    body: VincularProdutoRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Vincula manualmente um produto local a um produto do Bling."""
    produto = db.query(Produto).filter(Produto.id == body.produto_id).first()
    if not produto:
        raise HTTPException(status_code=404, detail=PRODUTO_NAO_ENCONTRADO)

    sync = db.query(ProdutoBlingSync).filter(
        ProdutoBlingSync.produto_id == body.produto_id
    ).first()

    if not sync:
        sync = ProdutoBlingSync(
            tenant_id=produto.tenant_id,
            produto_id=produto.id,
        )
        db.add(sync)

    sync.bling_produto_id = str(body.bling_id)
    sync.sincronizar = True
    sync.status = "ativo"
    sync.erro_mensagem = None
    sync.updated_at = utc_now()

    db.commit()
    return {
        "message": "Produto vinculado com sucesso",
        "produto_id": produto.id,
        "bling_produto_id": sync.bling_produto_id,
    }


@router.post("/vincular-automatico/{produto_id}")
def vincular_produto_bling_automatico(
    produto_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Tenta vincular automaticamente um produto local ao Bling pelo código/SKU."""
    _current_user, tenant_id = user_and_tenant

    produto = db.query(Produto).filter(
        Produto.id == produto_id,
        Produto.tenant_id == tenant_id
    ).first()
    if not produto:
        raise HTTPException(status_code=404, detail=PRODUTO_NAO_ENCONTRADO)

    bling = BlingAPI()

    codigo_busca = (produto.codigo or "").strip()
    nome_busca = (produto.nome or "").strip()

    item_escolhido = _buscar_item_bling_para_vinculo(bling, codigo_busca, nome_busca)

    if not item_escolhido:
        raise HTTPException(status_code=404, detail="Produto não encontrado no Bling para vínculo automático")

    bling_id = str(item_escolhido.get("id") or "").strip()
    if not bling_id:
        raise HTTPException(status_code=400, detail="Resposta do Bling sem ID de produto")

    sync = db.query(ProdutoBlingSync).filter(
        ProdutoBlingSync.produto_id == produto.id,
        ProdutoBlingSync.tenant_id == tenant_id
    ).first()

    if not sync:
        sync = ProdutoBlingSync(
            tenant_id=tenant_id,
            produto_id=produto.id,
        )
        db.add(sync)

    sync.bling_produto_id = bling_id
    sync.sincronizar = True
    sync.status = "ativo"
    sync.erro_mensagem = None
    sync.updated_at = utc_now()

    db.commit()

    return {
        "message": "Produto vinculado automaticamente com sucesso",
        "produto_id": produto.id,
        "bling_produto_id": bling_id,
    }


@router.get("/produtos-bling")
def listar_produtos_bling(
    busca: Optional[str] = Query(default=None),
    pagina: int = Query(default=1, ge=1),
    limite: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Busca produtos diretamente no Bling para facilitar vínculo manual."""
    try:
        termo = _normalizar_termo_busca(busca)
        bling = BlingAPI()
        itens = _buscar_produtos_bling_por_termo(bling, termo, pagina, limite)

        # Fallback final: para termo vazio ou quando filtros específicos retornam vazio,
        # faz uma listagem padrão da página para não bloquear a tela.
        if not itens and not termo:
            itens = _extrair_lista_produtos_bling(bling.listar_produtos(pagina=pagina, limite=limite))

        produtos_bling = []
        for item in itens:
            produtos_bling.append({
                "id": str(item.get("id")),
                "descricao": item.get("nome") or item.get("descricao") or "Sem descrição",
                "codigo": item.get("codigo") or item.get("sku"),
                "estoque": item.get("estoque") or item.get("saldoFisicoTotal") or 0,
            })
        return produtos_bling
    except Exception as e:
        mensagem = str(e)
        if "429" in mensagem or "TOO_MANY_REQUESTS" in mensagem:
            raise HTTPException(
                status_code=429,
                detail="Bling com limite temporário de consultas. Aguarde alguns segundos e tente novamente.",
            )
        raise HTTPException(status_code=500, detail=f"Erro ao consultar produtos no Bling: {mensagem}")


@router.get("/health")
def health_sincronizacao(
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Resumo operacional da integração com o Bling."""
    return BlingSyncService.get_health_snapshot(db)

# ============================================================================
# ENVIAR ESTOQUE PARA BLING
# ============================================================================

@router.post("/enviar/{produto_id}")
def enviar_estoque_para_bling(
    produto_id: int,
    force: bool = Query(default=False),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Envia estoque atual do produto para o Bling
    Usado após vendas na loja física
    """
    logger.info(f"📤 Enviando estoque para Bling - Produto {produto_id} (force={force})")

    resultado = BlingSyncService.force_sync_now(
        produto_id=produto_id,
        motivo="forcar_manual" if force else "envio_manual",
    )
    if not resultado.get("ok"):
        raise HTTPException(status_code=400, detail=resultado.get("detail") or resultado.get("erro") or "Falha ao sincronizar")

    return {
        "message": "Estoque enviado para Bling com sucesso",
        "produto_id": produto_id,
        "bling_produto_id": resultado.get("bling_produto_id"),
        "estoque_enviado": resultado.get("estoque_enviado"),
        "queue_id": resultado.get("queue_id"),
    }


@router.post("/forcar/{produto_id}")
def forcar_sincronizacao_produto(
    produto_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Força o envio imediato do estoque de um único produto."""
    resultado = BlingSyncService.force_sync_now(produto_id=produto_id, motivo="botao_forcar_sync")
    if not resultado.get("ok"):
        raise HTTPException(status_code=400, detail=resultado.get("detail") or resultado.get("erro") or "Falha ao forçar sincronização")
    return {
        "message": "Sincronização forçada concluída",
        **resultado,
    }

# ============================================================================
# STATUS DE SINCRONIZAÇÃO
# ============================================================================

@router.get("/status", response_model=List[SyncStatusResponse])
def status_sincronizacao(
    apenas_divergencias: bool = False,
    busca: Optional[str] = Query(default=None),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Lista status de sincronização de todos os produtos
    
    - apenas_divergencias: Se TRUE, mostra apenas produtos com divergência de estoque
    """
    logger.info("📊 Consultando status de sincronização")
    _current_user, tenant_id = user_and_tenant
    
    # Buscar produtos com sincronização configurada
    query = db.query(Produto, ProdutoBlingSync).join(
        ProdutoBlingSync,
        Produto.id == ProdutoBlingSync.produto_id
    ).filter(
        Produto.tenant_id == tenant_id,
        ProdutoBlingSync.tenant_id == tenant_id,
        ProdutoBlingSync.sincronizar == True
    )

    if busca:
        termo = f"%{busca}%"
        query = query.filter(
            or_(
                Produto.nome.ilike(termo),
                Produto.codigo.ilike(termo),
                ProdutoBlingSync.bling_produto_id.ilike(termo),
            )
        )
    
    resultados = []
    
    for produto, sync in query.all():
        fila = db.query(ProdutoBlingSyncQueue).filter(
            ProdutoBlingSyncQueue.produto_id == produto.id
        ).order_by(ProdutoBlingSyncQueue.updated_at.desc()).first()

        # Usar dados cacheados para manter endpoint rápido e evitar rate-limit/timeout.
        estoque_bling = sync.ultimo_estoque_bling
        divergencia = sync.ultima_divergencia
        
        # Filtrar divergências se solicitado
        if apenas_divergencias and divergencia is not None and abs(divergencia) < 0.01:
            continue
        
        resultados.append(SyncStatusResponse(
            produto_id=produto.id,
            produto_nome=produto.nome,
            sku=produto.codigo,
            estoque_sistema=produto.estoque_atual or 0,
            estoque_bling=estoque_bling,
            divergencia=divergencia,
            sincronizado=sync.sincronizar,
            bling_produto_id=sync.bling_produto_id,
            ultima_sincronizacao=sync.ultima_sincronizacao,
            status=sync.status,
            ultima_tentativa_sync=sync.ultima_tentativa_sync,
            proxima_tentativa_sync=sync.proxima_tentativa_sync,
            ultima_conferencia_bling=sync.ultima_conferencia_bling,
            ultima_sincronizacao_sucesso=sync.ultima_sincronizacao_sucesso,
            ultimo_estoque_bling=sync.ultimo_estoque_bling,
            tentativas_sync=sync.tentativas_sync or 0,
            ultimo_erro=sync.erro_mensagem or (fila.ultimo_erro if fila else None),
            queue_id=fila.id if fila else None,
            queue_status=fila.status if fila else None,
        ))
    
    logger.info(f"✅ {len(resultados)} produtos em sincronização")
    return resultados


@router.post("/reprocessar-falhas")
def reprocessar_falhas(
    body: Optional[ReconciliarBatchRequest] = None,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Reagenda imediatamente os itens com erro para nova tentativa."""
    limite = body.limit if body else 100
    return BlingSyncService.reprocess_failed_syncs(limit=limite)


@router.post("/reconciliar-recentes")
def reconciliar_recentes(
    body: ReconciliarBatchRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Confere novamente produtos alterados recentemente ou com erro."""
    return BlingSyncService.reconcile_recent_products(minutes=body.minutes, limit=body.limit)


@router.post("/reconciliar-geral")
def reconciliar_geral(
    body: Optional[ReconciliarBatchRequest] = None,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Inicia auditoria ampla em segundo plano para evitar travamento por timeout."""
    limite = body.limit if body else None

    with _reconciliacao_geral_lock:
        if _reconciliacao_geral_estado["running"]:
            return {
                "status": "running",
                "message": "Auditoria geral já está em execução",
                "started_at": _reconciliacao_geral_estado["started_at"],
            }

        _reconciliacao_geral_estado["running"] = True
        _reconciliacao_geral_estado["started_at"] = utc_now()
        _reconciliacao_geral_estado["finished_at"] = None
        _reconciliacao_geral_estado["result"] = None

    worker = threading.Thread(
        target=_executar_reconciliacao_geral_em_background,
        args=(limite,),
        daemon=True,
    )
    worker.start()

    return {
        "status": "started",
        "message": "Auditoria geral iniciada em segundo plano",
        "limit": limite,
        "started_at": _reconciliacao_geral_estado["started_at"],
    }


@router.get("/reconciliar-geral/status")
def status_reconciliar_geral(
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """Retorna status da auditoria geral em background."""
    with _reconciliacao_geral_lock:
        return {
            "running": _reconciliacao_geral_estado["running"],
            "started_at": _reconciliacao_geral_estado["started_at"],
            "finished_at": _reconciliacao_geral_estado["finished_at"],
            "result": _reconciliacao_geral_estado["result"],
        }

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

    current_user, _tenant = user_and_tenant

    if origem == "sistema":
        resultado = BlingSyncService.reconcile_product(produto_id=produto_id, force_sync=True)
        if not resultado.get("ok"):
            raise HTTPException(status_code=400, detail=resultado.get("detail") or "Erro ao reconciliar")
        return {
            "message": "Reconciliação executada com sucesso",
            **resultado,
        }
    
    # Buscar produto e sync
    produto = db.query(Produto).filter(Produto.id == produto_id).first()
    if not produto:
        raise HTTPException(status_code=404, detail=PRODUTO_NAO_ENCONTRADO)
    
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
            # Busca valor do Bling (saldo físico real)
            saldo = bling.consultar_saldo_estoque(sync.bling_produto_id)
            estoque_novo = float(saldo.get('saldoFisicoTotal', 0))
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
        sync.ultima_sincronizacao = utc_now()
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
                        
                        # Registrar movimentação com status 'reservado' (pendente de NF confirmada)
                        movimentacao = EstoqueMovimentacao(
                            produto_id=produto.id,
                            tipo='saida',
                            motivo='venda_online',
                            quantidade=quantidade,
                            quantidade_anterior=estoque_anterior,
                            quantidade_nova=produto.estoque_atual,
                            documento=f"BLING-{venda_id}",
                            referencia_id=venda_id,
                            referencia_tipo='venda_bling',
                            status='reservado',  # ← NOVO: Estoque reservado até NF ser autorizada
                            observacao="Venda online via Bling - Pendente de NF autorizada",
                            user_id=1  # Sistema
                        )
                        db.add(movimentacao)
                        
                        # Atualizar sync
                        sync.ultima_sincronizacao = utc_now()
                        
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


# ============================================================================
# VINCULAR TODOS POR SKU
# ============================================================================

@router.post("/vincular-todos")
def vincular_todos_por_sku(
    limite: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Vincula automaticamente produtos do sistema com o Bling pelo código (SKU).

    Para cada produto sem vínculo:
    - Busca no Bling pelo campo `codigo`
    - Se encontrar, cria ou atualiza ProdutoBlingSync com o ID do Bling
    - Produtos do tipo PAI são ignorados

    Retorna resumo com vinculados, não encontrados e erros.
    """
    logger.info("🔗 Iniciando vinculação em massa por SKU")
    _current_user, tenant_id = user_and_tenant

    # Produtos sem vínculo ou com bling_produto_id vazio
    subq_vinculados = (
        db.query(ProdutoBlingSync.produto_id)
        .filter(
            ProdutoBlingSync.tenant_id == tenant_id,
            ProdutoBlingSync.bling_produto_id.isnot(None),
            ProdutoBlingSync.bling_produto_id != ""
        )
        .subquery()
    )

    consulta_sem_vinculo = (
        db.query(Produto)
        .filter(
            Produto.tenant_id == tenant_id,
            Produto.codigo.isnot(None),
            Produto.codigo != "",
            Produto.tipo_produto != "PAI"
        )
        .filter(Produto.id.notin_(subq_vinculados))
    )

    total_sem_vinculo = consulta_sem_vinculo.count()
    produtos_sem_vinculo = consulta_sem_vinculo.limit(limite).all()

    total = len(produtos_sem_vinculo)
    vinculados = []
    nao_encontrados = []
    erros = []

    logger.info(f"📦 Processando lote: {total} de {total_sem_vinculo} produtos sem vínculo")

    bling = BlingAPI()

    for produto in produtos_sem_vinculo:
        try:
            codigo_busca = (produto.codigo or "").strip()
            nome_busca = (produto.nome or "").strip()
            item_escolhido = _buscar_item_bling_com_retry(bling, codigo_busca, nome_busca)

            if not item_escolhido:
                nao_encontrados.append({"produto_id": produto.id, "codigo": produto.codigo, "nome": produto.nome})
                continue

            bling_produto_id = str(item_escolhido.get("id") or "").strip()
            if not bling_produto_id:
                nao_encontrados.append({"produto_id": produto.id, "codigo": produto.codigo, "nome": produto.nome})
                continue

            _upsert_sync_vinculo(db, tenant_id, produto, bling_produto_id)

            vinculados.append({
                "produto_id": produto.id,
                "codigo": produto.codigo,
                "nome": produto.nome,
                "bling_produto_id": bling_produto_id
            })

            logger.info(f"✅ Vinculado: {produto.codigo} → Bling ID {bling_produto_id}")
            time.sleep(0.35)

        except Exception as e:
            logger.error(f"❌ Erro ao vincular produto {produto.codigo}: {e}")
            erros.append({"produto_id": produto.id, "codigo": produto.codigo, "erro": str(e)})

    db.commit()

    logger.info(f"🔗 Vinculação concluída: {len(vinculados)} vinculados, {len(nao_encontrados)} não encontrados, {len(erros)} erros")

    restantes = max(total_sem_vinculo - total, 0)

    return {
        "limite_lote": limite,
        "total_sem_vinculo": total_sem_vinculo,
        "total_processados": total,
        "restantes_para_proximo_lote": restantes,
        "vinculados": len(vinculados),
        "nao_encontrados_no_bling": len(nao_encontrados),
        "erros": len(erros),
        "detalhes_vinculados": vinculados,
        "detalhes_nao_encontrados": nao_encontrados,
        "detalhes_erros": erros
    }
