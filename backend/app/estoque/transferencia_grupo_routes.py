import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.estoque.transferencia_grupo_schemas import (
    TransferenciaGrupoExecutarRequest,
    TransferenciaGrupoPreviaRequest,
)
from app.estoque.transferencia_grupo_service import (
    executar_transferencia_integrada,
    listar_destinos_transferencia,
    preparar_previa_transferencia,
)
from app.security.permissions_decorator import require_permission


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/transferencia-parceiro/grupo")


@router.get("/destinos")
@require_permission("produtos.editar")
def listar_destinos_grupo(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _usuario, empresa_id = user_and_tenant
    return {"items": listar_destinos_transferencia(db, empresa_origem_id=empresa_id)}


@router.post("/previa")
@require_permission("produtos.editar")
def conferir_transferencia_grupo(
    payload: TransferenciaGrupoPreviaRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _usuario, empresa_id = user_and_tenant
    return preparar_previa_transferencia(
        db,
        empresa_origem_id=empresa_id,
        payload=payload,
    )


@router.post("/executar", status_code=status.HTTP_201_CREATED)
@require_permission("produtos.editar")
def transferir_entre_empresas_grupo(
    payload: TransferenciaGrupoExecutarRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    usuario, empresa_id = user_and_tenant
    try:
        return executar_transferencia_integrada(
            db,
            empresa_origem_id=empresa_id,
            usuario_origem_id=usuario.id,
            payload=payload,
        )
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esta transferência já foi registrada. Recarregue o histórico.",
        ) from exc
    except Exception as exc:
        db.rollback()
        logger.exception("Erro na transferência integrada entre empresas: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "A transferência integrada não foi concluída. Nenhuma saída ou "
                "entrada foi mantida."
            ),
        ) from exc
