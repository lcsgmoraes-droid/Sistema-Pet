
import os
from uuid import UUID

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from decimal import Decimal

from app.db import get_session
from app.pedido_integrado_models import PedidoIntegrado
from app.pedido_integrado_item_models import PedidoIntegradoItem
from app.estoque_reserva_service import EstoqueReservaService
from app.services.provisao_simples_service import gerar_provisao_simples_por_nf
from app.tenancy.context import set_current_tenant
from app.utils.logger import logger

# Tenant fixo para webhooks do Bling (chamadas sem JWT)
_BLING_WEBHOOK_TENANT_ID = os.getenv("BLING_WEBHOOK_TENANT_ID")

router = APIRouter(
    prefix="/integracoes/bling",
    tags=["Integração Bling - NF"]
)

# Situações de NF no Bling (campo situacao é um número)
# 1=Pendente, 2=Emitida, 4=Cancelada, 5=Denegada, 9=Autorizado pelo SEFAZ
_NF_SITUACAO_AUTORIZADA = {2, 9}   # emitida ou autorizada
_NF_SITUACAO_CANCELADA  = {4, 5}   # cancelada ou denegada


@router.post("/nf")
async def receber_nf_bling(request: Request, db: Session = Depends(get_session)):
    """
    Recebe webhooks de NF-e e NF-e de consumidor do Bling.
    Formato envelope v1:
      { eventId, date, version, event: 'invoice.created'|'invoice.updated', data: {...} }
    O campo data.situacao é um NÚMERO: 2=Emitida, 9=Autorizada, 4=Cancelada.
    O payload do webhook NÃO inclui o pedido vinculado — precisa chamar a API.
    """
    body = await request.json()

    # Injetar tenant no contexto (webhook chega sem JWT)
    if _BLING_WEBHOOK_TENANT_ID:
        set_current_tenant(UUID(_BLING_WEBHOOK_TENANT_ID))

    # Desempacotar envelope Bling (v1)
    event  = body.get("event", "")   # ex: "invoice.updated"
    data   = body.get("data", body)  # fallback p/ payload legado

    nf_id = str(data.get("id", ""))
    if not nf_id or nf_id == "None":
        return {"status": "ignorado", "motivo": "sem_id"}

    situacao_num = data.get("situacao")
    try:
        situacao_num = int(situacao_num)
    except (TypeError, ValueError):
        situacao_num = 0

    # Ignorar eventos que não são emissão ou cancelamento
    if situacao_num not in _NF_SITUACAO_AUTORIZADA and situacao_num not in _NF_SITUACAO_CANCELADA:
        return {"status": "ignorado", "motivo": f"situacao_{situacao_num}_nao_tratada"}

    # Buscar NF completa na API do Bling para obter o pedido vinculado
    pedido_bling_id = None
    try:
        from app.bling_integration import BlingAPI
        nf_completa = BlingAPI().consultar_nfe(int(nf_id))
        # Campo pode estar em 'pedido', 'pedidoCompra', 'pedidoVenda' dependendo da versão
        pedido_ref = (
            nf_completa.get("pedido")
            or nf_completa.get("pedidoCompra")
            or nf_completa.get("pedidoVenda")
        )
        if isinstance(pedido_ref, dict):
            pedido_bling_id = str(pedido_ref.get("id", ""))
        logger.info(f"[BLING NF] NF {nf_id} situacao={situacao_num} pedido_bling={pedido_bling_id}")
    except Exception as e:
        logger.warning(f"[BLING NF] Falha ao buscar NF {nf_id} na API: {e}")

    if not pedido_bling_id:
        # NF sem pedido vinculado (ex: NF emitida manualmente fora do fluxo)
        return {"status": "ignorado", "motivo": "nf_sem_pedido_vinculado"}

    pedido = db.query(PedidoIntegrado).filter(
        PedidoIntegrado.pedido_bling_id == pedido_bling_id
    ).first()

    if not pedido:
        return {"status": "ignorado", "motivo": "pedido_nao_encontrado_no_sistema"}

    itens = db.query(PedidoIntegradoItem).filter(
        PedidoIntegradoItem.pedido_integrado_id == pedido.id
    ).all()

    # ============================
    # NF EMITIDA / AUTORIZADA
    # ============================
    if situacao_num in _NF_SITUACAO_AUTORIZADA:
        pedido.status = "confirmado"
        pedido.confirmado_em = datetime.utcnow()

        for item in itens:
            EstoqueReservaService.confirmar_venda(db, item)

            # Baixar estoque real — busca produto pelo SKU e desconta estoque_atual
            try:
                from app.estoque.service import EstoqueService
                from app.produtos_models import Produto

                produto = db.query(Produto).filter(
                    Produto.sku == item.sku,
                    Produto.tenant_id == pedido.tenant_id
                ).first()

                if produto:
                    EstoqueService.baixar_estoque(
                        produto_id=produto.id,
                        quantidade=float(item.quantidade),
                        motivo="venda_bling",
                        referencia_id=pedido.id,
                        referencia_tipo="pedido_integrado",
                        user_id=0,  # 0 = sistema / integração automática
                        db=db,
                        tenant_id=pedido.tenant_id,
                        documento=pedido.pedido_bling_numero,
                        observacao=f"Baixa automática via NF Bling #{nf_id}",
                    )
                else:
                    logger.warning(f"⚠️  Produto com SKU '{item.sku}' não encontrado para baixa de estoque")

            except Exception as e:
                logger.warning(f"⚠️  Falha ao baixar estoque para SKU {item.sku}: {e}")
                # Não bloqueia o fluxo — marca vendido_em e segue

        db.add(pedido)
        db.commit()
        
        # 🔹 Gerar provisão de Simples Nacional no DRE
        try:
            valor_total_nf = data.get("valorTotalNf") or data.get("valor_total", 0)
            data_emissao = data.get("dataEmissao") or data.get("data_emissao")
            
            if valor_total_nf and data_emissao and pedido.tenant_id:
                # Converter data_emissao para date
                if isinstance(data_emissao, str):
                    from datetime import date
                    data_emissao = date.fromisoformat(data_emissao.split("T")[0])
                
                resultado = gerar_provisao_simples_por_nf(
                    db=db,
                    tenant_id=pedido.tenant_id,
                    valor_nf=Decimal(str(valor_total_nf)),
                    data_emissao=data_emissao,
                    usuario_id=pedido.usuario_id if hasattr(pedido, 'usuario_id') else None
                )
                
                if resultado.get("sucesso"):
                    logger.info(f"✅ Provisão Simples: R$ {resultado['valor_provisao']:.2f} (Período {resultado['mes']}/{resultado['ano']})")
        except Exception as e:
            logger.info(f"⚠️  Erro ao gerar provisão Simples Nacional: {e}")
            import traceback
            traceback.print_exc()
            # Não falhar o webhook por conta disso

        return {"status": "ok", "acao": "venda_confirmada"}

    # ============================
    # NF CANCELADA
    # ============================
    if situacao_num in _NF_SITUACAO_CANCELADA:
        pedido.status = "cancelado"
        pedido.cancelado_em = datetime.utcnow()

        for item in itens:
            EstoqueReservaService.liberar(db, item)

        db.add(pedido)
        db.commit()

        return {"status": "ok", "acao": "venda_cancelada"}

    return {"status": "ignorado", "motivo": "status_nf_desconhecido"}
