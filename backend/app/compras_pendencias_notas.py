"""Helpers de notas de entrada para pendencias de compras."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload

from .models import Cliente
from .produtos_models import (
    NotaEntrada,
    NotaEntradaItem,
    PedidoCompra,
    PedidoCompraNotaEntrada,
)
from .compras_pendencias_utils import (
    _formatar_moeda,
    _formatar_qtd,
    _normalizar_texto,
    _round_quantity,
)


def _quantidades_conferencia_item(item: NotaEntradaItem) -> Dict[str, float]:
    quantidade_nf = _round_quantity(item.quantidade)
    quantidade_conferida = item.quantidade_conferida
    if quantidade_conferida is None:
        quantidade_conferida = quantidade_nf
    quantidade_conferida = max(
        0.0, min(_round_quantity(quantidade_conferida), quantidade_nf)
    )

    quantidade_avariada = max(0.0, _round_quantity(item.quantidade_avariada))
    max_avariada = max(quantidade_nf - quantidade_conferida, 0.0)
    quantidade_avariada = min(quantidade_avariada, max_avariada)
    quantidade_faltante = max(
        quantidade_nf - quantidade_conferida - quantidade_avariada, 0.0
    )

    return {
        "quantidade_nf": quantidade_nf,
        "quantidade_conferida": quantidade_conferida,
        "quantidade_avariada": quantidade_avariada,
        "quantidade_faltante": _round_quantity(quantidade_faltante),
    }


def _status_conferencia_item(quantidades: Dict[str, float]) -> str:
    tem_avaria = quantidades["quantidade_avariada"] > 0
    tem_falta = quantidades["quantidade_faltante"] > 0
    if tem_avaria and tem_falta:
        return "falta_avaria"
    if tem_avaria:
        return "avaria"
    if tem_falta:
        return "falta"
    return "ok"


def _divergencia_item(item: NotaEntradaItem) -> Dict[str, Any]:
    quantidades = _quantidades_conferencia_item(item)
    status_conferencia = _status_conferencia_item(quantidades)
    valor_unitario = float(item.valor_unitario or 0)
    quantidade_divergente = (
        quantidades["quantidade_faltante"] + quantidades["quantidade_avariada"]
    )
    return {
        **quantidades,
        "status_conferencia": status_conferencia,
        "tem_divergencia": status_conferencia != "ok",
        "valor_unitario": valor_unitario,
        "valor_total_divergente": round(quantidade_divergente * valor_unitario, 2),
        "acao_sugerida": item.acao_sugerida
        or ("contatar_fornecedor" if status_conferencia != "ok" else "sem_acao"),
        "observacao": _normalizar_texto(item.observacao_conferencia),
    }


def _buscar_nota(db: Session, tenant_id, nota_id: int) -> NotaEntrada:
    nota = (
        db.query(NotaEntrada)
        .options(
            joinedload(NotaEntrada.itens).joinedload(NotaEntradaItem.produto),
            joinedload(NotaEntrada.pedidos_compra_vinculos).joinedload(
                PedidoCompraNotaEntrada.pedido
            ),
        )
        .filter(NotaEntrada.id == nota_id, NotaEntrada.tenant_id == tenant_id)
        .first()
    )
    if not nota:
        raise HTTPException(status_code=404, detail="NF de entrada nao encontrada.")
    return nota


def _pedido_principal_da_nota(
    db: Session, nota: NotaEntrada, tenant_id
) -> Optional[PedidoCompra]:
    vinculos = list(getattr(nota, "pedidos_compra_vinculos", []) or [])
    for vinculo in vinculos:
        if getattr(vinculo, "pedido", None):
            return vinculo.pedido

    if nota.id:
        return (
            db.query(PedidoCompra)
            .filter(
                PedidoCompra.nota_entrada_id == nota.id,
                PedidoCompra.tenant_id == tenant_id,
            )
            .order_by(desc(PedidoCompra.id))
            .first()
        )
    return None


def _buscar_fornecedor(db: Session, nota: NotaEntrada, tenant_id) -> Optional[Cliente]:
    if not nota.fornecedor_id:
        return None
    return (
        db.query(Cliente)
        .filter(Cliente.id == nota.fornecedor_id, Cliente.tenant_id == tenant_id)
        .first()
    )


def _itens_divergentes(nota: NotaEntrada) -> List[Dict[str, Any]]:
    itens = []
    for item in getattr(nota, "itens", []) or []:
        divergencia = _divergencia_item(item)
        if divergencia["tem_divergencia"]:
            itens.append({"item": item, "divergencia": divergencia})
    return itens


def _resumo_pendencia(itens: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_faltante = sum(row["divergencia"]["quantidade_faltante"] for row in itens)
    total_avariada = sum(row["divergencia"]["quantidade_avariada"] for row in itens)
    valor = sum(row["divergencia"]["valor_total_divergente"] for row in itens)
    return {
        "itens": len(itens),
        "faltante": _round_quantity(total_faltante),
        "avariada": _round_quantity(total_avariada),
        "valor_estimado": round(valor, 2),
    }


def _montar_assunto(nota: NotaEntrada, pedido: Optional[PedidoCompra]) -> str:
    pedido_txt = f" - Pedido {pedido.numero_pedido}" if pedido else ""
    return f"Divergencias na NF {nota.numero_nota}{pedido_txt}"


def _montar_mensagem(
    nota: NotaEntrada,
    pedido: Optional[PedidoCompra],
    itens: List[Dict[str, Any]],
    prazo_previsto: Optional[datetime] = None,
) -> str:
    resumo = _resumo_pendencia(itens)
    linhas = [
        f"Ola, {nota.fornecedor_nome}.",
        "",
        "Identificamos divergencias durante a conferencia da mercadoria.",
        f"NF: {nota.numero_nota} | Emissao: {nota.data_emissao.strftime('%d/%m/%Y') if nota.data_emissao else '-'}",
    ]
    if pedido:
        linhas.append(f"Pedido de compra: {pedido.numero_pedido}")
    linhas.extend(
        [
            f"Itens com divergencia: {resumo['itens']}",
            f"Quantidade faltante: {_formatar_qtd(resumo['faltante'])}",
            f"Quantidade avariada: {_formatar_qtd(resumo['avariada'])}",
            f"Valor estimado das divergencias: {_formatar_moeda(resumo['valor_estimado'])}",
            "",
            "Itens:",
        ]
    )
    for row in itens:
        item = row["item"]
        div = row["divergencia"]
        linhas.append(
            "- "
            f"{item.descricao} | NF: {_formatar_qtd(div['quantidade_nf'])} | "
            f"recebido: {_formatar_qtd(div['quantidade_conferida'])} | "
            f"faltante: {_formatar_qtd(div['quantidade_faltante'])} | "
            f"avariado: {_formatar_qtd(div['quantidade_avariada'])}"
        )
        if div.get("observacao"):
            linhas.append(f"  Observacao: {div['observacao']}")
    linhas.extend(
        [
            "",
            "Pode nos orientar como devemos proceder para resolver essa pendencia?",
        ]
    )
    if prazo_previsto:
        linhas.append(
            f"Prazo interno previsto para retorno: {prazo_previsto.strftime('%d/%m/%Y')}."
        )
    linhas.extend(["", "Obrigado."])
    return "\n".join(linhas)
