from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.notas_entrada.conferencia import (
    CONFERENCIA_STATUS_COM_DIVERGENCIA,
    CONFERENCIA_STATUS_NAO_INICIADA,
    CONFERENCIA_STATUS_SEM_DIVERGENCIA,
    _normalizar_texto_curto,
    _obter_acao_conferencia,
    _resumir_conferencia_nota,
    _round_quantity,
    _serializar_conferencia_item,
)
from app.notas_entrada.schemas import ConferenciaNotaPayload
from app.produtos_models import NotaEntrada

router = APIRouter()


@router.post("/{nota_id}/conferencia")
def salvar_conferencia_nota(
    nota_id: int,
    payload: ConferenciaNotaPayload,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Salva a conferência física da NF, assumindo tudo OK por padrão e ajustando apenas exceções."""
    current_user, tenant_id = user_and_tenant

    nota = (
        db.query(NotaEntrada)
        .options(joinedload(NotaEntrada.itens))
        .filter(NotaEntrada.id == nota_id, NotaEntrada.tenant_id == tenant_id)
        .first()
    )

    if not nota:
        raise HTTPException(status_code=404, detail="Nota não encontrada")

    itens_por_id = {item.id: item for item in nota.itens}
    payload_por_id = {item.item_id: item for item in payload.itens}

    itens_invalidos = [
        item_id for item_id in payload_por_id if item_id not in itens_por_id
    ]
    if itens_invalidos:
        raise HTTPException(
            status_code=400,
            detail=f"Itens de conferência inválidos: {', '.join(str(item_id) for item_id in itens_invalidos)}",
        )

    for item in nota.itens:
        quantidade_nf = _round_quantity(item.quantidade)
        payload_item = payload_por_id.get(item.id)

        quantidade_conferida = (
            item.quantidade_conferida
            if item.quantidade_conferida is not None
            else quantidade_nf
        )
        quantidade_avariada = item.quantidade_avariada or 0
        observacao_conferencia = item.observacao_conferencia
        acao_sugerida = item.acao_sugerida

        if payload_item:
            quantidade_conferida = _round_quantity(payload_item.quantidade_conferida)
            quantidade_avariada = _round_quantity(payload_item.quantidade_avariada)
            observacao_conferencia = payload_item.observacao_conferencia
            acao_sugerida = payload_item.acao_sugerida

        if quantidade_conferida < 0 or quantidade_avariada < 0:
            raise HTTPException(
                status_code=400,
                detail=f"Quantidades inválidas para o item {item.numero_item}.",
            )

        if quantidade_conferida > quantidade_nf:
            raise HTTPException(
                status_code=400,
                detail=f"A quantidade conferida do item {item.numero_item} não pode ser maior que a quantidade da NF.",
            )

        if quantidade_conferida + quantidade_avariada > quantidade_nf:
            raise HTTPException(
                status_code=400,
                detail=f"A soma de conferida + avariada do item {item.numero_item} não pode ultrapassar a quantidade da NF.",
            )

        tem_divergencia = (
            quantidade_conferida + quantidade_avariada
        ) < quantidade_nf or quantidade_avariada > 0

        item.quantidade_conferida = quantidade_conferida
        item.quantidade_avariada = quantidade_avariada
        item.observacao_conferencia = _normalizar_texto_curto(observacao_conferencia)
        item.acao_sugerida = _obter_acao_conferencia(acao_sugerida, tem_divergencia)

    nota.conferencia_observacoes = _normalizar_texto_curto(payload.observacao_geral)
    nota.conferencia_realizada_em = datetime.utcnow()

    resumo = _resumir_conferencia_nota(nota)
    nota.conferencia_status = (
        CONFERENCIA_STATUS_COM_DIVERGENCIA
        if resumo["itens_com_divergencia"] > 0
        else CONFERENCIA_STATUS_SEM_DIVERGENCIA
    )
    nota.conferencia_user_id = current_user.id

    db.commit()

    return {
        "message": "Conferência salva com sucesso",
        "nota_id": nota.id,
        "conferencia": _resumir_conferencia_nota(nota),
    }


@router.post("/{nota_id}/conferencia/desfazer")
def desfazer_conferencia_nota(
    nota_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Limpa a conferencia registrada da NF antes do processamento do estoque."""
    current_user, tenant_id = user_and_tenant

    nota = (
        db.query(NotaEntrada)
        .options(joinedload(NotaEntrada.itens))
        .filter(NotaEntrada.id == nota_id, NotaEntrada.tenant_id == tenant_id)
        .first()
    )

    if not nota:
        raise HTTPException(status_code=404, detail="Nota não encontrada")

    if nota.entrada_estoque_realizada or nota.status == "processada":
        raise HTTPException(
            status_code=400,
            detail="Nao e possivel desfazer a conferencia apos processar a entrada no estoque.",
        )

    for item in nota.itens:
        item.quantidade_conferida = None
        item.quantidade_avariada = 0
        item.observacao_conferencia = None
        item.acao_sugerida = "sem_acao"

    nota.conferencia_observacoes = None
    nota.conferencia_realizada_em = None
    nota.conferencia_status = CONFERENCIA_STATUS_NAO_INICIADA
    nota.conferencia_user_id = None

    db.commit()

    return {
        "message": "Conferencia desfeita com sucesso",
        "nota_id": nota.id,
        "conferencia": _resumir_conferencia_nota(nota),
    }


@router.get("/{nota_id}/devolucao-draft")
def gerar_rascunho_nf_devolucao(
    nota_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Gera um rascunho de NF de devolução com base nos itens avariados da conferência."""
    _, tenant_id = user_and_tenant

    nota = (
        db.query(NotaEntrada)
        .options(joinedload(NotaEntrada.itens))
        .filter(NotaEntrada.id == nota_id, NotaEntrada.tenant_id == tenant_id)
        .first()
    )

    if not nota:
        raise HTTPException(status_code=404, detail="Nota não encontrada")

    itens_devolucao = []
    valor_total_estimado = 0.0

    for item in nota.itens:
        conferencia_item = _serializar_conferencia_item(item)
        quantidade_devolucao = conferencia_item["quantidade_para_devolucao"]
        if quantidade_devolucao <= 0:
            continue

        valor_total_item = round(
            quantidade_devolucao * float(item.valor_unitario or 0), 2
        )
        valor_total_estimado += valor_total_item
        itens_devolucao.append(
            {
                "item_id": item.id,
                "numero_item_nf": item.numero_item,
                "codigo_produto": item.codigo_produto,
                "descricao": item.descricao,
                "unidade": item.unidade,
                "quantidade_devolucao": quantidade_devolucao,
                "valor_unitario": float(item.valor_unitario or 0),
                "valor_total": valor_total_item,
                "observacao_conferencia": conferencia_item["observacao_conferencia"],
            }
        )

    observacao_padrao = (
        f"Rascunho de NF de devolução referente à NF de entrada {nota.numero_nota}. "
        "Gerado a partir das divergências por avaria registradas na conferência física."
    )

    return {
        "disponivel": len(itens_devolucao) > 0,
        "nota_entrada_id": nota.id,
        "numero_nota_origem": nota.numero_nota,
        "fornecedor_nome": nota.fornecedor_nome,
        "fornecedor_cnpj": nota.fornecedor_cnpj,
        "data_emissao_origem": nota.data_emissao.isoformat()
        if nota.data_emissao
        else None,
        "itens": itens_devolucao,
        "quantidade_itens": len(itens_devolucao),
        "valor_total_estimado": round(valor_total_estimado, 2),
        "observacao_sugerida": observacao_padrao,
        "message": (
            "Rascunho gerado com sucesso"
            if itens_devolucao
            else "Nenhuma divergência com avaria foi encontrada para gerar NF de devolução"
        ),
    }
