"""Processamento de estoque da baixa FULL por NF."""

from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..models import User
from ..produtos_models import EstoqueMovimentacao, Produto, ProdutoKitComponente
from ..services.kit_estoque_service import KitEstoqueService
from .common import _texto_limpo
from .schemas import SaidaFullNFItemRequest


def _resolver_produto_full_nf(
    db: Session, tenant_id: int, item: SaidaFullNFItemRequest
) -> Optional[Produto]:
    if item.produto_id:
        return (
            db.query(Produto)
            .filter(
                Produto.id == item.produto_id,
                Produto.tenant_id == tenant_id,
            )
            .first()
        )

    if item.sku:
        filtros_sku = [Produto.codigo == item.sku]
        # Compatibilidade com modelos legados que ainda possam expor campo "sku".
        if hasattr(Produto, "sku"):
            filtros_sku.append(getattr(Produto, "sku") == item.sku)

        return (
            db.query(Produto)
            .filter(
                Produto.tenant_id == tenant_id,
                or_(*filtros_sku),
            )
            .first()
        )

    return None


def _sku_produto(produto: Produto) -> Optional[str]:
    return getattr(produto, "sku", None) or getattr(produto, "codigo", None)


def _produto_usa_estoque_virtual_full_nf(produto: Produto) -> bool:
    return (
        getattr(produto, "tipo_produto", None) in ("KIT", "VARIACAO")
        and getattr(produto, "tipo_kit", None) == "VIRTUAL"
    )


def _estoque_disponivel_saida_full_nf(
    db: Session, tenant_id: int, produto: Produto
) -> float:
    if _produto_usa_estoque_virtual_full_nf(produto):
        return float(
            KitEstoqueService.calcular_estoque_virtual_kit(
                db,
                produto.id,
                tenant_id=tenant_id,
            )
            or 0
        )

    return float(getattr(produto, "estoque_atual", 0) or 0)


def _processar_item_saida_full_nf(
    db: Session,
    tenant_id: int,
    item: SaidaFullNFItemRequest,
    numero_nf: str,
    observacao_movimentacao: str,
    current_user: User,
    permitir_estoque_negativo: bool = False,
):
    produto = _resolver_produto_full_nf(db, tenant_id, item)
    if not produto:
        raise HTTPException(
            status_code=400,
            detail=f"Produto nao encontrado para item (produto_id={item.produto_id}, sku={item.sku})",
        )

    if _produto_usa_estoque_virtual_full_nf(produto):
        return _processar_item_kit_virtual_saida_full_nf(
            db=db,
            tenant_id=tenant_id,
            produto=produto,
            item=item,
            numero_nf=numero_nf,
            observacao_movimentacao=observacao_movimentacao,
            current_user=current_user,
            permitir_estoque_negativo=permitir_estoque_negativo,
        )

    estoque_anterior = float(produto.estoque_atual or 0)
    faltante = max(float(item.quantidade or 0) - estoque_anterior, 0)
    if estoque_anterior < item.quantidade and not permitir_estoque_negativo:
        sku_label = _sku_produto(produto) or "sem-sku"
        raise HTTPException(
            status_code=400,
            detail=(
                f"Estoque insuficiente para {produto.nome} (SKU {sku_label}). "
                f"Disponivel: {estoque_anterior}, solicitado: {item.quantidade}"
            ),
        )

    produto.estoque_atual = estoque_anterior - item.quantidade

    movimentacao = EstoqueMovimentacao(
        produto_id=produto.id,
        tipo="saida",
        motivo="full_nfe_saida",
        quantidade=item.quantidade,
        quantidade_anterior=estoque_anterior,
        quantidade_nova=produto.estoque_atual,
        custo_unitario=produto.preco_custo,
        valor_total=item.quantidade * float(produto.preco_custo or 0),
        documento=numero_nf,
        observacao=observacao_movimentacao,
        user_id=current_user.id,
        tenant_id=tenant_id,
    )
    db.add(movimentacao)

    return {
        "produto_id": produto.id,
        "sku": _sku_produto(produto),
        "nome": produto.nome,
        "quantidade": item.quantidade,
        "estoque_anterior": estoque_anterior,
        "estoque_novo": float(produto.estoque_atual or 0),
        "estoque_negativo": float(produto.estoque_atual or 0) < 0,
        "faltante": faltante,
    }


def _processar_item_kit_virtual_saida_full_nf(
    db: Session,
    tenant_id: int,
    produto: Produto,
    item: SaidaFullNFItemRequest,
    numero_nf: str,
    observacao_movimentacao: str,
    current_user: User,
    permitir_estoque_negativo: bool = False,
):
    estoque_anterior = _estoque_disponivel_saida_full_nf(db, tenant_id, produto)
    quantidade_kits = float(item.quantidade or 0)

    if estoque_anterior < quantidade_kits and not permitir_estoque_negativo:
        sku_label = _sku_produto(produto) or "sem-sku"
        raise HTTPException(
            status_code=400,
            detail=(
                f"Estoque insuficiente para {produto.nome} (SKU {sku_label}). "
                f"Disponivel: {estoque_anterior}, solicitado: {quantidade_kits}"
            ),
        )

    componentes = (
        db.query(ProdutoKitComponente)
        .filter(ProdutoKitComponente.kit_id == produto.id)
        .all()
    )
    if not componentes:
        sku_label = _sku_produto(produto) or "sem-sku"
        raise HTTPException(
            status_code=400,
            detail=f"Kit virtual {produto.nome} (SKU {sku_label}) nao possui componentes cadastrados",
        )

    componentes_para_baixa = []
    for componente in componentes:
        produto_componente = (
            db.query(Produto)
            .filter(
                Produto.id == componente.produto_componente_id,
                Produto.tenant_id == tenant_id,
            )
            .first()
        )
        if not produto_componente:
            raise HTTPException(
                status_code=400,
                detail=f"Componente #{componente.produto_componente_id} do kit {produto.nome} nao encontrado",
            )

        quantidade_componente = quantidade_kits * float(componente.quantidade or 0)
        estoque_componente = float(produto_componente.estoque_atual or 0)
        if estoque_componente < quantidade_componente and not permitir_estoque_negativo:
            sku_label = _sku_produto(produto_componente) or "sem-sku"
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Estoque insuficiente no componente {produto_componente.nome} (SKU {sku_label}) "
                    f"para baixar o kit {produto.nome}. Disponivel: {estoque_componente}, "
                    f"solicitado: {quantidade_componente}"
                ),
            )

        componentes_para_baixa.append(
            {
                "produto": produto_componente,
                "quantidade": quantidade_componente,
                "estoque_anterior": estoque_componente,
            }
        )

    componentes_baixados = []
    for baixa in componentes_para_baixa:
        produto_componente = baixa["produto"]
        quantidade_componente = baixa["quantidade"]
        estoque_componente_anterior = baixa["estoque_anterior"]
        estoque_componente_novo = estoque_componente_anterior - quantidade_componente
        produto_componente.estoque_atual = estoque_componente_novo

        movimentacao_componente = EstoqueMovimentacao(
            produto_id=produto_componente.id,
            tipo="saida",
            motivo="full_nfe_saida",
            quantidade=quantidade_componente,
            quantidade_anterior=estoque_componente_anterior,
            quantidade_nova=estoque_componente_novo,
            custo_unitario=produto_componente.preco_custo,
            valor_total=quantidade_componente
            * float(produto_componente.preco_custo or 0),
            documento=numero_nf,
            observacao=(
                f"{observacao_movimentacao} | componente do kit virtual "
                f"{_sku_produto(produto) or produto.nome} ({quantidade_kits:g} kit(s))"
            ),
            user_id=current_user.id,
            tenant_id=tenant_id,
        )
        db.add(movimentacao_componente)

        componentes_baixados.append(
            {
                "produto_id": produto_componente.id,
                "sku": _sku_produto(produto_componente),
                "nome": produto_componente.nome,
                "quantidade": quantidade_componente,
                "estoque_anterior": estoque_componente_anterior,
                "estoque_novo": estoque_componente_novo,
            }
        )

    estoque_novo = _estoque_disponivel_saida_full_nf(db, tenant_id, produto)
    movimentacao_kit = EstoqueMovimentacao(
        produto_id=produto.id,
        tipo="saida",
        motivo="full_nfe_saida",
        quantidade=quantidade_kits,
        quantidade_anterior=estoque_anterior,
        quantidade_nova=estoque_novo,
        custo_unitario=0,
        valor_total=0,
        documento=numero_nf,
        observacao=f"{observacao_movimentacao} | kit virtual (baixa real nos componentes)",
        user_id=current_user.id,
        tenant_id=tenant_id,
    )
    db.add(movimentacao_kit)

    return {
        "produto_id": produto.id,
        "sku": _sku_produto(produto),
        "nome": produto.nome,
        "quantidade": quantidade_kits,
        "estoque_anterior": estoque_anterior,
        "estoque_novo": estoque_novo,
        "estoque_negativo": any(
            float(componente["estoque_novo"] or 0) < 0
            for componente in componentes_baixados
        ),
        "faltante": max(quantidade_kits - estoque_anterior, 0),
        "tipo_kit": "VIRTUAL",
        "componentes_baixados": componentes_baixados,
        "sync_itens": [
            {
                "produto_id": componente["produto_id"],
                "estoque_novo": componente["estoque_novo"],
            }
            for componente in componentes_baixados
        ]
        + [
            {
                "produto_id": produto.id,
                "estoque_novo": estoque_novo,
            }
        ],
    }


def _problemas_estoque_saida_full_nf(
    db: Session,
    tenant_id: int,
    itens: List[SaidaFullNFItemRequest],
) -> List[dict]:
    problemas = []

    for item in itens:
        produto = _resolver_produto_full_nf(db, tenant_id, item)
        entrada_sku = _texto_limpo(item.sku)

        if not produto:
            problemas.append(
                {
                    "tipo": "produto_nao_encontrado",
                    "produto_id": item.produto_id,
                    "entrada_sku": entrada_sku,
                    "sku": entrada_sku,
                    "nome": "Produto nao encontrado",
                    "disponivel": 0,
                    "solicitado": float(item.quantidade or 0),
                    "faltante": float(item.quantidade or 0),
                    "mensagem": f"Produto nao encontrado para SKU {entrada_sku or item.produto_id or '-'}",
                    "url_correcao": None,
                }
            )
            continue

        estoque_anterior = _estoque_disponivel_saida_full_nf(db, tenant_id, produto)
        quantidade = float(item.quantidade or 0)
        if estoque_anterior < quantidade:
            sku_label = _sku_produto(produto) or entrada_sku or "sem-sku"
            faltante = max(quantidade - estoque_anterior, 0)
            usa_estoque_virtual = _produto_usa_estoque_virtual_full_nf(produto)
            problemas.append(
                {
                    "tipo": "estoque_insuficiente_kit_virtual"
                    if usa_estoque_virtual
                    else "estoque_insuficiente",
                    "produto_id": produto.id,
                    "entrada_sku": entrada_sku,
                    "sku": sku_label,
                    "nome": produto.nome,
                    "disponivel": estoque_anterior,
                    "solicitado": quantidade,
                    "faltante": faltante,
                    "mensagem": (
                        f"Estoque insuficiente para {produto.nome} (SKU {sku_label}). "
                        f"Disponivel: {estoque_anterior}, solicitado: {quantidade}"
                    ),
                    "url_correcao": f"/produtos/{produto.id}/editar"
                    if usa_estoque_virtual
                    else f"/produtos/{produto.id}/movimentacoes",
                }
            )

    return problemas


def _validar_estoque_saida_full_nf(
    db: Session,
    tenant_id: int,
    itens: List[SaidaFullNFItemRequest],
) -> None:
    problemas = _problemas_estoque_saida_full_nf(db, tenant_id, itens)
    if problemas:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "estoque_insuficiente_full_nf",
                "message": (
                    "Alguns itens nao possuem estoque suficiente para baixa. "
                    "Corrija o estoque dos produtos marcados e revalide antes de confirmar."
                ),
                "itens": problemas,
            },
        )
