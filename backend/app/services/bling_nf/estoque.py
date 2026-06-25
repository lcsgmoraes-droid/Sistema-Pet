"""Helpers de produto, movimentos e baixa de estoque por NF Bling."""

from collections import Counter
import re

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.produtos_models import Produto, ProdutoKitComponente, EstoqueMovimentacao
from app.services.kit_estoque_service import KitEstoqueService

from .common import _regex_token_numerico, _text


def buscar_produto_do_item(db: Session, tenant_id, sku: str):
    if not sku:
        return None
    sku_normalizado = str(sku).strip()
    sku_lower = sku_normalizado.lower()

    return (
        db.query(Produto)
        .filter(
            Produto.tenant_id == tenant_id,
            or_(
                func.lower(func.trim(Produto.codigo)) == sku_lower,
                Produto.codigo_barras == sku_normalizado,
            ),
        )
        .first()
    )


def produto_usa_composicao_virtual(produto: Produto | None) -> bool:
    return bool(
        produto
        and produto.tipo_kit == "VIRTUAL"
        and produto.tipo_produto in {"KIT", "VARIACAO"}
    )


def produto_ids_estoque_afetados(db: Session, produto: Produto | None) -> list[int]:
    if not produto:
        return []

    if produto_usa_composicao_virtual(produto):
        componentes = (
            db.query(ProdutoKitComponente)
            .filter(ProdutoKitComponente.kit_id == produto.id)
            .all()
        )
        ids: list[int] = []
        for componente in componentes:
            if (
                componente.produto_componente_id
                and componente.produto_componente_id not in ids
            ):
                ids.append(int(componente.produto_componente_id))
        return ids

    return [int(produto.id)] if getattr(produto, "id", None) else []


def consumir_movimentacoes_esperadas(
    ids_esperados: list[int],
    movimentos_por_produto: Counter,
    movimentos_consumidos: Counter,
) -> bool:
    if not ids_esperados:
        return False

    for produto_id in ids_esperados:
        if movimentos_consumidos[produto_id] >= movimentos_por_produto[produto_id]:
            return False

    for produto_id in ids_esperados:
        movimentos_consumidos[produto_id] += 1
    return True


def movimento_documentado_por_nf(
    mov: EstoqueMovimentacao | None,
    *,
    nf_numero: str | None = None,
    nf_bling_id: str | None = None,
) -> bool:
    if not mov:
        return False

    documento = _text(getattr(mov, "documento", None))
    observacao = _text(getattr(mov, "observacao", None)) or ""
    nf_numero = _text(nf_numero)
    nf_bling_id = _text(nf_bling_id)

    if nf_numero and documento == nf_numero:
        return True

    padrao_nf_numero = _regex_token_numerico(nf_numero)
    if padrao_nf_numero and re.search(padrao_nf_numero, observacao):
        return True

    padrao_nf_bling = _regex_token_numerico(nf_bling_id)
    if padrao_nf_bling and re.search(padrao_nf_bling, observacao):
        return True

    return False


def movimento_legado_pedido_para_nf(
    mov: EstoqueMovimentacao | None,
    *,
    pedido_bling_numero: str | None = None,
    nf_numero: str | None = None,
    nf_bling_id: str | None = None,
) -> bool:
    if not mov or movimento_documentado_por_nf(
        mov, nf_numero=nf_numero, nf_bling_id=nf_bling_id
    ):
        return False

    documento = _text(getattr(mov, "documento", None))
    observacao = (_text(getattr(mov, "observacao", None)) or "").lower()
    pedido_bling_numero = _text(pedido_bling_numero)

    if pedido_bling_numero and documento == pedido_bling_numero:
        return True

    if "baixa automatica via nf autorizada do bling" in observacao:
        return True

    if "webhook bling" in observacao or "pedido criado ja atendido" in observacao:
        return True

    return False


def _consumir_movimentacoes_esperadas_lista(
    ids_esperados: list[int],
    movimentos_por_produto: dict[int, list[EstoqueMovimentacao]],
) -> list[EstoqueMovimentacao] | None:
    if not ids_esperados:
        return None

    selecionadas: list[EstoqueMovimentacao] = []
    for produto_id in ids_esperados:
        lista = movimentos_por_produto.get(produto_id) or []
        if not lista:
            return None
        selecionadas.append(lista[0])

    for movimentacao in selecionadas:
        lista = movimentos_por_produto.get(int(movimentacao.produto_id)) or []
        if lista:
            lista.pop(0)

    return selecionadas


def _normalizar_movimentacoes_legadas_para_nf(
    db: Session,
    movimentos: list[EstoqueMovimentacao],
    *,
    nf_numero: str | None,
    nf_bling_id: str | None,
) -> int:
    movimentos_atualizados = 0
    observacao_nf = _observacao_baixa_nf(nf_numero, nf_bling_id)

    for movimentacao in movimentos:
        if _text(nf_numero):
            movimentacao.documento = _text(nf_numero)
        if observacao_nf:
            movimentacao.observacao = observacao_nf
        db.add(movimentacao)
        movimentos_atualizados += 1

    return movimentos_atualizados


def _observacao_baixa_nf(
    nf_numero: str | None,
    nf_bling_id: str | None,
) -> str | None:
    nf_numero = _text(nf_numero)
    if nf_numero:
        return f"Baixa automatica via NF {nf_numero}"

    nf_bling_id = _text(nf_bling_id)
    if nf_bling_id:
        return f"Baixa automatica via NF Bling #{nf_bling_id}"

    return None


def _sincronizar_cache_estoque_virtual(
    db: Session, tenant_id, kit_id: int
) -> float | None:
    produto_kit = (
        db.query(Produto)
        .filter(Produto.id == kit_id, Produto.tenant_id == tenant_id)
        .first()
    )
    if not produto_kit or not produto_usa_composicao_virtual(produto_kit):
        return None

    estoque_virtual = float(KitEstoqueService.calcular_estoque_virtual_kit(db, kit_id))
    produto_kit.estoque_atual = estoque_virtual
    db.add(produto_kit)
    return estoque_virtual


def _baixar_estoque_produto_simples(
    *,
    estoque_service,
    db: Session,
    tenant_id,
    produto: Produto,
    quantidade: float,
    motivo: str,
    referencia_id: int,
    referencia_tipo: str,
    user_id: int,
    documento: str | None = None,
    observacao: str | None = None,
) -> dict:
    resultado = estoque_service.baixar_estoque(
        produto_id=produto.id,
        quantidade=quantidade,
        motivo=motivo,
        referencia_id=referencia_id,
        referencia_tipo=referencia_tipo,
        user_id=user_id,
        db=db,
        tenant_id=tenant_id,
        documento=documento,
        observacao=observacao,
    )
    return {
        "movimentos": [
            {
                "produto_id": produto.id,
                "produto_nome": resultado.get("produto_nome"),
                "quantidade": quantidade,
            }
        ],
        "estoques_virtuais": {},
    }


def _produto_componente_ou_erro(
    db: Session,
    *,
    tenant_id,
    produto: Produto,
    componente: ProdutoKitComponente,
) -> Produto:
    produto_componente = (
        db.query(Produto)
        .filter(
            Produto.id == componente.produto_componente_id,
            Produto.tenant_id == tenant_id,
        )
        .first()
    )
    if not produto_componente:
        raise ValueError(
            f"Componente ID {componente.produto_componente_id} nao encontrado para '{produto.nome}'."
        )
    return produto_componente


def _baixar_estoque_produto_composto(
    *,
    estoque_service,
    db: Session,
    tenant_id,
    produto: Produto,
    quantidade: float,
    motivo: str,
    referencia_id: int,
    referencia_tipo: str,
    user_id: int,
    documento: str | None = None,
    observacao: str | None = None,
) -> dict:
    componentes = (
        db.query(ProdutoKitComponente)
        .filter(ProdutoKitComponente.kit_id == produto.id)
        .all()
    )
    if not componentes:
        raise ValueError(
            f"Produto composto '{produto.nome}' nao possui componentes cadastrados."
        )

    movimentos: list[dict] = []
    kits_recalculados: dict[int, float] = {}

    for componente in componentes:
        produto_componente = _produto_componente_ou_erro(
            db,
            tenant_id=tenant_id,
            produto=produto,
            componente=componente,
        )
        quantidade_componente = quantidade * float(componente.quantidade or 0)
        resultado = estoque_service.baixar_estoque(
            produto_id=produto_componente.id,
            quantidade=quantidade_componente,
            motivo=motivo,
            referencia_id=referencia_id,
            referencia_tipo=referencia_tipo,
            user_id=user_id,
            db=db,
            tenant_id=tenant_id,
            documento=documento,
            observacao=(
                observacao or f"Componente do produto composto '{produto.nome}'"
            ),
        )
        movimentos.append(
            {
                "produto_id": produto_componente.id,
                "produto_nome": resultado.get("produto_nome"),
                "quantidade": quantidade_componente,
                "kit_origem_id": produto.id,
                "kit_origem_nome": produto.nome,
            }
        )

        for (
            kit_id,
            estoque_virtual,
        ) in KitEstoqueService.recalcular_kits_que_usam_produto(
            db,
            produto_componente.id,
        ).items():
            kits_recalculados[kit_id] = float(estoque_virtual)

    for kit_id, estoque_virtual in list(kits_recalculados.items()):
        estoque_sincronizado = _sincronizar_cache_estoque_virtual(db, tenant_id, kit_id)
        if estoque_sincronizado is not None:
            kits_recalculados[kit_id] = estoque_sincronizado

    return {
        "movimentos": movimentos,
        "estoques_virtuais": kits_recalculados,
    }


def baixar_estoque_item_integrado(
    *,
    db: Session,
    tenant_id,
    produto: Produto,
    quantidade: float,
    motivo: str,
    referencia_id: int,
    referencia_tipo: str,
    user_id: int,
    documento: str | None = None,
    observacao: str | None = None,
) -> dict:
    from app.estoque.service import EstoqueService

    quantidade = float(quantidade or 0)
    if quantidade <= 0:
        return {"movimentos": [], "estoques_virtuais": {}}
    if not user_id:
        raise ValueError(
            "Nenhum usuario valido disponivel para registrar a movimentacao automatica do estoque."
        )

    if produto_usa_composicao_virtual(produto):
        return _baixar_estoque_produto_composto(
            estoque_service=EstoqueService,
            db=db,
            tenant_id=tenant_id,
            produto=produto,
            quantidade=quantidade,
            motivo=motivo,
            referencia_id=referencia_id,
            referencia_tipo=referencia_tipo,
            user_id=user_id,
            documento=documento,
            observacao=observacao,
        )

    return _baixar_estoque_produto_simples(
        estoque_service=EstoqueService,
        db=db,
        tenant_id=tenant_id,
        produto=produto,
        quantidade=quantidade,
        motivo=motivo,
        referencia_id=referencia_id,
        referencia_tipo=referencia_tipo,
        user_id=user_id,
        documento=documento,
        observacao=observacao,
    )
