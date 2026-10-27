"""Entrega sem cobrança, com conferência do valor e histórico preservado."""

from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException

from app.banho_tosa_vendas import _montar_itens_venda, _obter_venda_existente


TIPO_ENTREGA_SEM_COBRANCA = "entrega_sem_cobranca"


def entrega_sem_cobranca_registrada(atendimento) -> bool:
    return atendimento.status == "entregue" and any(
        item.get("tipo") == TIPO_ENTREGA_SEM_COBRANCA
        and item.get("system_generated") is True
        for item in getattr(atendimento, "ocorrencias", None) or []
    )


def registrar_entrega_sem_cobranca(db, tenant_id, user_id, atendimento, motivo):
    motivo = (motivo or "").strip()
    if len(motivo) < 3:
        raise HTTPException(422, "Informe o motivo da entrega sem cobranca.")
    if atendimento.pacote_credito_id:
        raise HTTPException(
            422, "Atendimento com pacote deve manter sua vinculacao financeira."
        )
    if _obter_venda_existente(db, tenant_id, atendimento):
        raise HTTPException(
            422, "Atendimento ja possui venda. Confira a cobranca no PDV."
        )
    if _montar_itens_venda(db, tenant_id, atendimento):
        raise HTTPException(
            422,
            "Ha valores a cobrar neste atendimento. Confira os servicos e o taxi dog.",
        )
    atendimento.ocorrencias = [
        *(getattr(atendimento, "ocorrencias", None) or []),
        {
            "id": str(uuid4()),
            "tipo": TIPO_ENTREGA_SEM_COBRANCA,
            "gravidade": "baixa",
            "descricao": f"Entrega sem cobranca (valor zero): {motivo}",
            "created_by": user_id,
            "created_at": datetime.now().isoformat(),
            "system_generated": True,
        },
    ]
