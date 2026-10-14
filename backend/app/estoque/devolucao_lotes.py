"""Recompoe os lotes comprovados na saida original, sem executar um novo FIFO."""

import json
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from fastapi import HTTPException

from app.produtos_models import EstoqueMovimentacao, ProdutoLote
from app.utils.timezone import now_brasilia

_EPSILON = Decimal("0.000001")


def _inconsistente():
    raise HTTPException(
        status_code=409,
        detail=(
            "Os lotes originais ou as devolucoes anteriores nao tem saldo rastreavel. "
            "Concilie o estoque antes de devolver."
        ),
    )


def _quantidade(valor):
    try:
        quantidade = Decimal(str(valor))
    except (InvalidOperation, ValueError, TypeError):
        _inconsistente()
    if not quantidade.is_finite() or quantidade < 0:
        _inconsistente()
    return quantidade


def _composicao(movimento, *, permitir_sem_lote=False):
    bruto = getattr(movimento, "lotes_consumidos", None)
    try:
        composicao = json.loads(bruto) if isinstance(bruto, str) else bruto
    except (ValueError, TypeError):
        _inconsistente()
    if composicao is None:
        composicao = []
    if not isinstance(composicao, list):
        _inconsistente()
    resultado = defaultdict(Decimal)
    for parte in composicao:
        if not isinstance(parte, dict):
            _inconsistente()
        lote_id = parte.get("lote_id")
        if lote_id is None and permitir_sem_lote:
            pass
        elif not isinstance(lote_id, int) or isinstance(lote_id, bool) or lote_id <= 0:
            _inconsistente()
        quantidade = _quantidade(parte.get("quantidade"))
        if quantidade <= 0:
            _inconsistente()
        resultado[lote_id] += quantidade
    lote_principal = getattr(movimento, "lote_id", None)
    if lote_principal is not None:
        if (
            not isinstance(lote_principal, int)
            or isinstance(lote_principal, bool)
            or lote_principal <= 0
        ):
            _inconsistente()
        if resultado and set(resultado) != {lote_principal}:
            _inconsistente()
        if not resultado:
            resultado[lote_principal] = _quantidade(movimento.quantidade)
    return dict(resultado)


@dataclass
class PlanoDevolucaoLotes:
    produto_id: int
    tenant_id: object
    venda_id: int
    disponivel_por_item: dict
    lotes: dict


def _origens_por_item(
    itens, saidas_por_id, partes_por_saida, vendidos, tenant_id, venda_id
):
    origens = {}
    for item in itens:
        prova = getattr(item, "custo_original_saida", None)
        origem = None
        if isinstance(prova, dict):
            saida = saidas_por_id.get(prova.get("movimentacao_id"))
            if (
                saida is not None
                and prova.get("origem") == "baixa_estoque_venda"
                and prova.get("venda_id") == venda_id
                and prova.get("venda_item_id") == item.id
                and prova.get("produto_id") == item.produto_id
                and str(prova.get("tenant_estoque_id")) == str(tenant_id)
                and _quantidade(prova.get("quantidade")) == _quantidade(item.quantidade)
                and _quantidade(saida.quantidade) == _quantidade(item.quantidade)
            ):
                origem = dict(partes_por_saida[saida.id])
        lote_id = getattr(item, "lote_id", None)
        if lote_id is not None:
            if origem is not None and set(origem) != {lote_id}:
                _inconsistente()
            origem = {lote_id: _quantidade(item.quantidade)}
        if origem is None:
            if len(itens) == 1:
                origem = dict(vendidos)
            elif len(vendidos) == 1:
                origem = {next(iter(vendidos)): _quantidade(item.quantidade)}
            else:
                # O SKU repetido nao prova qual linha consumiu cada lote.
                _inconsistente()
        origens[item.id] = origem
    atribuido = defaultdict(Decimal)
    for partes in origens.values():
        for lote_id, qtd in partes.items():
            atribuido[lote_id] += qtd
    if set(atribuido) != set(vendidos) or any(
        abs(atribuido[lote_id] - qtd) > _EPSILON for lote_id, qtd in vendidos.items()
    ):
        _inconsistente()
    return origens


def _item_entrada(entrada, partes, origens):
    bruto = getattr(entrada, "lotes_consumidos", None)
    bruto = json.loads(bruto) if isinstance(bruto, str) else bruto
    ids = {parte.get("venda_item_id") for parte in bruto or []}
    if ids and None not in ids:
        if len(ids) != 1:
            _inconsistente()
        item_id = next(iter(ids))
        if (
            not isinstance(item_id, int)
            or isinstance(item_id, bool)
            or item_id not in origens
        ):
            _inconsistente()
        return item_id
    candidatas = [
        item_id for item_id, origem in origens.items() if set(partes).issubset(origem)
    ]
    if len(candidatas) != 1:
        _inconsistente()
    return candidatas[0]


def preparar_devolucao_lotes(
    db,
    *,
    produto_id,
    tenant_id,
    venda_id,
    saidas,
    itens_venda,
    quantidades_por_item,
    bloquear=False,
):
    """Valida o historico sem escrever. O registro bloqueia os lotes envolvidos.

    Saidas sem lotes continuam sem lotes. Se o item comprova um unico lote e a
    movimentacao antiga nao tem JSON, esse vinculo original serve de prova.
    Historicos parciais ou contraditorios nunca usam o FIFO atual como fallback.
    """
    vendidos = defaultdict(Decimal)
    lotes_itens = {getattr(item, "lote_id", None) for item in itens_venda}
    lote_unico = next(iter(lotes_itens)) if len(lotes_itens) == 1 else None
    partes_por_saida = {}
    saidas_por_id = {}
    for saida in sorted(saidas, key=lambda movimento: getattr(movimento, "id", 0)):
        total = _quantidade(saida.quantidade)
        if total <= 0:
            _inconsistente()
        partes = _composicao(saida)
        if not partes and lote_unico is not None:
            partes = {lote_unico: total}
        if partes:
            if abs(sum(partes.values(), Decimal("0")) - total) > _EPSILON:
                _inconsistente()
            for lote_id, qtd in partes.items():
                vendidos[lote_id] += qtd
        else:
            vendidos[None] += total
            partes = {None: total}
        saida_id = getattr(saida, "id", None)
        partes_por_saida[saida_id] = partes
        saidas_por_id[saida_id] = saida
    if any(lote_id not in vendidos for lote_id in lotes_itens if lote_id is not None):
        _inconsistente()
    ids_lotes = [lote_id for lote_id in vendidos if lote_id is not None]
    if not ids_lotes:
        return None
    origens = _origens_por_item(
        itens_venda, saidas_por_id, partes_por_saida, vendidos, tenant_id, venda_id
    )

    # As entradas novas gravam exatamente quais lotes foram recompostos.
    # Uma entrada legada sem essa prova so cabe na parte originalmente sem lote.
    entradas = (
        db.query(EstoqueMovimentacao)
        .filter(
            EstoqueMovimentacao.tenant_id == tenant_id,
            EstoqueMovimentacao.produto_id == produto_id,
            EstoqueMovimentacao.referencia_tipo == "venda",
            EstoqueMovimentacao.referencia_id == venda_id,
            EstoqueMovimentacao.tipo == "entrada",
            EstoqueMovimentacao.motivo == "devolucao",
            EstoqueMovimentacao.status != "cancelado",
        )
        .all()
    )
    devolvidos = {item_id: defaultdict(Decimal) for item_id in origens}
    for entrada in entradas:
        total = _quantidade(entrada.quantidade)
        partes = _composicao(entrada, permitir_sem_lote=True)
        total_lotes = sum(partes.values(), Decimal("0"))
        if total_lotes > total + _EPSILON:
            _inconsistente()
        if total > total_lotes:
            partes[None] = partes.get(None, Decimal("0")) + total - total_lotes
        item_id = _item_entrada(entrada, partes, origens)
        for lote_id, qtd in partes.items():
            devolvidos[item_id][lote_id] += qtd
    disponivel_por_item = {}
    for item_id, origem in origens.items():
        if any(
            qtd > origem.get(lote_id, 0) + _EPSILON
            for lote_id, qtd in devolvidos[item_id].items()
        ):
            _inconsistente()
        disponivel_por_item[item_id] = {
            lote_id: max(Decimal("0"), qtd - devolvidos[item_id][lote_id])
            for lote_id, qtd in origem.items()
        }
    for item_id, quantidade in quantidades_por_item.items():
        if (
            item_id not in disponivel_por_item
            or _quantidade(quantidade)
            > sum(disponivel_por_item[item_id].values(), Decimal("0")) + _EPSILON
        ):
            _inconsistente()

    consulta = (
        db.query(ProdutoLote)
        .filter(
            ProdutoLote.tenant_id == tenant_id,
            ProdutoLote.produto_id == produto_id,
            ProdutoLote.id.in_(ids_lotes),
        )
        .order_by(ProdutoLote.id)
    )
    if bloquear:
        consulta = consulta.with_for_update().populate_existing()
    lotes = {lote.id: lote for lote in consulta.all()}
    if set(lotes) != set(ids_lotes):
        _inconsistente()
    for lote in lotes.values():
        _quantidade(lote.quantidade_disponivel)
    return PlanoDevolucaoLotes(
        produto_id, tenant_id, venda_id, disponivel_por_item, lotes
    )


def recompor_lotes_devolucao(db, plano, item_id, quantidade, movimentacao_id):
    """Aplica o plano na transacao do estoque/caixa e registra sua composicao."""
    if plano is None:
        return []
    restante = _quantidade(quantidade)
    disponivel = plano.disponivel_por_item.get(item_id, {})
    if restante <= 0 or restante > sum(disponivel.values(), Decimal("0")) + _EPSILON:
        _inconsistente()
    composicao = []
    for lote_id, saldo in disponivel.items():
        qtd = min(saldo, restante)
        if qtd <= 0:
            continue
        disponivel[lote_id] -= qtd
        restante -= qtd
        if lote_id is None:
            composicao.append(
                {"lote_id": None, "venda_item_id": item_id, "quantidade": float(qtd)}
            )
            continue
        lote = plano.lotes[lote_id]
        saldo_anterior = _quantidade(lote.quantidade_disponivel)
        lote.quantidade_disponivel = float(saldo_anterior + qtd)
        # Nao liberar um lote bloqueado/vencido ao recompor seu saldo fisico.
        if lote.status == "esgotado":
            validade = lote.data_validade
            lote.status = (
                "vencido"
                if validade and validade.date() < now_brasilia().date()
                else "ativo"
            )
        composicao.append(
            {
                "lote_id": lote_id,
                "venda_item_id": item_id,
                "nome_lote": lote.nome_lote,
                "quantidade": float(qtd),
                "saldo_anterior": float(saldo_anterior),
            }
        )
    if restante > _EPSILON:
        _inconsistente()
    entrada = (
        db.query(EstoqueMovimentacao)
        .filter(
            EstoqueMovimentacao.id == movimentacao_id,
            EstoqueMovimentacao.tenant_id == plano.tenant_id,
            EstoqueMovimentacao.produto_id == plano.produto_id,
            EstoqueMovimentacao.referencia_id == plano.venda_id,
            EstoqueMovimentacao.referencia_tipo == "venda",
            EstoqueMovimentacao.tipo == "entrada",
            EstoqueMovimentacao.motivo == "devolucao",
        )
        .first()
    )
    if (
        entrada is None
        or abs(_quantidade(entrada.quantidade) - _quantidade(quantidade)) > _EPSILON
    ):
        _inconsistente()
    entrada.lotes_consumidos = json.dumps(composicao) if composicao else None
    # A quantidade principal so e atribuida se toda a entrada pertence a um lote.
    entrada.lote_id = (
        composicao[0]["lote_id"]
        if len(composicao) == 1
        and composicao[0]["lote_id"] is not None
        and abs(Decimal(str(composicao[0]["quantidade"])) - _quantidade(quantidade))
        <= _EPSILON
        else None
    )
    db.flush()
    return composicao
