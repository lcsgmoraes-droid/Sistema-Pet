"""Auditoria do caixa por venda e lançamento, com histórico de conferências."""

import json
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func
from sqlalchemy.orm import Session, contains_eager

from app.auth.dependencies import get_current_user_and_tenant
from app.caixa.auditoria import (
    assinatura_item,
    estado_conferencia_salvo,
    incluir_composicao_comercial,
    registrar_evento_caixa,
    reunir_espelhos_baixa_lote,
    situacao_conferencia,
)
from app.caixa.escopo import buscar_caixa_acessivel
from app.caixa.recebimentos import filtro_recebimentos_caixa
from app.caixa.pix_identificacao import (
    IdentificacaoPixSchema,
    carregar_identificacoes_pix,
    item_pagamento_auditoria,
    registrar_identificacao_pix,
)
from app.db import get_session
from app.models import AuditLog
from app.vendas_models import Venda, VendaPagamento

router = APIRouter()


class ConferenciaItemSchema(BaseModel):
    tipo_item: Literal["venda", "movimentacao", "pagamento"]
    item_id: int = Field(gt=0)
    conferido: bool
    estado: Literal["pendente", "ok", "divergencia"] | None = None
    assinatura: str = Field(min_length=64, max_length=64)
    observacao: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validar_estado(self):
        self.estado = self.estado or ("ok" if self.conferido else "pendente")
        if self.conferido != (self.estado == "ok"):
            raise ValueError("O estado informado não corresponde ao campo conferido.")
        self.observacao = (self.observacao or "").strip() or None
        if self.estado == "divergencia" and not self.observacao:
            raise ValueError("Informe uma observação para registrar a divergência.")
        return self


def _itens_caixa(db, caixa_id, usuario_e_tenant, *, resumo=None):
    from app.caixa_routes import (
        listar_movimentacoes_caixa,
        listar_vendas_caixa,
        obter_resumo_caixa,
    )

    usuario, tenant_id = usuario_e_tenant
    caixa, _ = buscar_caixa_acessivel(
        db, caixa_id=caixa_id, tenant_id=tenant_id, usuario_id=usuario.id
    )
    if not caixa:
        raise HTTPException(404, "Caixa não encontrado")
    if resumo is None:
        resumo = obter_resumo_caixa(
            caixa_id, db=db, current_user_and_tenant=usuario_e_tenant, compact=True
        )
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
        "venda": incluir_composicao_comercial(
            db,
            vendas=listar_vendas_caixa(
                caixa_id, db=db, current_user_and_tenant=usuario_e_tenant
            ),
            resumo=resumo,
            tenant_id=tenant_id,
        ),
        "movimentacao": listar_movimentacoes_caixa(
            caixa_id, db=db, current_user_and_tenant=usuario_e_tenant
        )["movimentacoes"],
        "pagamento": [item_pagamento_auditoria(pagamento) for pagamento in pagamentos],
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
    resumo = obter_resumo_caixa(
        caixa_id,
        db=db,
        current_user_and_tenant=current_user_and_tenant,
        compact=True,
    )
    itens = _itens_caixa(db, caixa_id, current_user_and_tenant, resumo=resumo)
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
        if evento.action == "caixa_conferencia":
            dados["estado"] = estado_conferencia_salvo(dados)
        registro = {
            "id": evento.id,
            "acao": evento.action,
            "data": evento.timestamp.isoformat(),
            "usuario_nome": dados.get("usuario_nome"),
            "usuario_id": evento.user_id,
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
            item.update(situacao_conferencia(assinatura, conferencia))
    carregar_identificacoes_pix(db, tenant_id, itens["pagamento"])
    return {
        "resumo": resumo,
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
        motivo=dados.observacao,
        novo={**dados.model_dump(), "item": item},
    )
    db.commit()
    return {"success": True, "estado": dados.estado, "conferido": dados.conferido}


@router.post("/{caixa_id}/auditoria/pix")
def identificar_pix_caixa(
    caixa_id: int,
    dados: IdentificacaoPixSchema,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    return registrar_identificacao_pix(
        db, current_user_and_tenant, dados, caixa_id=caixa_id
    )
