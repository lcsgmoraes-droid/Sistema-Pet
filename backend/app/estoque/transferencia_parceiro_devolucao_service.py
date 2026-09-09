"""Devolucoes parciais por produto, usando os movimentos como fonte do saldo."""

from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException
from sqlalchemy.orm import joinedload

from app.estoque.service import EstoqueService
from app.produtos_models import EstoqueMovimentacao, Produto

CENTAVO = Decimal("0.01")
QUANTIDADE = Decimal("0.001")
MOTIVOS_SAIDA = ("transf_parceiro", "transferencia_parceiro")
MOTIVO_DEVOLUCAO = "transf_dev"
REFERENCIA_DEVOLUCAO = "transf_devolucao"


def _decimal(valor):
    return Decimal(str(valor or 0))


def _moeda(valor):
    return _decimal(valor).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def resumir_movimentos_devolucao(movimentos):
    """Agrupa repeticoes do mesmo produto e desconta devolucoes anteriores."""
    produtos = {}
    devolucoes = []
    for mov in movimentos:
        produto_id = int(mov.produto_id)
        item = produtos.setdefault(
            produto_id,
            {
                "produto_id": produto_id,
                "produto_nome": getattr(mov.produto, "nome", None)
                or f"Produto #{produto_id}",
                "codigo": getattr(mov.produto, "codigo", None),
                "quantidade": Decimal(0),
                "quantidade_devolvida": Decimal(0),
                "valor_total": Decimal(0),
                "valor_devolvido": Decimal(0),
            },
        )
        quantidade = _decimal(mov.quantidade)
        valor = (
            _decimal(mov.valor_total)
            if mov.valor_total is not None
            else quantidade * _decimal(mov.custo_unitario)
        )
        if mov.tipo == "saida" and mov.motivo in MOTIVOS_SAIDA:
            item["quantidade"] += quantidade
            item["valor_total"] += valor
        elif mov.tipo == "entrada" and mov.motivo == MOTIVO_DEVOLUCAO:
            item["quantidade_devolvida"] += quantidade
            item["valor_devolvido"] += valor
            devolucoes.append(
                {
                    "movimentacao_id": mov.id,
                    "produto_nome": item["produto_nome"],
                    "quantidade": float(quantidade),
                    "valor_total": float(_moeda(valor)),
                    "registrado_em": mov.created_at,
                    "observacao": mov.observacao,
                }
            )

    itens = []
    for item in produtos.values():
        if item["quantidade"] <= 0:
            continue
        item["quantidade_disponivel"] = max(
            item["quantidade"] - item["quantidade_devolvida"], Decimal(0)
        )
        itens.append(
            {
                chave: float(valor) if isinstance(valor, Decimal) else valor
                for chave, valor in item.items()
            }
        )
    return {"itens": itens, "devolucoes": list(reversed(devolucoes))}


def buscar_resumos_devolucao(db, *, tenant_id, conta_ids):
    if not conta_ids:
        return {}
    movimentos = (
        db.query(EstoqueMovimentacao)
        .options(joinedload(EstoqueMovimentacao.produto))
        .filter(
            EstoqueMovimentacao.tenant_id == str(tenant_id),
            EstoqueMovimentacao.referencia_id.in_(conta_ids),
            EstoqueMovimentacao.motivo.in_((*MOTIVOS_SAIDA, MOTIVO_DEVOLUCAO)),
        )
        .order_by(EstoqueMovimentacao.id.asc())
        .all()
    )
    por_conta = defaultdict(list)
    for mov in movimentos:
        por_conta[mov.referencia_id].append(mov)
    return {
        conta_id: resumir_movimentos_devolucao(itens)
        for conta_id, itens in por_conta.items()
    }


def preparar_devolucao(itens_disponiveis, itens_solicitados):
    disponiveis = {item["produto_id"]: item for item in itens_disponiveis}
    selecionados = set()
    preparados = []
    for pedido in itens_solicitados:
        produto_id = pedido.produto_id
        item = disponiveis.get(produto_id)
        if item is None or produto_id in selecionados:
            raise HTTPException(400, "Produto invalido ou repetido na devolucao.")
        selecionados.add(produto_id)
        quantidade = _decimal(pedido.quantidade)
        if (
            not quantidade.is_finite()
            or quantidade <= 0
            or quantidade != quantidade.quantize(QUANTIDADE)
        ):
            raise HTTPException(
                400, "Informe uma quantidade positiva com ate 3 casas decimais."
            )
        if quantidade > _decimal(item["quantidade_disponivel"]):
            raise HTTPException(
                400,
                f"Quantidade a devolver ultrapassa o restante de {item['produto_nome']}.",
            )
        # Arredondamento acumulado: a ultima devolucao fecha exatamente o total original.
        total_acumulado = _moeda(
            _decimal(item["valor_total"])
            * (_decimal(item["quantidade_devolvida"]) + quantidade)
            / _decimal(item["quantidade"])
        )
        valor = total_acumulado - _moeda(item["valor_devolvido"])
        if valor < 0:
            raise HTTPException(
                400, "O valor das devolucoes anteriores precisa ser conferido."
            )
        preparados.append(
            {
                "produto_id": produto_id,
                "produto_nome": item["produto_nome"],
                "quantidade": float(quantidade),
                "valor_total": valor,
                "custo_unitario": _decimal(item["valor_total"])
                / _decimal(item["quantidade"]),
            }
        )
    if not preparados:
        raise HTTPException(
            400, "Informe a quantidade de pelo menos um produto a devolver."
        )
    return preparados, sum((item["valor_total"] for item in preparados), Decimal(0))


def registrar_entrada_devolucao(db, *, conta, itens, user_id, tenant_id, observacao):
    produto_ids = [item["produto_id"] for item in itens]
    produtos = (
        db.query(Produto)
        .filter(Produto.tenant_id == str(tenant_id), Produto.id.in_(produto_ids))
        .order_by(Produto.id.asc())
        .with_for_update()
        .populate_existing()
        .all()
    )
    if len(produtos) != len(set(produto_ids)):
        raise HTTPException(400, "Produto da devolucao nao encontrado nesta empresa.")
    movimentos = []
    for item in sorted(itens, key=lambda item: item["produto_id"]):
        resultado = EstoqueService.estornar_estoque(
            produto_id=item["produto_id"],
            quantidade=item["quantidade"],
            motivo=MOTIVO_DEVOLUCAO,
            referencia_id=conta.id,
            referencia_tipo=REFERENCIA_DEVOLUCAO,
            user_id=user_id,
            db=db,
            tenant_id=str(tenant_id),
            documento=conta.documento,
            observacao=observacao,
            custo_unitario_override=float(item["custo_unitario"]),
            valor_total_override=float(item["valor_total"]),
        )
        movimentos.append(resultado["movimentacao_id"])
    return movimentos
