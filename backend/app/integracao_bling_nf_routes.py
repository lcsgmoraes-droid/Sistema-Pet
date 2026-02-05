
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from decimal import Decimal

from app.database.session import get_db
from app.pedido_integrado_models import PedidoIntegrado
from app.pedido_integrado_item_models import PedidoIntegradoItem
from app.estoque_reserva_service import EstoqueReservaService
from app.services.provisao_simples_service import gerar_provisao_simples_por_nf
from app.utils.logger import logger

router = APIRouter(
    prefix="/integracoes/bling",
    tags=["Integração Bling - NF"]
)

@router.post("/nf")
async def receber_nf_bling(request: Request, db: Session = next(get_db())):
    payload = await request.json()

    nf_id = str(payload.get("id"))
    pedido_id = str(payload.get("pedido_id"))
    status_nf = payload.get("status")

    if not nf_id or not pedido_id:
        raise HTTPException(status_code=400, detail="NF sem vínculo com pedido")

    pedido = db.query(PedidoIntegrado).filter(
        PedidoIntegrado.pedido_bling_id == pedido_id
    ).first()

    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    itens = db.query(PedidoIntegradoItem).filter(
        PedidoIntegradoItem.pedido_integrado_id == pedido.id
    ).all()

    # ============================
    # NF EMITIDA / AUTORIZADA
    # ============================
    if status_nf in ["emitida", "autorizada"]:
        pedido.status = "confirmado"
        pedido.confirmado_em = datetime.utcnow()

        for item in itens:
            EstoqueReservaService.confirmar_venda(db, item)

        db.add(pedido)
        db.commit()
        
        # 🔹 Gerar provisão de Simples Nacional no DRE
        try:
            valor_total_nf = payload.get("valor_total", 0)
            data_emissao = payload.get("data_emissao")
            
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
    if status_nf == "cancelada":
        pedido.status = "cancelado"
        pedido.cancelado_em = datetime.utcnow()

        for item in itens:
            EstoqueReservaService.liberar(db, item)

        db.add(pedido)
        db.commit()

        return {"status": "ok", "acao": "venda_cancelada"}

    return {"status": "ignorado", "motivo": "status_nf_desconhecido"}
