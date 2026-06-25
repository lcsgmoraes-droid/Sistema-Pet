"""Formas de pagamento aceitas pelo PDV mobile."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.financeiro_models import FormaPagamento
from app.models import User
from app.routes.ecommerce_auth import _get_current_ecommerce_user

from .auth import _get_funcionario_operacional_or_403
from .schemas import (
    FuncionarioPdvFormaPagamentoResponse,
    FuncionarioPdvPagamentoRequest,
)

router = APIRouter()


def _normalizar_forma_pagamento_pdv(forma_pagamento: str) -> str:
    forma = (forma_pagamento or "").strip().lower()
    mapa = {
        "dinheiro": "Dinheiro",
        "pix": "PIX",
        "credito": "cartao_credito",
        "cartao_credito": "cartao_credito",
        "cartao de credito": "cartao_credito",
        "debito": "cartao_debito",
        "cartao_debito": "cartao_debito",
        "cartao de debito": "cartao_debito",
        "cashback": "Cashback",
    }
    if forma not in mapa:
        raise HTTPException(
            status_code=400, detail="Forma de pagamento invalida para o PDV mobile."
        )
    return mapa[forma]


def _forma_pagamento_key_funcionario_pdv(
    forma_pagamento: FormaPagamento,
) -> Optional[str]:
    texto = f"{forma_pagamento.tipo or ''} {forma_pagamento.nome or ''} {forma_pagamento.tipo_cartao or ''}".lower()
    if "credito" in texto or "crédito" in texto:
        return "credito"
    if "debito" in texto or "débito" in texto:
        return "debito"
    if "pix" in texto:
        return "pix"
    if "dinheiro" in texto:
        return "dinheiro"
    return None


def _resolver_forma_pagamento_cartao_funcionario_pdv(
    db: Session,
    tenant_id: str,
    pagamento: FuncionarioPdvPagamentoRequest,
) -> Optional[FormaPagamento]:
    forma_key = (pagamento.forma_pagamento or "").strip().lower()
    if forma_key not in {"credito", "debito", "cartao_credito", "cartao_debito"}:
        return None

    forma_normalizada = "credito" if "credito" in forma_key else "debito"
    query = db.query(FormaPagamento).filter(
        FormaPagamento.tenant_id == tenant_id,
        FormaPagamento.ativo.is_(True),
    )

    if pagamento.forma_pagamento_id:
        forma = query.filter(FormaPagamento.id == pagamento.forma_pagamento_id).first()
        if not forma:
            raise HTTPException(
                status_code=400, detail="Forma de pagamento do cartao nao encontrada."
            )
        if _forma_pagamento_key_funcionario_pdv(forma) != forma_normalizada:
            raise HTTPException(
                status_code=400,
                detail="Forma de pagamento nao corresponde ao tipo de cartao selecionado.",
            )
    else:
        formas_cartao = [
            forma
            for forma in query.order_by(FormaPagamento.nome.asc()).all()
            if _forma_pagamento_key_funcionario_pdv(forma) == forma_normalizada
        ]
        if len(formas_cartao) != 1:
            raise HTTPException(
                status_code=400, detail="Selecione a bandeira/operadora do cartao."
            )
        forma = formas_cartao[0]

    max_parcelas = max(1, int(forma.parcelas_maximas or forma.max_parcelas or 1))
    numero_parcelas = max(1, int(pagamento.numero_parcelas or 1))
    pode_parcelar = forma_normalizada == "credito" and (
        bool(forma.permite_parcelamento) or bool(forma.split_parcelas)
    )

    if forma_normalizada == "debito" and numero_parcelas != 1:
        raise HTTPException(
            status_code=400, detail="Cartao de debito deve ser registrado em 1 parcela."
        )
    if forma_normalizada == "credito" and numero_parcelas > 1 and not pode_parcelar:
        raise HTTPException(
            status_code=400, detail="Esta forma de credito nao permite parcelamento."
        )
    if forma_normalizada == "credito" and numero_parcelas > max_parcelas:
        raise HTTPException(
            status_code=400,
            detail=f"Esta forma de credito permite no maximo {max_parcelas}x.",
        )

    return forma


@router.get(
    "/funcionario/pdv/formas-pagamento",
    response_model=list[FuncionarioPdvFormaPagamentoResponse],
)
def listar_formas_pagamento_funcionario_pdv(
    current_user: User = Depends(_get_current_ecommerce_user),
    db: Session = Depends(get_session),
):
    _funcionario, tenant_id = _get_funcionario_operacional_or_403(db, current_user)
    formas = (
        db.query(FormaPagamento)
        .filter(
            FormaPagamento.tenant_id == tenant_id,
            FormaPagamento.ativo.is_(True),
        )
        .order_by(FormaPagamento.nome.asc())
        .all()
    )

    resposta = []
    for forma in formas:
        key = _forma_pagamento_key_funcionario_pdv(forma)
        if not key:
            continue
        parcelas_maximas = int(forma.parcelas_maximas or forma.max_parcelas or 1)
        max_parcelas = int(forma.max_parcelas or parcelas_maximas or 1)
        numero_parcelas = max(1, parcelas_maximas, max_parcelas)
        permite_parcelamento = key == "credito" and (
            bool(forma.permite_parcelamento) or bool(forma.split_parcelas)
        )
        resposta.append(
            {
                "id": forma.id,
                "nome": forma.nome,
                "tipo": forma.tipo,
                "key": key,
                "taxa_percentual": float(forma.taxa_percentual or 0),
                "permite_parcelamento": permite_parcelamento,
                "numero_parcelas": numero_parcelas if permite_parcelamento else 1,
                "max_parcelas": numero_parcelas if permite_parcelamento else 1,
                "parcelas_maximas": numero_parcelas if permite_parcelamento else 1,
                "operadora": forma.operadora,
                "requer_nsu": bool(forma.requer_nsu),
                "tipo_cartao": forma.tipo_cartao,
                "bandeira": forma.bandeira,
                "split_parcelas": bool(forma.split_parcelas),
            }
        )
    return resposta
