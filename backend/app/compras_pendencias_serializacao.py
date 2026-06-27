"""Persistencia auxiliar e serializacao das pendencias de compras."""

from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from .compras_pendencias_models import (
    CompraPendenciaFornecedor,
    CompraPendenciaFornecedorHistorico,
    CompraPendenciaFornecedorItem,
)
from .compras_pendencias_utils import _normalizar_texto, _round_quantity


def _adicionar_historico(
    pendencia: CompraPendenciaFornecedor,
    tipo: str,
    user_id: int,
    observacao: Optional[str] = None,
    status_anterior: Optional[str] = None,
    status_novo: Optional[str] = None,
) -> None:
    pendencia.historico.append(
        CompraPendenciaFornecedorHistorico(
            tenant_id=pendencia.tenant_id,
            tipo=tipo,
            observacao=_normalizar_texto(observacao),
            status_anterior=status_anterior,
            status_novo=status_novo,
            user_id=user_id,
        )
    )


def _sincronizar_itens_pendencia(
    db: Session,
    pendencia: CompraPendenciaFornecedor,
    itens: List[Dict[str, Any]],
) -> None:
    if pendencia.id:
        db.query(CompraPendenciaFornecedorItem).filter(
            CompraPendenciaFornecedorItem.pendencia_id == pendencia.id,
            CompraPendenciaFornecedorItem.tenant_id == pendencia.tenant_id,
        ).delete(synchronize_session=False)

    for row in itens:
        item = row["item"]
        div = row["divergencia"]
        pendencia.itens.append(
            CompraPendenciaFornecedorItem(
                tenant_id=pendencia.tenant_id,
                nota_entrada_item_id=item.id,
                produto_id=item.produto_id,
                codigo_produto=item.codigo_produto,
                descricao=item.descricao,
                unidade=item.unidade,
                quantidade_nf=div["quantidade_nf"],
                quantidade_recebida=div["quantidade_conferida"],
                quantidade_faltante=div["quantidade_faltante"],
                quantidade_avariada=div["quantidade_avariada"],
                valor_unitario=div["valor_unitario"],
                valor_total_divergente=div["valor_total_divergente"],
                status_conferencia=div["status_conferencia"],
                acao_sugerida=div["acao_sugerida"],
                observacao=div["observacao"],
            )
        )


def _serializar_historico(item: CompraPendenciaFornecedorHistorico) -> Dict[str, Any]:
    usuario = getattr(item, "user", None)
    return {
        "id": item.id,
        "tipo": item.tipo,
        "observacao": item.observacao,
        "status_anterior": item.status_anterior,
        "status_novo": item.status_novo,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "usuario": getattr(usuario, "nome", None) or getattr(usuario, "email", None),
    }


def _serializar_item(item: CompraPendenciaFornecedorItem) -> Dict[str, Any]:
    return {
        "id": item.id,
        "nota_entrada_item_id": item.nota_entrada_item_id,
        "produto_id": item.produto_id,
        "codigo_produto": item.codigo_produto,
        "descricao": item.descricao,
        "unidade": item.unidade,
        "quantidade_nf": item.quantidade_nf,
        "quantidade_recebida": item.quantidade_recebida,
        "quantidade_faltante": item.quantidade_faltante,
        "quantidade_avariada": item.quantidade_avariada,
        "valor_unitario": item.valor_unitario,
        "valor_total_divergente": item.valor_total_divergente,
        "status_conferencia": item.status_conferencia,
        "acao_sugerida": item.acao_sugerida,
        "observacao": item.observacao,
        "resolvido": item.resolvido,
    }


def _serializar_pendencia(
    pendencia: CompraPendenciaFornecedor,
    incluir_itens: bool = False,
    incluir_historico: bool = False,
) -> Dict[str, Any]:
    itens = list(getattr(pendencia, "itens", []) or [])
    resumo = {
        "itens": len(itens),
        "faltante": _round_quantity(
            sum(float(item.quantidade_faltante or 0) for item in itens)
        ),
        "avariada": _round_quantity(
            sum(float(item.quantidade_avariada or 0) for item in itens)
        ),
        "valor_estimado": round(
            sum(float(item.valor_total_divergente or 0) for item in itens), 2
        ),
    }
    dados = {
        "id": pendencia.id,
        "codigo": pendencia.codigo,
        "status": pendencia.status,
        "origem": pendencia.origem,
        "tipo": pendencia.tipo,
        "titulo": pendencia.titulo,
        "resumo": pendencia.resumo,
        "resumo_numerico": resumo,
        "fornecedor_id": pendencia.fornecedor_id,
        "fornecedor_nome": pendencia.fornecedor_nome,
        "fornecedor_cnpj": pendencia.fornecedor_cnpj,
        "nota_entrada_id": pendencia.nota_entrada_id,
        "pedido_compra_id": pendencia.pedido_compra_id,
        "numero_nota": pendencia.numero_nota,
        "numero_pedido": pendencia.numero_pedido,
        "prazo_previsto": pendencia.prazo_previsto.isoformat()
        if pendencia.prazo_previsto
        else None,
        "email_destinatario": pendencia.email_destinatario,
        "email_assunto": pendencia.email_assunto,
        "email_mensagem": pendencia.email_mensagem,
        "email_enviado_em": pendencia.email_enviado_em.isoformat()
        if pendencia.email_enviado_em
        else None,
        "pdf_gerado_em": pendencia.pdf_gerado_em.isoformat()
        if pendencia.pdf_gerado_em
        else None,
        "resolvida_em": pendencia.resolvida_em.isoformat()
        if pendencia.resolvida_em
        else None,
        "resolucao_observacao": pendencia.resolucao_observacao,
        "created_at": pendencia.created_at.isoformat()
        if pendencia.created_at
        else None,
        "updated_at": pendencia.updated_at.isoformat()
        if pendencia.updated_at
        else None,
    }
    if incluir_itens:
        dados["itens"] = [_serializar_item(item) for item in itens]
    if incluir_historico:
        dados["historico"] = [
            _serializar_historico(item) for item in (pendencia.historico or [])
        ]
    return dados


def _buscar_pendencia(
    db: Session, tenant_id, pendencia_id: int
) -> CompraPendenciaFornecedor:
    pendencia = (
        db.query(CompraPendenciaFornecedor)
        .options(
            joinedload(CompraPendenciaFornecedor.itens),
            joinedload(CompraPendenciaFornecedor.historico).joinedload(
                CompraPendenciaFornecedorHistorico.user
            ),
        )
        .filter(
            CompraPendenciaFornecedor.id == pendencia_id,
            CompraPendenciaFornecedor.tenant_id == tenant_id,
        )
        .first()
    )
    if not pendencia:
        raise HTTPException(status_code=404, detail="Pendencia nao encontrada.")
    return pendencia
