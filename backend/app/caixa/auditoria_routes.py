"""Auditoria do caixa por venda e lançamento, com histórico de conferências."""

import json
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session, contains_eager

from app.auth.dependencies import get_current_user_and_tenant
from app.caixa.auditoria import (
    assinatura_item,
    registrar_evento_caixa,
    reunir_espelhos_baixa_lote,
)
from app.caixa.escopo import buscar_caixa_acessivel
from app.caixa.recebimentos import filtro_recebimentos_caixa
from app.db import get_session
from app.models import AuditLog
from app.vendas_models import Venda, VendaPagamento

router = APIRouter()


class ConferenciaItemSchema(BaseModel):
    tipo_item: Literal["venda", "movimentacao", "pagamento"]
    item_id: int = Field(gt=0)
    conferido: bool
    assinatura: str = Field(min_length=64, max_length=64)
    observacao: str | None = Field(default=None, max_length=1000)


def _itens_caixa(db, caixa_id, usuario_e_tenant):
    from app.caixa_routes import listar_movimentacoes_caixa, listar_vendas_caixa

    usuario, tenant_id = usuario_e_tenant
    caixa, _ = buscar_caixa_acessivel(
        db, caixa_id=caixa_id, tenant_id=tenant_id, usuario_id=usuario.id
    )
    if not caixa:
        raise HTTPException(404, "Caixa não encontrado")
    pagamentos = (
        db.query(VendaPagamento)
        .join(Venda, VendaPagamento.venda_id == Venda.id)
        .options(contains_eager(VendaPagamento.venda).lazyload(Venda.contas_receber))
        .filter(
            filtro_recebimentos_caixa(caixa),
            Venda.tenant_id == tenant_id,
            VendaPagamento.tenant_id == tenant_id,
            func.lower(func.trim(VendaPagamento.forma_pagamento)) != "dinheiro",
        )
        .order_by(VendaPagamento.data_pagamento.desc())
        .all()
    )
    return {
        "venda": listar_vendas_caixa(
            caixa_id, db=db, current_user_and_tenant=usuario_e_tenant
        ),
        "movimentacao": listar_movimentacoes_caixa(
            caixa_id, db=db, current_user_and_tenant=usuario_e_tenant
        )["movimentacoes"],
        "pagamento": [
            {
                **pagamento.to_dict(),
                "venda_id": pagamento.venda_id,
                "venda_numero": pagamento.venda.numero_venda,
                "data_movimento": pagamento.data_pagamento.isoformat()
                if pagamento.data_pagamento
                else None,
                "tipo": "recebimento",
                "descricao": f"Recebimento da venda {pagamento.venda.numero_venda}",
                "natureza": "entrada",
            }
            for pagamento in pagamentos
        ],
    }


@router.get("/{caixa_id}/auditoria")
def obter_auditoria_caixa(
    caixa_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    from app.caixa_routes import obter_resumo_caixa

    usuario, tenant_id = current_user_and_tenant
    caixa, _ = buscar_caixa_acessivel(
        db, caixa_id=caixa_id, tenant_id=tenant_id, usuario_id=usuario.id
    )
    if not caixa:
        raise HTTPException(404, "Caixa não encontrado")
    itens = _itens_caixa(db, caixa_id, current_user_and_tenant)
    itens["movimentacao"], espelhos = reunir_espelhos_baixa_lote(
        itens["movimentacao"], itens["pagamento"]
    )
    logs = (
        db.query(AuditLog)
        .filter(
            AuditLog.tenant_id == tenant_id,
            AuditLog.entity_type == "caixa",
            AuditLog.entity_id == caixa_id,
            AuditLog.action.in_(
                ["caixa_fechado", "caixa_reaberto", "caixa_conferencia"]
            ),
        )
        .order_by(AuditLog.timestamp.desc(), AuditLog.id.desc())
        .all()
    )
    conferencias = {}
    historico = []
    for evento in logs:
        dados = json.loads(evento.new_value or "{}")
        registro = {
            "id": evento.id,
            "acao": evento.action,
            "data": evento.timestamp.isoformat(),
            "usuario_nome": dados.get("usuario_nome"),
            "observacao": evento.details,
            "dados": dados,
            "anterior": json.loads(evento.old_value) if evento.old_value else None,
        }
        if evento.action == "caixa_conferencia":
            conferencias.setdefault(
                f"{dados['tipo_item']}:{dados['item_id']}", registro
            )
        historico.append(registro)
    for tipo, registros in itens.items():
        for item in registros:
            assinatura = assinatura_item(item)
            conferencia = conferencias.get(f"{tipo}:{item['id']}")
            item["assinatura"] = assinatura
            item["conferencia"] = conferencia
            item["conferido"] = bool(
                conferencia
                and conferencia["dados"].get("conferido")
                and conferencia["dados"].get("assinatura") == assinatura
            )
    return {
        "resumo": obter_resumo_caixa(
            caixa_id,
            db=db,
            current_user_and_tenant=current_user_and_tenant,
            compact=True,
        ),
        "vendas": itens["venda"],
        "movimentacoes": itens["movimentacao"],
        "pagamentos": itens["pagamento"],
        "espelhos_pagamentos": espelhos,
        "historico": historico,
    }


@router.post("/{caixa_id}/auditoria/conferencia")
def conferir_item_caixa(
    caixa_id: int,
    dados: ConferenciaItemSchema,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    usuario, tenant_id = current_user_and_tenant
    itens = _itens_caixa(db, caixa_id, current_user_and_tenant)
    item = next(
        (item for item in itens[dados.tipo_item] if item["id"] == dados.item_id), None
    )
    if item is None:
        raise HTTPException(404, "O lançamento não pertence a este caixa")
    if assinatura_item(item) != dados.assinatura:
        raise HTTPException(
            409, "O lançamento mudou. Atualize o caixa antes de conferir."
        )
    registrar_evento_caixa(
        db,
        caixa_id=caixa_id,
        usuario=usuario,
        tenant_id=tenant_id,
        acao="caixa_conferencia",
        motivo=(dados.observacao or "").strip() or None,
        novo={**dados.model_dump(exclude={"observacao"}), "item": item},
    )
    db.commit()
    return {"success": True}
