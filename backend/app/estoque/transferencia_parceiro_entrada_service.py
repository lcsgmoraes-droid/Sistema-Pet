from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.bling_estoque_sync import sincronizar_bling_background
from app.financeiro_models import ContaPagar
from app.models import Cliente
from app.produtos_models import EstoqueMovimentacao, Produto


CENTAVO = Decimal("0.01")
MOTIVO_ENTRADA_PARCEIRO = "transf_parceiro_entrada"


def _texto_limpo(valor) -> str | None:
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto or None


def _decimal_monetario(valor) -> Decimal:
    if valor is None:
        return Decimal("0.00")
    return Decimal(str(valor)).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def _gerar_documento_entrada_parceiro() -> str:
    return f"TRP-ENT-{datetime.now().strftime('%Y%m%d%H%M%S')}"


def _validar_produto_entrada_parceiro(produto, *, entrar_estoque: bool) -> None:
    if entrar_estoque and getattr(produto, "is_parent", False):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Produto '{produto.nome}' possui variacoes. "
                "Selecione a variacao individual para entrar no estoque."
            ),
        )
    if (
        entrar_estoque
        and getattr(produto, "tipo_produto", None) == "KIT"
        and getattr(produto, "tipo_kit", None) == "VIRTUAL"
    ):
        raise HTTPException(
            status_code=400,
            detail=f"Produto '{produto.nome}' e um KIT VIRTUAL e nao recebe estoque manual.",
        )


def preparar_itens_entrada_parceiro(
    produtos_cache: dict[int, object],
    itens,
    *,
    entrar_estoque: bool = True,
) -> tuple[list[dict], Decimal]:
    itens_validos = [item for item in (itens or []) if float(item.quantidade or 0) > 0]
    if not itens_validos:
        raise HTTPException(
            status_code=400,
            detail="Informe ao menos um item com quantidade maior que zero.",
        )

    processados: list[dict] = []
    total_divida = Decimal("0.00")

    for item in itens_validos:
        produto_id = int(item.produto_id)
        produto = produtos_cache.get(produto_id)
        if not produto:
            raise HTTPException(
                status_code=404,
                detail=f"Produto ID {produto_id} nao encontrado.",
            )
        _validar_produto_entrada_parceiro(produto, entrar_estoque=entrar_estoque)

        quantidade = Decimal(str(float(item.quantidade or 0)))
        total_informado = (
            _decimal_monetario(item.valor_total)
            if getattr(item, "valor_total", None) is not None
            else None
        )
        if total_informado is not None:
            total_item = total_informado
            custo_unitario = (
                (total_item / quantidade).quantize(CENTAVO, rounding=ROUND_HALF_UP)
                if quantidade > 0
                else Decimal("0.00")
            )
        else:
            custo_base = (
                getattr(item, "custo_unitario", None)
                if getattr(item, "custo_unitario", None) is not None
                else getattr(produto, "preco_custo", 0)
            )
            custo_unitario = _decimal_monetario(custo_base)
            total_item = (custo_unitario * quantidade).quantize(
                CENTAVO, rounding=ROUND_HALF_UP
            )

        if total_item <= 0:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Informe valor total maior que zero para o item "
                    f"'{getattr(produto, 'nome', produto_id)}'."
                ),
            )

        total_divida += total_item
        processados.append(
            {
                "produto_id": produto_id,
                "produto_nome": getattr(produto, "nome", f"Produto #{produto_id}"),
                "codigo": getattr(produto, "codigo", None),
                "codigo_barras": getattr(produto, "codigo_barras", None),
                "quantidade": float(quantidade),
                "custo_unitario": float(custo_unitario),
                "total_item": float(total_item),
                "estoque_anterior": float(getattr(produto, "estoque_atual", 0) or 0),
            }
        )

    return processados, total_divida.quantize(CENTAVO, rounding=ROUND_HALF_UP)


def _montar_observacoes_entrada_parceiro(
    observacao: str | None,
    itens_processados: list[dict],
    *,
    entrou_estoque: bool,
) -> str:
    itens_texto = "; ".join(
        f"{item['produto_nome']} x {item['quantidade']}" for item in itens_processados
    )
    partes = [
        "Entrada de parceiro com conta a pagar.",
        f"Estoque atualizado: {'sim' if entrou_estoque else 'nao'}.",
        f"Itens: {itens_texto}",
    ]
    observacao_limpa = _texto_limpo(observacao)
    if observacao_limpa:
        partes.insert(0, observacao_limpa)
    return "\n\n".join(partes)


def _buscar_parceiro_entrada(db: Session, tenant_id, parceiro_id: int):
    parceiro = (
        db.query(Cliente)
        .filter(
            Cliente.id == parceiro_id,
            Cliente.tenant_id == tenant_id,
            or_(Cliente.ativo.is_(True), Cliente.ativo.is_(None)),
        )
        .first()
    )
    if not parceiro:
        raise HTTPException(status_code=404, detail="Pessoa nao encontrada.")
    return parceiro


def _buscar_produtos_entrada(db: Session, tenant_id, produto_ids: list[int]):
    produtos = (
        db.query(Produto)
        .filter(
            Produto.id.in_(produto_ids),
            Produto.tenant_id == tenant_id,
        )
        .all()
    )
    return {int(produto.id): produto for produto in produtos}


def _registrar_movimentacoes_entrada(
    db: Session,
    *,
    tenant_id,
    user_id: int,
    conta_pagar: ContaPagar,
    parceiro,
    documento: str,
    itens_processados: list[dict],
    produtos_cache: dict[int, Produto],
) -> list[int]:
    movimentacao_ids: list[int] = []
    for item in itens_processados:
        produto = produtos_cache[int(item["produto_id"])]
        estoque_anterior = float(produto.estoque_atual or 0)
        produto.estoque_atual = estoque_anterior + float(item["quantidade"])

        movimentacao = EstoqueMovimentacao(
            produto_id=produto.id,
            tipo="entrada",
            motivo=MOTIVO_ENTRADA_PARCEIRO,
            quantidade=float(item["quantidade"]),
            quantidade_anterior=estoque_anterior,
            quantidade_nova=float(produto.estoque_atual or 0),
            custo_unitario=float(item["custo_unitario"]),
            valor_total=float(item["total_item"]),
            documento=documento,
            referencia_id=conta_pagar.id,
            referencia_tipo=MOTIVO_ENTRADA_PARCEIRO,
            observacao=(
                f"Entrada de produto recebido do parceiro {parceiro.nome}. "
                f"Conta a pagar #{conta_pagar.id}."
            ),
            user_id=user_id,
            tenant_id=str(tenant_id),
        )
        db.add(produto)
        db.add(movimentacao)
        db.flush()
        movimentacao_ids.append(movimentacao.id)

    return movimentacao_ids


def registrar_entrada_parceiro(db: Session, *, tenant_id, user_id: int, payload) -> dict:
    parceiro = _buscar_parceiro_entrada(db, tenant_id, int(payload.parceiro_id))
    documento = _texto_limpo(payload.documento) or _gerar_documento_entrada_parceiro()

    conta_existente = (
        db.query(ContaPagar)
        .filter(ContaPagar.tenant_id == str(tenant_id), ContaPagar.documento == documento)
        .first()
    )
    if conta_existente:
        raise HTTPException(
            status_code=400,
            detail="Ja existe uma conta a pagar com este documento.",
        )

    produto_ids = sorted({int(item.produto_id) for item in payload.itens or []})
    produtos_cache = _buscar_produtos_entrada(db, tenant_id, produto_ids)
    itens_processados, total_divida = preparar_itens_entrada_parceiro(
        produtos_cache,
        payload.itens,
        entrar_estoque=bool(payload.entrar_estoque),
    )

    data_emissao = payload.data_emissao or date.today()
    data_vencimento = payload.data_vencimento or data_emissao
    conta_pagar = ContaPagar(
        tenant_id=str(tenant_id),
        descricao=f"Entrada de parceiro - {parceiro.nome}",
        fornecedor_id=parceiro.id,
        canal="transferencia_parceiro_entrada",
        valor_original=total_divida,
        valor_pago=Decimal("0.00"),
        valor_final=total_divida,
        data_emissao=data_emissao,
        data_vencimento=data_vencimento,
        status="pendente",
        documento=documento,
        observacoes=_montar_observacoes_entrada_parceiro(
            payload.observacao,
            itens_processados,
            entrou_estoque=bool(payload.entrar_estoque),
        ),
        user_id=user_id,
    )
    db.add(conta_pagar)
    db.flush()

    movimentacao_ids: list[int] = []
    if payload.entrar_estoque:
        movimentacao_ids = _registrar_movimentacoes_entrada(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            conta_pagar=conta_pagar,
            parceiro=parceiro,
            documento=documento,
            itens_processados=itens_processados,
            produtos_cache=produtos_cache,
        )

    db.commit()

    if payload.entrar_estoque:
        for item in itens_processados:
            produto = produtos_cache.get(int(item["produto_id"]))
            if not produto:
                continue
            try:
                sincronizar_bling_background(
                    produto.id,
                    float(produto.estoque_atual or 0),
                    "transferencia_parceiro_entrada",
                )
            except Exception:
                pass

    return {
        "sucesso": True,
        "documento": documento,
        "conta_pagar_id": conta_pagar.id,
        "parceiro_id": parceiro.id,
        "total_divida": float(total_divida),
        "entrar_estoque": bool(payload.entrar_estoque),
        "movimentacoes_estoque": movimentacao_ids,
    }
