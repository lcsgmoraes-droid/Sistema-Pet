"""Rotas de cancelamento e exclusao logica de vendas."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.idempotency import idempotent
from app.services.opportunity_background_processor import get_opportunity_processor
from app.utils.logger import logger as struct_logger, set_user_id
from app.vendas.routes_common import (
    _normalizar_motivo_exclusao_venda,
    _validar_tenant_e_obter_usuario,
)
from app.vendas.schemas import CancelarVendaRequest, ExcluirVendaRequest
from app.vendas_models import Venda

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/{venda_id}/cancelar")
@idempotent()  # 🔒 IDEMPOTÊNCIA: evita cancelamento duplicado
async def cancelar_venda(
    venda_id: int,
    dados: CancelarVendaRequest,
    request: Request,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Cancela uma venda realizando estorno completo.

    🎯 ROTA REFATORADA: Agora usa VendaService como orquestrador central.
    A rota apenas valida o request e chama o service.
    """
    from app.vendas.service import VendaService

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    motivo_final = _normalizar_motivo_exclusao_venda(dados.motivo)

    set_user_id(current_user.id)
    struct_logger.info(
        event="VENDA_CANCELAMENTO_START",
        message="Iniciando cancelamento de venda via service",
        venda_id=venda_id,
        motivo=motivo_final,
    )

    # Chamar service (toda lógica de negócio está lá)
    resultado = VendaService.cancelar_venda(
        venda_id=venda_id,
        motivo=motivo_final,
        user_id=current_user.id,
        tenant_id=tenant_id,
        db=db,
    )

    struct_logger.info(
        event="VENDA_CANCELADA_SUCESSO",
        message="Cancelamento concluído com sucesso",
        venda_id=venda_id,
        numero_venda=resultado["venda"]["numero_venda"],
        itens_estornados=resultado["estornos"]["itens_estornados"],
    )

    # ============================================================================
    # 💾 INVALIDAR CACHE DE OPORTUNIDADES (venda cancelada)
    # ============================================================================
    try:
        from uuid import UUID

        session_id = f"venda_{venda_id}"
        processor = get_opportunity_processor(
            tenant_id=UUID(str(tenant_id)), session_id=session_id
        )
        processor.cleanup()  # Limpa processador e invalida cache
    except Exception as e:
        logger.debug(f"Cache cleanup (cancelar): {str(e)}")
        pass

    return resultado["venda"]


@router.delete("/{venda_id}")
def excluir_venda(
    venda_id: int,
    dados: Optional[ExcluirVendaRequest] = None,
    motivo: Optional[str] = Query(
        None, description="Justificativa para cancelar/excluir a venda"
    ),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Cancelar uma venda mantendo rastreabilidade para auditoria."""
    from app.rotas_entrega_models import RotaEntrega
    from app.vendas.service import VendaService

    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    motivo_payload = motivo
    if dados:
        motivo_payload = motivo_payload or dados.motivo or dados.justificativa
    motivo_final = _normalizar_motivo_exclusao_venda(motivo_payload)

    venda = db.query(Venda).filter_by(id=venda_id, tenant_id=tenant_id).first()

    if not venda:
        raise HTTPException(status_code=404, detail="Venda nao encontrada")

    if venda.status == "pago_nf":
        raise HTTPException(
            status_code=400,
            detail="Nao e possivel cancelar/excluir uma venda com NF-e emitida. Cancele a nota fiscal primeiro.",
        )

    rota_vinculada = db.query(RotaEntrega).filter_by(venda_id=venda_id).first()
    if rota_vinculada:
        passos_resolucao = [
            f"1. Acesse a rota de entrega #{rota_vinculada.id}",
            "2. Remova esta venda da rota",
            "3. Tente cancelar/excluir a venda novamente",
        ]
        raise HTTPException(
            status_code=400,
            detail={
                "erro": "Venda vinculada a uma rota de entrega",
                "mensagem": f"Esta venda esta associada a Rota #{rota_vinculada.id} (Status: {rota_vinculada.status})",
                "solucao": "Para cancelar/excluir esta venda, primeiro remova-a da rota de entrega.",
                "passos": passos_resolucao,
                "rota_id": rota_vinculada.id,
                "rota_status": rota_vinculada.status,
            },
        )

    logger.info("Cancelando venda por rota DELETE preservando auditoria")
    resultado = VendaService.cancelar_venda(
        venda_id=venda_id,
        motivo=motivo_final,
        user_id=current_user.id,
        tenant_id=tenant_id,
        db=db,
    )

    return {
        "message": "Venda cancelada com sucesso e mantida no historico",
        "venda": resultado["venda"],
        "itens_devolvidos": resultado["estornos"].get("itens_estornados", 0),
    }
