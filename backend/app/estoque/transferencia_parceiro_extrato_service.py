"""Monta um extrato cronologico das transferencias e respectivas baixas."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
import re
from typing import Any, Iterable

from app.estoque.transferencia_parceiro_documents import (
    _saldo_conta_receber,
    _status_transferencia_parceiro,
)
from app.estoque.transferencia_parceiro_extrato_schemas import (
    TransferenciaParceiroExtratoItem,
    TransferenciaParceiroExtratoResponse,
    TransferenciaParceiroExtratoTotais,
)
from app.estoque.transferencia_parceiro_support import (
    _detectar_modo_baixa_transferencia,
    _texto_limpo,
)

_DATA_NO_HISTORICO = re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b")
_ORDEM_TIPO = {
    "divida": 0,
    "pagamento": 1,
    "acerto": 1,
    "devolucao": 1,
    "ajuste": 2,
    "cancelamento": 3,
}


def _numero(valor: Any) -> float:
    return round(float(valor or 0), 2)


def _data_datetime(valor: datetime | None) -> date | None:
    return valor.date() if isinstance(valor, datetime) else None


def _data_devolucao(observacao: str | None, registrado_em: datetime | None) -> date:
    encontrado = _DATA_NO_HISTORICO.search(observacao or "")
    if encontrado:
        dia, mes, ano = (int(parte) for parte in encontrado.groups())
        try:
            return date(ano, mes, dia)
        except ValueError:
            pass
    return _data_datetime(registrado_em) or date.today()


def _timestamp_ordenacao(valor: datetime | None) -> float:
    if not valor:
        return 0
    try:
        return valor.timestamp()
    except (OSError, ValueError):
        return 0


def _item_produto(item: Any) -> dict[str, Any]:
    return {
        "produto_id": getattr(item, "produto_id", None),
        "produto_nome": getattr(item, "produto_nome", None)
        or f"Produto #{getattr(item, 'produto_id', '')}",
        "codigo": _texto_limpo(getattr(item, "codigo", None)),
        "quantidade": float(getattr(item, "quantidade", 0) or 0),
        "custo_unitario": float(getattr(item, "custo_unitario", 0) or 0),
        "valor_total": float(getattr(item, "valor_total", 0) or 0),
    }


def _agrupar_devolucoes(resumo: dict[str, Any]) -> list[dict[str, Any]]:
    grupos: dict[tuple[Any, ...], dict[str, Any]] = {}
    for devolucao in resumo.get("devolucoes", []) or []:
        registrado_em = devolucao.get("registrado_em")
        observacao = _texto_limpo(devolucao.get("observacao"))
        chave = (registrado_em, observacao)
        grupo = grupos.setdefault(
            chave,
            {
                "movimentacao_ids": [],
                "registrado_em": registrado_em,
                "observacao": observacao,
                "data": _data_devolucao(observacao, registrado_em),
                "valor_total": 0.0,
                "itens": [],
            },
        )
        grupo["movimentacao_ids"].append(int(devolucao["movimentacao_id"]))
        grupo["valor_total"] += float(devolucao.get("valor_total") or 0)
        quantidade = float(devolucao.get("quantidade") or 0)
        valor_total = float(devolucao.get("valor_total") or 0)
        grupo["itens"].append(
            {
                "produto_nome": devolucao.get("produto_nome") or "Produto devolvido",
                "quantidade": quantidade,
                "custo_unitario": valor_total / quantidade if quantidade else 0,
                "valor_total": valor_total,
            }
        )
    return list(grupos.values())


def _movimentos_conta(
    conta: Any,
    itens: Iterable[Any],
    resumo_devolucao: dict[str, Any],
) -> list[dict[str, Any]]:
    conta_id = int(conta.id)
    documento = _texto_limpo(getattr(conta, "documento", None)) or f"TRP-{conta_id:06d}"
    status, status_label = _status_transferencia_parceiro(conta)
    data_emissao = conta.data_emissao or _data_datetime(
        getattr(conta, "created_at", None)
    )
    if not data_emissao:
        data_emissao = date.today()
    valor_divida = _numero(getattr(conta, "valor_original", None) or conta.valor_final)
    saldo_documento = _saldo_conta_receber(conta)
    base = {
        "conta_receber_id": conta_id,
        "documento": documento,
        "saldo_documento": saldo_documento,
        "conta_status": status,
        "conta_status_label": status_label,
        "data_vencimento": getattr(conta, "data_vencimento", None),
    }
    movimentos: list[dict[str, Any]] = [
        {
            **base,
            "id": f"divida-{conta_id}",
            "tipo": "divida",
            "tipo_label": "Divida gerada",
            "data": data_emissao,
            "registrado_em": getattr(conta, "created_at", None),
            "descricao": f"Produtos retirados - {documento}",
            "debito": valor_divida,
            "credito": 0,
            "observacoes": _texto_limpo(getattr(conta, "observacoes", None)),
            "itens": [_item_produto(item) for item in itens],
        }
    ]

    credito_estruturado = 0.0
    for recebimento in list(getattr(conta, "recebimentos", None) or []):
        valor = _numero(recebimento.valor_recebido)
        credito_estruturado += valor
        modo, modo_label = _detectar_modo_baixa_transferencia(
            recebimento,
            observacoes_conta=getattr(conta, "observacoes", None),
        )
        tipo = "acerto" if modo == "acerto" else "pagamento"
        forma = getattr(recebimento, "forma_pagamento", None)
        movimentos.append(
            {
                **base,
                "id": f"recebimento-{int(recebimento.id)}",
                "tipo": tipo,
                "tipo_label": modo_label or "Pagamento recebido",
                "data": recebimento.data_recebimento,
                "registrado_em": getattr(recebimento, "created_at", None),
                "descricao": f"{modo_label or 'Pagamento recebido'} - {documento}",
                "debito": 0,
                "credito": valor,
                "forma_pagamento_nome": _texto_limpo(getattr(forma, "nome", None)),
                "observacoes": _texto_limpo(getattr(recebimento, "observacoes", None)),
                "itens": [],
            }
        )

    for devolucao in _agrupar_devolucoes(resumo_devolucao):
        valor = _numero(devolucao["valor_total"])
        credito_estruturado += valor
        primeiro_id = min(devolucao["movimentacao_ids"])
        movimentos.append(
            {
                **base,
                "id": f"devolucao-{primeiro_id}",
                "tipo": "devolucao",
                "tipo_label": "Produto devolvido",
                "data": devolucao["data"],
                "registrado_em": devolucao["registrado_em"],
                "descricao": f"Produtos devolvidos - {documento}",
                "debito": 0,
                "credito": valor,
                "observacoes": devolucao["observacao"],
                "itens": devolucao["itens"],
            }
        )

    credito_esperado = _numero(getattr(conta, "valor_recebido", 0))
    diferenca = _numero(credito_esperado - credito_estruturado)
    if abs(diferenca) >= 0.01:
        data_ajuste = (
            getattr(conta, "data_recebimento", None)
            or _data_datetime(getattr(conta, "updated_at", None))
            or data_emissao
        )
        movimentos.append(
            {
                **base,
                "id": f"ajuste-{conta_id}",
                "tipo": "ajuste",
                "tipo_label": "Baixa historica",
                "data": data_ajuste,
                "registrado_em": getattr(conta, "updated_at", None),
                "descricao": f"Baixa registrada no saldo - {documento}",
                "debito": abs(diferenca) if diferenca < 0 else 0,
                "credito": diferenca if diferenca > 0 else 0,
                "observacoes": (
                    "Lancamento de conciliacao criado para representar uma baixa antiga "
                    "que nao possui detalhe individual estruturado."
                ),
                "itens": [],
            }
        )

    if status == "cancelado":
        valor_cancelado = _numero(max(valor_divida - credito_esperado, 0))
        if valor_cancelado:
            data_cancelamento = (
                _data_datetime(getattr(conta, "updated_at", None)) or data_emissao
            )
            movimentos.append(
                {
                    **base,
                    "id": f"cancelamento-{conta_id}",
                    "tipo": "cancelamento",
                    "tipo_label": "Divida cancelada",
                    "data": data_cancelamento,
                    "registrado_em": getattr(conta, "updated_at", None),
                    "descricao": f"Cancelamento - {documento}",
                    "debito": 0,
                    "credito": valor_cancelado,
                    "observacoes": "Saldo retirado por cancelamento da transferencia.",
                    "itens": [],
                }
            )
    return movimentos


def montar_extrato_transferencia_parceiro(
    *,
    parceiro_id: int,
    contas: Iterable[Any],
    itens_por_conta: dict[int, list[Any]],
    resumos_devolucao: dict[int, dict[str, Any]],
    data_inicio: date | None = None,
    data_fim: date | None = None,
) -> TransferenciaParceiroExtratoResponse:
    contas = list(contas)
    movimentos: list[dict[str, Any]] = []
    for conta in contas:
        movimentos.extend(
            _movimentos_conta(
                conta,
                itens_por_conta.get(int(conta.id), []),
                resumos_devolucao.get(int(conta.id), {}),
            )
        )

    movimentos.sort(
        key=lambda item: (
            item["data"],
            _ORDEM_TIPO.get(item["tipo"], 9),
            _timestamp_ordenacao(item.get("registrado_em")),
            item["id"],
        )
    )

    saldo = 0.0
    saldo_anterior = 0.0
    exibidos: list[TransferenciaParceiroExtratoItem] = []
    total_debitos = 0.0
    total_creditos = 0.0
    for movimento in movimentos:
        dentro_inicio = not data_inicio or movimento["data"] >= data_inicio
        dentro_fim = not data_fim or movimento["data"] <= data_fim
        if data_inicio and movimento["data"] < data_inicio:
            saldo = _numero(saldo + movimento["debito"] - movimento["credito"])
            saldo_anterior = saldo
            continue
        if not dentro_fim:
            continue
        if dentro_inicio:
            saldo = _numero(saldo + movimento["debito"] - movimento["credito"])
            movimento["saldo"] = saldo
            total_debitos += movimento["debito"]
            total_creditos += movimento["credito"]
            exibidos.append(TransferenciaParceiroExtratoItem(**movimento))

    parceiro_nome = None
    if contas:
        parceiro = getattr(contas[0], "cliente", None)
        parceiro_nome = _texto_limpo(getattr(parceiro, "nome", None))

    em_aberto = sum(
        1
        for conta in contas
        if _status_transferencia_parceiro(conta)[0]
        in {"pendente", "parcial", "vencido"}
        and _saldo_conta_receber(conta) > 0
    )
    return TransferenciaParceiroExtratoResponse(
        parceiro_id=parceiro_id,
        parceiro_nome=parceiro_nome,
        items=list(reversed(exibidos)),
        totais=TransferenciaParceiroExtratoTotais(
            saldo_anterior=saldo_anterior,
            total_debitos=_numero(total_debitos),
            total_creditos=_numero(total_creditos),
            saldo_final=_numero(saldo),
            total_lancamentos=len(exibidos),
            total_documentos=len(contas),
            documentos_em_aberto=em_aberto,
        ),
    )
