"""Rotas de campanha automatica por validade de lote."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.campaigns.routes_common import get_db
from app.produtos_models import (
    CampanhaValidadeAutomatica,
    CampanhaValidadeExclusao,
    Produto,
    ProdutoLote,
)
from app.services.validade_campanha_service import (
    contar_exclusoes_ativas,
    obter_campanha_validade_config,
    serializar_campanha_validade_config,
)


router = APIRouter()


def _serializar_exclusao_validade(exclusao: CampanhaValidadeExclusao) -> dict:
    return {
        "id": exclusao.id,
        "produto_id": exclusao.produto_id,
        "lote_id": exclusao.lote_id,
        "ativo": bool(exclusao.ativo),
        "motivo": exclusao.motivo,
        "observacao": exclusao.observacao,
        "created_at": exclusao.created_at.isoformat() if exclusao.created_at else None,
    }


class CampanhaValidadeConfigBody(BaseModel):
    ativo: bool = False
    aplicar_app: bool = True
    aplicar_ecommerce: bool = True
    desconto_60_dias: float = 10
    desconto_30_dias: float = 20
    desconto_7_dias: float = 35
    rotulo_publico: Optional[str] = "Validade proxima"
    mensagem_publica: Optional[str] = "Oferta por lote com quantidade limitada."


class CampanhaValidadeExclusaoBody(BaseModel):
    produto_id: int
    lote_id: Optional[int] = None
    motivo: Optional[str] = None
    observacao: Optional[str] = None


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@router.get("/validade/config")
def obter_config_campanha_validade(
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    config = obter_campanha_validade_config(db, tenant_id)
    total_exclusoes = contar_exclusoes_ativas(db, tenant_id)
    return serializar_campanha_validade_config(
        config,
        total_exclusoes=total_exclusoes,
    )


@router.put("/validade/config")
def salvar_config_campanha_validade(
    body: CampanhaValidadeConfigBody,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    config = obter_campanha_validade_config(db, tenant_id)
    if not config:
        config = CampanhaValidadeAutomatica(tenant_id=tenant_id)
        db.add(config)

    config.ativo = bool(body.ativo)
    config.aplicar_app = bool(body.aplicar_app)
    config.aplicar_ecommerce = bool(body.aplicar_ecommerce)
    config.desconto_60_dias = min(max(float(body.desconto_60_dias or 0), 0.0), 95.0)
    config.desconto_30_dias = min(max(float(body.desconto_30_dias or 0), 0.0), 95.0)
    config.desconto_7_dias = min(max(float(body.desconto_7_dias or 0), 0.0), 95.0)
    config.rotulo_publico = (
        body.rotulo_publico or "Validade proxima"
    ).strip() or "Validade proxima"
    config.mensagem_publica = (
        body.mensagem_publica or "Oferta por lote com quantidade limitada."
    ).strip() or "Oferta por lote com quantidade limitada."

    db.commit()
    db.refresh(config)

    return serializar_campanha_validade_config(
        config,
        total_exclusoes=contar_exclusoes_ativas(db, tenant_id),
    )


@router.post("/validade/exclusoes")
def criar_exclusao_campanha_validade(
    body: CampanhaValidadeExclusaoBody,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant

    produto = (
        db.query(Produto)
        .filter(Produto.id == body.produto_id, Produto.tenant_id == tenant_id)
        .first()
    )
    if not produto:
        raise HTTPException(status_code=404, detail="Produto nao encontrado")

    if body.lote_id:
        lote = (
            db.query(ProdutoLote)
            .filter(
                ProdutoLote.id == body.lote_id,
                ProdutoLote.produto_id == body.produto_id,
                ProdutoLote.tenant_id == tenant_id,
            )
            .first()
        )
        if not lote:
            raise HTTPException(status_code=404, detail="Lote nao encontrado")

    query_existente = db.query(CampanhaValidadeExclusao).filter(
        CampanhaValidadeExclusao.tenant_id == tenant_id,
        CampanhaValidadeExclusao.produto_id == body.produto_id,
        CampanhaValidadeExclusao.ativo.is_(True),
    )
    if body.lote_id:
        query_existente = query_existente.filter(
            CampanhaValidadeExclusao.lote_id == body.lote_id
        )
    else:
        query_existente = query_existente.filter(
            CampanhaValidadeExclusao.lote_id.is_(None)
        )

    existente = query_existente.first()
    if existente:
        return _serializar_exclusao_validade(existente)

    exclusao = CampanhaValidadeExclusao(
        tenant_id=tenant_id,
        produto_id=body.produto_id,
        lote_id=body.lote_id,
        motivo=(body.motivo or "Opt-out manual").strip() or "Opt-out manual",
        observacao=(body.observacao or "").strip() or None,
        ativo=True,
    )
    db.add(exclusao)
    db.commit()
    db.refresh(exclusao)

    return _serializar_exclusao_validade(exclusao)


@router.delete("/validade/exclusoes/{exclusao_id}")
def remover_exclusao_campanha_validade(
    exclusao_id: int,
    db: Session = Depends(get_db),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _, tenant_id = user_and_tenant
    exclusao = (
        db.query(CampanhaValidadeExclusao)
        .filter(
            CampanhaValidadeExclusao.id == exclusao_id,
            CampanhaValidadeExclusao.tenant_id == tenant_id,
            CampanhaValidadeExclusao.ativo.is_(True),
        )
        .first()
    )
    if not exclusao:
        raise HTTPException(status_code=404, detail="Exclusao nao encontrada")

    exclusao.ativo = False
    db.commit()

    return {"ok": True, "id": exclusao_id}


# ---------------------------------------------------------------------------
# Campanhas — listagem e gestão
# ---------------------------------------------------------------------------
