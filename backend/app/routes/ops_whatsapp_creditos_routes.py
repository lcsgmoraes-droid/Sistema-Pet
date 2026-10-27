"""OPS: pacotes, pedidos de compra, controle e ajustes dos creditos de WhatsApp."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_session
from app.platform_auth import require_platform_admin
from app.platform_auth_models import PlatformAdmin
from app.services import ops_whatsapp_creditos_service as svc

router = APIRouter(
    prefix="/admin/whatsapp-creditos", tags=["Admin - Créditos de WhatsApp"]
)


class PacoteNovo(BaseModel):
    nome: str = Field(min_length=2, max_length=80)
    creditos: int = Field(ge=1, le=10_000_000)
    preco: float = Field(gt=0, le=1_000_000)


class PacoteAtivo(BaseModel):
    ativo: bool


class CustoNovo(BaseModel):
    creditos: int = Field(ge=0, le=100_000)


class Confirmacao(BaseModel):
    observacao: str | None = Field(default=None, max_length=1000)


class ControleDaLoja(BaseModel):
    ativo: bool
    franquia_mensal: int = Field(ge=0, le=10_000_000)


class AjusteDaLoja(BaseModel):
    quantidade: int
    descricao: str = Field(min_length=3, max_length=200)


def _executar(db: Session, acao):
    try:
        resultado = acao()
        db.commit()
        return resultado
    except svc.CreditosError as erro:
        db.rollback()
        raise HTTPException(status_code=erro.status_code, detail=str(erro)) from erro


@router.get("")
def visao_geral(
    _admin: PlatformAdmin = Depends(require_platform_admin),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    return svc.visao_geral(db)


@router.post("/pacotes", status_code=201)
def novo_pacote(
    dados: PacoteNovo,
    admin: PlatformAdmin = Depends(require_platform_admin),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    return _executar(
        db,
        lambda: svc.pacote_para_dict(
            svc.criar_pacote(
                db,
                nome=dados.nome,
                creditos=dados.creditos,
                preco=dados.preco,
                admin_email=admin.email,
            )
        ),
    )


@router.patch("/pacotes/{pacote_id}")
def pacote_ativo(
    pacote_id: int,
    dados: PacoteAtivo,
    _admin: PlatformAdmin = Depends(require_platform_admin),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    return _executar(
        db,
        lambda: svc.pacote_para_dict(
            svc.alterar_pacote(db, pacote_id, ativo=dados.ativo)
        ),
    )


@router.put("/custos/{chave}")
def custo(
    chave: str,
    dados: CustoNovo,
    admin: PlatformAdmin = Depends(require_platform_admin),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    def _salvar():
        svc.definir_custo(db, chave, dados.creditos, admin.email)
        return {"custos": svc.custos_para_lista(db)}

    return _executar(db, _salvar)


@router.post("/compras/{compra_id}/confirmar")
def confirmar(
    compra_id: int,
    dados: Confirmacao,
    admin: PlatformAdmin = Depends(require_platform_admin),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """Pagamento recebido: libera os créditos da compra (uma única vez)."""
    return _executar(
        db,
        lambda: svc.compra_para_dict(
            svc.confirmar_compra(
                db, compra_id, admin=admin, observacao=dados.observacao
            )
        ),
    )


@router.post("/compras/{compra_id}/cancelar")
def cancelar(
    compra_id: int,
    admin: PlatformAdmin = Depends(require_platform_admin),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    return _executar(
        db,
        lambda: svc.compra_para_dict(
            svc.cancelar_compra(db, compra_id, admin_email=admin.email)
        ),
    )


@router.put("/lojas/{tenant_id}/controle")
def controle(
    tenant_id: str,
    dados: ControleDaLoja,
    admin: PlatformAdmin = Depends(require_platform_admin),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """Liga ou desliga o controle de créditos da loja e define a franquia mensal."""
    return _executar(
        db,
        lambda: svc.configurar_loja(
            db,
            tenant_id,
            ativo=dados.ativo,
            franquia_mensal=dados.franquia_mensal,
            admin=admin,
        ),
    )


@router.post("/lojas/{tenant_id}/ajuste")
def ajuste(
    tenant_id: str,
    dados: AjusteDaLoja,
    admin: PlatformAdmin = Depends(require_platform_admin),
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """Ajuste manual (positivo ou negativo) nos créditos avulsos, com motivo."""
    return _executar(
        db,
        lambda: svc.ajustar_loja(
            db,
            tenant_id,
            quantidade=dados.quantidade,
            descricao=dados.descricao,
            admin=admin,
        ),
    )
