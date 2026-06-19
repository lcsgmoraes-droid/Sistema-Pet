"""Rotas de confronto entre pedidos de compra e NF-e."""

import io
import json
import logging
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.models import Cliente
from app.produtos_models import (
    PedidoCompra,
    PedidoCompraItem,
    PedidoCompraNotaEntrada,
    Produto,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# CONFRONTO PEDIDO x NF-e
# ============================================================================


def _float_confronto(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _calcular_composicoes_custo_confronto(notas: List) -> Dict[int, Dict[str, Any]]:
    """Reaproveita o custo final calculado na entrada da NF para o confronto."""
    try:
        from app import notas_entrada_routes
    except ImportError:
        logger.exception(
            "Nao foi possivel importar composicao de custos da NF para confronto"
        )
        return {}

    composicoes: Dict[int, Dict[str, Any]] = {}
    for nota in notas:
        try:
            composicoes.update(
                notas_entrada_routes.calcular_composicao_custos_nota(nota) or {}
            )
        except Exception:
            logger.exception(
                "Falha ao calcular custo final da NF no confronto pedido x nota",
                extra={"nota_entrada_id": getattr(nota, "id", None)},
            )
    return composicoes


def _valor_custo_final_item_nf(
    item_nf: Any, composicoes_custo: Dict[int, Dict[str, Any]]
) -> float:
    composicao = composicoes_custo.get(getattr(item_nf, "id", None)) or {}
    if composicao.get("custo_aquisicao_total") is not None:
        return _float_confronto(composicao.get("custo_aquisicao_total"))
    return _float_confronto(getattr(item_nf, "valor_total", 0))


def _preco_custo_final_item_nf(
    item_nf: Any, composicoes_custo: Dict[int, Dict[str, Any]]
) -> float:
    valor_total = _valor_custo_final_item_nf(item_nf, composicoes_custo)
    quantidade = _float_confronto(getattr(item_nf, "quantidade", 0))
    if quantidade:
        return valor_total / quantidade

    composicao = composicoes_custo.get(getattr(item_nf, "id", None)) or {}
    if composicao.get("custo_aquisicao_unitario") is not None:
        return _float_confronto(composicao.get("custo_aquisicao_unitario"))
    return _float_confronto(getattr(item_nf, "valor_unitario", 0))


def _status_item_confronto(
    dif_qtd: float, dif_preco_pct: float
) -> tuple[str, bool, bool]:
    divergiu_qtd = abs(dif_qtd) > 0.001
    divergiu_preco = abs(dif_preco_pct) > 0.5

    if divergiu_qtd and divergiu_preco:
        status_item = "divergencia_mista"
    elif divergiu_qtd:
        status_item = "divergencia_quantidade"
    elif divergiu_preco:
        status_item = "divergencia_preco"
    else:
        status_item = "ok"

    return status_item, divergiu_qtd, divergiu_preco


def _montar_item_confronto_encontrado(
    item_pedido,
    nome_produto,
    codigo_produto,
    item_nf_id,
    qtd_pedida,
    qtd_nf,
    preco_pedido,
    preco_nf,
    valor_pedido,
    valor_nf,
    extras: dict | None = None,
) -> tuple[dict, bool, bool]:
    dif_qtd = qtd_nf - qtd_pedida
    dif_preco_unit = preco_nf - preco_pedido
    dif_preco_pct = (
        ((preco_nf - preco_pedido) / preco_pedido * 100) if preco_pedido else 0
    )
    dif_valor = valor_nf - valor_pedido
    status_item, divergiu_qtd, divergiu_preco = _status_item_confronto(
        dif_qtd, dif_preco_pct
    )

    item = {
        "produto_id": item_pedido.produto_id,
        "produto_nome": nome_produto,
        "produto_codigo": codigo_produto,
        "item_pedido_id": item_pedido.id,
        "item_nf_id": item_nf_id,
        "qtd_pedida": qtd_pedida,
        "qtd_nf": qtd_nf,
        "dif_qtd": round(dif_qtd, 3),
        "preco_pedido": round(preco_pedido, 4),
        "preco_nf": round(preco_nf, 4),
        "dif_preco_unit": round(dif_preco_unit, 4),
        "dif_preco_pct": round(dif_preco_pct, 2),
        "valor_pedido": round(valor_pedido, 2),
        "valor_nf": round(valor_nf, 2),
        "dif_valor": round(dif_valor, 2),
        "status": status_item,
        "encontrado_na_nf": True,
    }
    if extras:
        item.update(extras)
    return item, divergiu_qtd, divergiu_preco


def _montar_item_confronto_nao_encontrado(
    item_pedido,
    nome_produto,
    codigo_produto,
    qtd_pedida,
    preco_pedido,
    valor_pedido,
    extras: dict | None = None,
) -> dict:
    item = {
        "produto_id": item_pedido.produto_id,
        "produto_nome": nome_produto,
        "produto_codigo": codigo_produto,
        "item_pedido_id": item_pedido.id,
        "item_nf_id": None,
        "qtd_pedida": qtd_pedida,
        "qtd_nf": 0,
        "dif_qtd": -qtd_pedida,
        "preco_pedido": round(preco_pedido, 4),
        "preco_nf": 0,
        "dif_preco_unit": None,
        "dif_preco_pct": 0,
        "valor_pedido": round(valor_pedido, 2),
        "valor_nf": 0,
        "dif_valor": -round(valor_pedido, 2),
        "status": "nao_encontrado",
        "encontrado_na_nf": False,
    }
    if extras:
        item.update(extras)
    return item


def _normalizar_notas_confronto(nota_ou_notas) -> List:
    if not nota_ou_notas:
        return []
    if isinstance(nota_ou_notas, (list, tuple, set)):
        return [n for n in nota_ou_notas if n]
    return [nota_ou_notas]


def _resumir_notas_confronto(notas: List) -> List[dict]:
    return [
        {
            "id": n.id,
            "numero_nota": n.numero_nota,
            "serie": n.serie,
            "chave_acesso": n.chave_acesso,
            "fornecedor_nome": n.fornecedor_nome,
            "data_emissao": n.data_emissao,
            "valor_total": n.valor_total,
        }
        for n in notas
    ]


def _formatar_numeros_notas(notas: List) -> str:
    numeros = [str(n.numero_nota) for n in notas if getattr(n, "numero_nota", None)]
    return ", ".join(numeros) if numeros else "-"


def _realizar_confronto(
    pedido: PedidoCompra, nota_ou_notas, db: Session, tenant_id: int
) -> dict:
    """Gera o confronto completo entre pedido e uma ou mais NF-e."""
    notas = _normalizar_notas_confronto(nota_ou_notas)
    itens_nf = [item for nota in notas for item in (nota.itens or [])]
    composicoes_custo = _calcular_composicoes_custo_confronto(notas)

    itens_confronto = []
    total_pedido = 0.0
    total_nf = 0.0
    tem_divergencia_qtd = False
    tem_divergencia_preco = False
    itens_nf_usados = set()

    def _codigo_igual(valor_a, valor_b) -> bool:
        if valor_a is None or valor_b is None:
            return False
        return str(valor_a).strip() == str(valor_b).strip()

    def _itens_nf_para_pedido(item_pedido, codigo_produto, ean_produto):
        candidatos = [
            it
            for it in itens_nf
            if it.id not in itens_nf_usados and it.produto_id == item_pedido.produto_id
        ]
        if candidatos:
            return candidatos

        if ean_produto:
            candidatos = [
                it
                for it in itens_nf
                if it.id not in itens_nf_usados
                and it.ean
                and _codigo_igual(it.ean, ean_produto)
            ]
            if candidatos:
                return candidatos

        if codigo_produto:
            candidatos = [
                it
                for it in itens_nf
                if it.id not in itens_nf_usados
                and it.codigo_produto
                and _codigo_igual(it.codigo_produto, codigo_produto)
            ]
            if candidatos:
                return candidatos

        return []

    for item_pedido in pedido.itens:
        produto = (
            db.query(Produto)
            .filter(
                Produto.id == item_pedido.produto_id, Produto.tenant_id == tenant_id
            )
            .first()
        )

        nome_produto = produto.nome if produto else f"Produto {item_pedido.produto_id}"
        codigo_produto = produto.codigo if produto else None
        ean_produto = produto.codigo_barras if produto else None
        itens_match = _itens_nf_para_pedido(item_pedido, codigo_produto, ean_produto)

        qtd_pedida = item_pedido.quantidade_pedida
        preco_pedido = item_pedido.preco_unitario - item_pedido.desconto_item
        valor_pedido = qtd_pedida * preco_pedido
        total_pedido += valor_pedido

        if itens_match:
            for it in itens_match:
                itens_nf_usados.add(it.id)

            qtd_nf = sum(float(it.quantidade or 0) for it in itens_match)
            valor_nf = sum(
                _valor_custo_final_item_nf(it, composicoes_custo) for it in itens_match
            )
            preco_nf = (
                (valor_nf / qtd_nf)
                if qtd_nf
                else _preco_custo_final_item_nf(itens_match[0], composicoes_custo)
            )
            total_nf += valor_nf

            item_confronto, divergiu_qtd, divergiu_preco = (
                _montar_item_confronto_encontrado(
                    item_pedido,
                    nome_produto,
                    codigo_produto,
                    itens_match[0].id,
                    qtd_pedida,
                    qtd_nf,
                    preco_pedido,
                    preco_nf,
                    valor_pedido,
                    valor_nf,
                    extras={
                        "item_nf_ids": [it.id for it in itens_match],
                        "nota_entrada_ids": sorted(
                            {
                                it.nota_entrada_id
                                for it in itens_match
                                if it.nota_entrada_id
                            }
                        ),
                    },
                )
            )
            if divergiu_qtd:
                tem_divergencia_qtd = True
            if divergiu_preco:
                tem_divergencia_preco = True

            itens_confronto.append(item_confronto)
        else:
            tem_divergencia_qtd = True
            item_confronto = _montar_item_confronto_nao_encontrado(
                item_pedido,
                nome_produto,
                codigo_produto,
                qtd_pedida,
                preco_pedido,
                valor_pedido,
                extras={"item_nf_ids": [], "nota_entrada_ids": []},
            )
            itens_confronto.append(item_confronto)

    for it in itens_nf:
        if it.id in itens_nf_usados:
            continue
        qtd_nf = _float_confronto(it.quantidade)
        valor_nf = _valor_custo_final_item_nf(it, composicoes_custo)
        preco_nf = _preco_custo_final_item_nf(it, composicoes_custo)
        total_nf += valor_nf
        itens_confronto.append(
            {
                "produto_id": it.produto_id,
                "produto_nome": it.descricao,
                "produto_codigo": it.codigo_produto,
                "item_pedido_id": None,
                "item_nf_id": it.id,
                "item_nf_ids": [it.id],
                "nota_entrada_ids": [it.nota_entrada_id] if it.nota_entrada_id else [],
                "qtd_pedida": 0,
                "qtd_nf": qtd_nf,
                "dif_qtd": qtd_nf,
                "preco_pedido": 0,
                "preco_nf": round(preco_nf, 4),
                "dif_preco_unit": None,
                "dif_preco_pct": 0,
                "valor_pedido": 0,
                "valor_nf": round(valor_nf, 2),
                "dif_valor": round(valor_nf, 2),
                "status": "nao_pedido",
                "encontrado_na_nf": True,
            }
        )

    if tem_divergencia_qtd and tem_divergencia_preco:
        status_confronto = "divergencia_mista"
    elif tem_divergencia_qtd:
        status_confronto = "divergencia_quantidade"
    elif tem_divergencia_preco:
        status_confronto = "divergencia_preco"
    else:
        status_confronto = "sem_divergencia"

    return {
        "status_confronto": status_confronto,
        "itens": itens_confronto,
        "resumo": {
            "total_pedido": round(total_pedido, 2),
            "total_nf": round(total_nf, 2),
            "dif_total": round(total_nf - total_pedido, 2),
            "frete_pedido": pedido.valor_frete,
            "frete_nf": round(sum(float(n.valor_frete or 0) for n in notas), 2),
            "desconto_pedido": pedido.valor_desconto,
            "desconto_nf": round(sum(float(n.valor_desconto or 0) for n in notas), 2),
            "itens_pedido": len(pedido.itens),
            "itens_nf": len(itens_nf),
            "notas_count": len(notas),
            "nota_entrada_ids": [n.id for n in notas],
            "numeros_nota": _formatar_numeros_notas(notas),
            "notas_entrada": _resumir_notas_confronto(notas),
        },
    }


def _aplicar_filtros_confronto(itens: List[dict], filtros: Optional[str]) -> List[dict]:
    if not filtros:
        return itens
    status_list = [s.strip() for s in filtros.split(",") if s.strip()]
    if not status_list:
        return itens
    return [i for i in itens if i.get("status") in status_list]


def _resumo_por_itens(itens: List[dict], resumo_base: dict) -> dict:
    total_pedido = round(sum(float(i.get("valor_pedido", 0) or 0) for i in itens), 2)
    total_nf = round(sum(float(i.get("valor_nf", 0) or 0) for i in itens), 2)
    return {
        "total_pedido": total_pedido,
        "total_nf": total_nf,
        "dif_total": round(total_nf - total_pedido, 2),
        "frete_pedido": resumo_base.get("frete_pedido", 0),
        "frete_nf": resumo_base.get("frete_nf", 0),
        "desconto_pedido": resumo_base.get("desconto_pedido", 0),
        "desconto_nf": resumo_base.get("desconto_nf", 0),
        "itens_pedido": resumo_base.get("itens_pedido", 0),
        "itens_nf": resumo_base.get("itens_nf", 0),
    }


def _ids_notas_vinculadas(
    db: Session, pedido: PedidoCompra, tenant_id: int
) -> List[int]:
    ids = [
        row[0]
        for row in db.query(PedidoCompraNotaEntrada.nota_entrada_id)
        .filter(
            PedidoCompraNotaEntrada.pedido_compra_id == pedido.id,
            PedidoCompraNotaEntrada.tenant_id == tenant_id,
        )
        .order_by(PedidoCompraNotaEntrada.id.asc())
        .all()
    ]
    if not ids and pedido.nota_entrada_id:
        ids = [pedido.nota_entrada_id]
    return ids


def _garantir_vinculo_legado(
    db: Session, pedido: PedidoCompra, tenant_id: int, user_id: int
) -> None:
    if not pedido.nota_entrada_id:
        return
    existe = (
        db.query(PedidoCompraNotaEntrada.id)
        .filter(
            PedidoCompraNotaEntrada.pedido_compra_id == pedido.id,
            PedidoCompraNotaEntrada.nota_entrada_id == pedido.nota_entrada_id,
            PedidoCompraNotaEntrada.tenant_id == tenant_id,
        )
        .first()
    )
    if existe:
        return
    db.add(
        PedidoCompraNotaEntrada(
            pedido_compra_id=pedido.id,
            nota_entrada_id=pedido.nota_entrada_id,
            user_id=user_id,
            tenant_id=tenant_id,
        )
    )
    db.flush()


def _sincronizar_nota_legacy(pedido: PedidoCompra, nota_ids: List[int]) -> None:
    pedido.nota_entrada_id = nota_ids[0] if nota_ids else None


def _obter_notas_vinculadas(
    db: Session, pedido: PedidoCompra, tenant_id: int, com_itens: bool = False
) -> List:
    from app.produtos_models import NotaEntrada

    nota_ids = _ids_notas_vinculadas(db, pedido, tenant_id)
    if not nota_ids:
        return []

    query = db.query(NotaEntrada)
    if com_itens:
        query = query.options(joinedload(NotaEntrada.itens))

    notas = query.filter(
        NotaEntrada.id.in_(nota_ids),
        NotaEntrada.tenant_id == tenant_id,
    ).all()
    por_id = {n.id: n for n in notas}
    return [por_id[nid] for nid in nota_ids if nid in por_id]


def _numero_nota_confronto_exportacao(
    db: Session, pedido: PedidoCompra, tenant_id: int, resumo: dict, default: str = "-"
) -> str:
    from app.produtos_models import NotaEntrada

    nota = (
        db.query(NotaEntrada)
        .filter(
            NotaEntrada.id == pedido.nota_entrada_id,
            NotaEntrada.tenant_id == tenant_id,
        )
        .first()
        if pedido.nota_entrada_id
        else None
    )
    return (
        _formatar_numeros_notas(_obter_notas_vinculadas(db, pedido, tenant_id))
        or resumo.get("numeros_nota")
        or (nota.numero_nota if nota and nota.numero_nota else default)
    )


def _carregar_confronto_exportacao(
    db: Session,
    pedido_id: int,
    tenant_id: int,
    filtros: Optional[str],
    numero_nota_default: Optional[str] = "-",
) -> tuple[PedidoCompra, List[dict], dict, str]:
    pedido = (
        db.query(PedidoCompra)
        .filter(PedidoCompra.id == pedido_id, PedidoCompra.tenant_id == tenant_id)
        .first()
    )
    if not pedido or not pedido.resumo_confronto:
        raise HTTPException(status_code=404, detail="Confronto não encontrado")

    confronto = json.loads(pedido.resumo_confronto)
    itens = _aplicar_filtros_confronto(confronto.get("itens", []), filtros)
    resumo = _resumo_por_itens(itens, confronto.get("resumo", {}))
    if numero_nota_default is None:
        numero_nota_default = str(pedido.nota_entrada_id or "")
    numero_nota = _numero_nota_confronto_exportacao(
        db, pedido, tenant_id, resumo, numero_nota_default
    )
    return pedido, itens, resumo, numero_nota


def _buscar_pedido_finalizado_da_nota(
    db: Session, nota_id: int, pedido_id: int, tenant_id: int
) -> Optional[PedidoCompra]:
    pedido_por_vinculo = (
        db.query(PedidoCompra)
        .join(
            PedidoCompraNotaEntrada,
            PedidoCompraNotaEntrada.pedido_compra_id == PedidoCompra.id,
        )
        .filter(
            PedidoCompraNotaEntrada.nota_entrada_id == nota_id,
            PedidoCompraNotaEntrada.tenant_id == tenant_id,
            PedidoCompra.confronto_finalizado,
            PedidoCompra.id != pedido_id,
            PedidoCompra.tenant_id == tenant_id,
        )
        .first()
    )
    if pedido_por_vinculo:
        return pedido_por_vinculo

    return (
        db.query(PedidoCompra)
        .filter(
            PedidoCompra.nota_entrada_id == nota_id,
            PedidoCompra.confronto_finalizado,
            PedidoCompra.id != pedido_id,
            PedidoCompra.tenant_id == tenant_id,
        )
        .first()
    )


def _salvar_confronto_pedido(
    pedido: PedidoCompra, notas: List, confronto: dict
) -> None:
    pedido.data_confronto = datetime.utcnow()
    pedido.status_confronto = confronto["status_confronto"]
    pedido.resumo_confronto = json.dumps(confronto, ensure_ascii=False, default=str)
    pedido.updated_at = datetime.utcnow()
    _sincronizar_nota_legacy(pedido, [n.id for n in notas])


@router.get("/{pedido_id}/notas-candidatas")
def listar_notas_candidatas(
    pedido_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista NF-e importadas do mesmo fornecedor do pedido, ordenadas pela mais recente."""
    from app.produtos_models import NotaEntrada

    current_user, tenant_id = current_user_and_tenant
    pedido = (
        db.query(PedidoCompra)
        .filter(PedidoCompra.id == pedido_id, PedidoCompra.tenant_id == tenant_id)
        .first()
    )
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    # Buscar CNPJ do fornecedor
    fornecedor = (
        db.query(Cliente)
        .filter(Cliente.id == pedido.fornecedor_id, Cliente.tenant_id == tenant_id)
        .first()
    )

    query = db.query(NotaEntrada).filter(NotaEntrada.tenant_id == tenant_id)

    if fornecedor and fornecedor.cnpj:
        cnpj_limpo = (
            fornecedor.cnpj.replace(".", "").replace("/", "").replace("-", "").strip()
        )
        query = query.filter(
            or_(
                NotaEntrada.fornecedor_id == pedido.fornecedor_id,
                func.replace(
                    func.replace(
                        func.replace(NotaEntrada.fornecedor_cnpj, ".", ""), "/", ""
                    ),
                    "-",
                    "",
                )
                == cnpj_limpo,
            )
        )
    elif fornecedor:
        query = query.filter(NotaEntrada.fornecedor_id == pedido.fornecedor_id)

    notas = query.order_by(desc(NotaEntrada.data_emissao)).limit(20).all()
    nota_ids_vinculadas = set(_ids_notas_vinculadas(db, pedido, tenant_id))

    result = []
    for n in notas:
        result.append(
            {
                "id": n.id,
                "numero_nota": n.numero_nota,
                "serie": n.serie,
                "chave_acesso": n.chave_acesso,
                "fornecedor_nome": n.fornecedor_nome,
                "data_emissao": n.data_emissao,
                "valor_total": n.valor_total,
                "status": n.status,
                "ja_vinculada": n.id in nota_ids_vinculadas,
            }
        )

    return {
        "notas": result,
        "nota_vinculada_id": pedido.nota_entrada_id,
        "nota_vinculada_ids": list(nota_ids_vinculadas),
    }


@router.post("/{pedido_id}/vincular-nota/{nota_id}")
def vincular_nota_e_confrontar(
    pedido_id: int,
    nota_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Vincula NF-e ao pedido e realiza o confronto completo."""
    from app.produtos_models import NotaEntrada

    current_user, tenant_id = current_user_and_tenant
    pedido = (
        db.query(PedidoCompra)
        .options(joinedload(PedidoCompra.itens))
        .filter(PedidoCompra.id == pedido_id, PedidoCompra.tenant_id == tenant_id)
        .first()
    )
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    nota = (
        db.query(NotaEntrada)
        .options(joinedload(NotaEntrada.itens))
        .filter(NotaEntrada.id == nota_id, NotaEntrada.tenant_id == tenant_id)
        .first()
    )
    if not nota:
        raise HTTPException(status_code=404, detail="Nota fiscal não encontrada")

    # Bloquear se NF já foi finalizada em outro pedido (vínculo permanente)
    if pedido.confronto_finalizado:
        raise HTTPException(status_code=400, detail="Confronto ja foi finalizado")

    outro_finalizado = _buscar_pedido_finalizado_da_nota(
        db, nota_id, pedido_id, tenant_id
    )
    if outro_finalizado:
        raise HTTPException(
            status_code=400,
            detail=f"Esta NF já está vinculada em definitivo ao pedido {outro_finalizado.numero_pedido}. Não é possível revinculá-la.",
        )

    _garantir_vinculo_legado(db, pedido, tenant_id, current_user.id)

    vinculo = (
        db.query(PedidoCompraNotaEntrada)
        .filter(
            PedidoCompraNotaEntrada.pedido_compra_id == pedido.id,
            PedidoCompraNotaEntrada.nota_entrada_id == nota_id,
            PedidoCompraNotaEntrada.tenant_id == tenant_id,
        )
        .first()
    )
    if not vinculo:
        db.add(
            PedidoCompraNotaEntrada(
                pedido_compra_id=pedido.id,
                nota_entrada_id=nota_id,
                user_id=current_user.id,
                tenant_id=tenant_id,
            )
        )
        db.flush()

    notas = _obter_notas_vinculadas(db, pedido, tenant_id, com_itens=True)
    confronto = _realizar_confronto(pedido, notas, db, tenant_id)

    # Salvar vínculo e resumo
    _salvar_confronto_pedido(pedido, notas, confronto)
    db.commit()

    return {
        "message": "Confronto realizado com sucesso",
        "pedido_id": pedido_id,
        "nota_id": nota_id,
        "nota_ids": [n.id for n in notas],
        "notas_entrada": _resumir_notas_confronto(notas),
        "confronto": confronto,
    }


@router.delete("/{pedido_id}/vincular-nota/{nota_id}")
def desvincular_nota_e_recalcular_confronto(
    pedido_id: int,
    nota_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Remove uma NF do confronto do pedido e recalcula com as restantes."""
    current_user, tenant_id = current_user_and_tenant
    pedido = (
        db.query(PedidoCompra)
        .options(joinedload(PedidoCompra.itens))
        .filter(PedidoCompra.id == pedido_id, PedidoCompra.tenant_id == tenant_id)
        .first()
    )
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido nao encontrado")
    if pedido.confronto_finalizado:
        raise HTTPException(status_code=400, detail="Confronto ja foi finalizado")

    _garantir_vinculo_legado(db, pedido, tenant_id, current_user.id)
    vinculo = (
        db.query(PedidoCompraNotaEntrada)
        .filter(
            PedidoCompraNotaEntrada.pedido_compra_id == pedido.id,
            PedidoCompraNotaEntrada.nota_entrada_id == nota_id,
            PedidoCompraNotaEntrada.tenant_id == tenant_id,
        )
        .first()
    )
    if vinculo:
        db.delete(vinculo)
        db.flush()
    if pedido.nota_entrada_id == nota_id:
        pedido.nota_entrada_id = None

    notas = _obter_notas_vinculadas(db, pedido, tenant_id, com_itens=True)
    if not notas:
        pedido.nota_entrada_id = None
        pedido.data_confronto = None
        pedido.status_confronto = None
        pedido.resumo_confronto = None
        pedido.updated_at = datetime.utcnow()
        db.commit()
        return {
            "message": "NF removida. Pedido sem NF vinculada.",
            "pedido_id": pedido_id,
            "nota_ids": [],
            "notas_entrada": [],
            "confronto": None,
        }

    confronto = _realizar_confronto(pedido, notas, db, tenant_id)
    _salvar_confronto_pedido(pedido, notas, confronto)
    db.commit()
    return {
        "message": "NF removida e confronto recalculado",
        "pedido_id": pedido_id,
        "nota_ids": [n.id for n in notas],
        "notas_entrada": _resumir_notas_confronto(notas),
        "confronto": confronto,
    }


@router.get("/{pedido_id}/confronto")
def obter_confronto_salvo(
    pedido_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Retorna o confronto salvo do pedido."""
    current_user, tenant_id = current_user_and_tenant
    pedido = (
        db.query(PedidoCompra)
        .filter(PedidoCompra.id == pedido_id, PedidoCompra.tenant_id == tenant_id)
        .first()
    )
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    notas = _obter_notas_vinculadas(db, pedido, tenant_id)
    if not notas:
        raise HTTPException(status_code=404, detail="Pedido não possui NF vinculada")

    return {
        "pedido_id": pedido_id,
        "nota_entrada_id": pedido.nota_entrada_id,
        "nota_entrada_ids": [n.id for n in notas],
        "numero_nota": _formatar_numeros_notas(notas),
        "notas_entrada": _resumir_notas_confronto(notas),
        "data_confronto": pedido.data_confronto,
        "status_confronto": pedido.status_confronto,
        "confronto_finalizado": pedido.confronto_finalizado or False,
        "confronto": json.loads(pedido.resumo_confronto)
        if pedido.resumo_confronto
        else None,
    }


@router.get("/{pedido_id}/confronto/csv")
def exportar_confronto_csv(
    pedido_id: int,
    filtros: Optional[str] = Query(
        None,
        description="Filtrar status separados por vírgula: ok,divergencia_quantidade,divergencia_preco,divergencia_mista,nao_encontrado,nao_pedido",
    ),
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Exporta o confronto do pedido em CSV."""
    _, tenant_id = current_user_and_tenant
    pedido, itens, resumo, numero_nota = _carregar_confronto_exportacao(
        db, pedido_id, tenant_id, filtros
    )

    def fmt(v):
        if v is None or v == "":
            return ""
        return str(v).replace(".", ",")

    linhas = [
        f"Pedido;{pedido.numero_pedido}",
        f"NF;{numero_nota}",
        "",
        "Produto;Código;Qtd Pedida;Qtd NF;Dif. Qtd;Preço Pedido (R$);Preço NF (R$);Dif. Unit. (R$);Dif. Preço (%);Valor Pedido (R$);Valor NF (R$);Dif. Valor (R$);Status",
    ]
    for it in itens:
        linhas.append(
            f"{it.get('produto_nome', '')};{it.get('produto_codigo', '')};{fmt(it.get('qtd_pedida', 0))};{fmt(it.get('qtd_nf', 0))};{fmt(it.get('dif_qtd', 0))};{fmt(it.get('preco_pedido', 0))};{fmt(it.get('preco_nf', 0))};{fmt(it.get('dif_preco_unit', ''))};{fmt(it.get('dif_preco_pct', 0))};{fmt(it.get('valor_pedido', 0))};{fmt(it.get('valor_nf', 0))};{fmt(it.get('dif_valor', 0))};{it.get('status', '')}"
        )
    linhas.append("")
    linhas.append(f";;Total Pedido (R$);;{fmt(resumo.get('total_pedido', 0))}")
    linhas.append(f";;Total NF (R$);;{fmt(resumo.get('total_nf', 0))}")
    linhas.append(f";;Diferença Total (R$);;{fmt(resumo.get('dif_total', 0))}")

    csv_content = "\n".join(linhas)
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename=confronto_{pedido.numero_pedido}.csv"
        },
    )


@router.get("/{pedido_id}/confronto/pdf")
def exportar_confronto_pdf(
    pedido_id: int,
    filtros: Optional[str] = Query(
        None, description="Filtrar status separados por vírgula"
    ),
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Exporta o confronto do pedido em PDF."""
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            SimpleDocTemplate,
            Table,
            TableStyle,
            Paragraph,
            Spacer,
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
    except ImportError:
        raise HTTPException(status_code=500, detail="reportlab não instalado")

    _, tenant_id = current_user_and_tenant
    pedido, itens, resumo, numero_nota = _carregar_confronto_exportacao(
        db, pedido_id, tenant_id, filtros
    )

    fornecedor = (
        db.query(Cliente)
        .filter(Cliente.id == pedido.fornecedor_id, Cliente.tenant_id == tenant_id)
        .first()
    )
    fornecedor_nome = (
        fornecedor.nome if fornecedor else f"Fornecedor {pedido.fornecedor_id}"
    )

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        leftMargin=10 * mm,
        rightMargin=10 * mm,
    )
    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "T",
        parent=styles["Heading1"],
        fontSize=16,
        textColor=colors.HexColor("#1a56db"),
        alignment=TA_CENTER,
        spaceAfter=8,
    )
    sub_style = ParagraphStyle("S", parent=styles["Normal"], fontSize=9, spaceAfter=4)
    small_style = ParagraphStyle(
        "Sm", parent=styles["Normal"], fontSize=6.5, leading=8, wordWrap="CJK"
    )

    def cell(valor):
        return Paragraph(escape(str(valor if valor is not None else "-")), small_style)

    elements.append(Paragraph("CONFRONTO PEDIDO x NOTA FISCAL", title_style))
    pedido_pdf = escape(str(pedido.numero_pedido or "-"))
    numero_nota_pdf = escape(str(numero_nota or "-"))
    fornecedor_pdf = escape(str(fornecedor_nome or "-"))
    data_confronto_pdf = escape(
        pedido.data_confronto.strftime("%d/%m/%Y %H:%M")
        if pedido.data_confronto
        else "-"
    )
    elements.append(
        Paragraph(
            f"Pedido: <b>{pedido_pdf}</b> &nbsp;|&nbsp; NF: <b>{numero_nota_pdf}</b> &nbsp;|&nbsp; Fornecedor: <b>{fornecedor_pdf}</b> &nbsp;|&nbsp; Data confronto: <b>{data_confronto_pdf}</b>",
            sub_style,
        )
    )
    elements.append(Spacer(1, 4 * mm))

    STATUS_LABELS = {
        "ok": "OK",
        "divergencia_quantidade": "Dif. Qtd",
        "divergencia_preco": "Dif. Preço",
        "divergencia_mista": "Dif. Mista",
        "nao_encontrado": "Não Recebido",
        "nao_pedido": "Não Pedido",
    }
    STATUS_COLORS = {
        "ok": colors.HexColor("#d1fae5"),
        "divergencia_quantidade": colors.HexColor("#fef3c7"),
        "divergencia_preco": colors.HexColor("#fef3c7"),
        "divergencia_mista": colors.HexColor("#fee2e2"),
        "nao_encontrado": colors.HexColor("#fee2e2"),
        "nao_pedido": colors.HexColor("#ede9fe"),
    }

    table_data = [
        [
            "Produto",
            "Cód.",
            "Qtd Ped.",
            "Qtd NF",
            "Dif.Qtd",
            "R$ Ped.",
            "R$ NF",
            "Dif.Unit",
            "Dif.%",
            "Vl.Ped.",
            "Vl.NF",
            "Dif.R$",
            "Status",
        ]
    ]
    row_colors = []

    for idx, it in enumerate(itens):
        st = it.get("status", "ok")
        row_colors.append((idx + 1, STATUS_COLORS.get(st, colors.white)))
        table_data.append(
            [
                cell(it.get("produto_nome", "")),
                cell(it.get("produto_codigo") or ""),
                cell(f"{it.get('qtd_pedida', 0):.2f}".rstrip("0").rstrip(".")),
                cell(f"{it.get('qtd_nf', 0):.2f}".rstrip("0").rstrip(".")),
                cell(f"{it.get('dif_qtd', 0):+.2f}".rstrip("0").rstrip(".")),
                cell(f"R$ {it.get('preco_pedido', 0):.2f}"),
                cell(f"R$ {it.get('preco_nf', 0):.2f}"),
                cell(
                    f"R$ {it.get('dif_preco_unit', 0):+.2f}"
                    if it.get("dif_preco_unit") is not None
                    else "-"
                ),
                cell(f"{it.get('dif_preco_pct', 0):+.1f}%"),
                cell(f"R$ {it.get('valor_pedido', 0):.2f}"),
                cell(f"R$ {it.get('valor_nf', 0):.2f}"),
                cell(f"R$ {it.get('dif_valor', 0):+.2f}"),
                cell(STATUS_LABELS.get(st, st)),
            ]
        )

    col_widths = [
        54 * mm,
        16 * mm,
        14 * mm,
        14 * mm,
        14 * mm,
        16 * mm,
        16 * mm,
        16 * mm,
        12 * mm,
        18 * mm,
        18 * mm,
        16 * mm,
        16 * mm,
    ]
    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a56db")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("ALIGN", (2, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]
    for row_idx, color in row_colors:
        style_cmds.append(("BACKGROUND", (0, row_idx), (-1, row_idx), color))
    t.setStyle(TableStyle(style_cmds))
    elements.append(t)
    elements.append(Spacer(1, 5 * mm))

    # Resumo financeiro
    resumo_data = [
        ["", "Total Produtos", "Frete", "Desconto"],
        [
            "Pedido",
            f"R$ {resumo.get('total_pedido', 0):.2f}",
            f"R$ {resumo.get('frete_pedido', 0):.2f}",
            f"R$ {resumo.get('desconto_pedido', 0):.2f}",
        ],
        [
            "NF",
            f"R$ {resumo.get('total_nf', 0):.2f}",
            f"R$ {resumo.get('frete_nf', 0):.2f}",
            f"R$ {resumo.get('desconto_nf', 0):.2f}",
        ],
        [
            "Diferença",
            f"R$ {resumo.get('dif_total', 0):+.2f}",
            f"R$ {(resumo.get('frete_nf', 0) - resumo.get('frete_pedido', 0)):+.2f}",
            "-",
        ],
    ]
    rt = Table(resumo_data, colWidths=[30 * mm, 45 * mm, 35 * mm, 35 * mm])
    rt.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    elements.append(rt)

    doc.build(elements)
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=confronto_{pedido.numero_pedido}.pdf"
        },
    )


@router.get("/{pedido_id}/confronto/email-texto")
def gerar_email_confronto(
    pedido_id: int,
    filtros: Optional[str] = Query(
        None, description="Filtrar status separados por vírgula"
    ),
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Gera texto de e-mail para enviar ao fornecedor com as divergências."""
    _, tenant_id = current_user_and_tenant
    pedido, itens, resumo, numero_nota = _carregar_confronto_exportacao(
        db, pedido_id, tenant_id, filtros, None
    )

    fornecedor = (
        db.query(Cliente)
        .filter(Cliente.id == pedido.fornecedor_id, Cliente.tenant_id == tenant_id)
        .first()
    )
    fornecedor_nome = fornecedor.nome if fornecedor else "Fornecedor"

    divergencias = [i for i in itens if i.get("status") != "ok"]

    linhas_divergencia = []
    for d in divergencias:
        partes = []
        st = d.get("status")
        if st in ("divergencia_quantidade", "divergencia_mista", "nao_encontrado"):
            partes.append(
                f"qtd. pedida: {d['qtd_pedida']}, qtd. recebida: {d['qtd_nf']}"
            )
        if st in ("divergencia_preco", "divergencia_mista"):
            partes.append(
                f"preço pedido: R$ {d['preco_pedido']:.2f}, preço NF: R$ {d['preco_nf']:.2f} ({d['dif_preco_pct']:+.1f}%)"
            )
        if st == "nao_pedido":
            partes.append("produto não constava no pedido")
        linhas_divergencia.append(f"- {d['produto_nome']}: {'; '.join(partes)}")

    dif_total = resumo.get("dif_total", 0)
    sinal = "a maior" if dif_total > 0 else "a menor"

    corpo = f"""Assunto: Divergências na NF {numero_nota} referente ao pedido {pedido.numero_pedido}

Prezados {fornecedor_nome},

Ao realizar a conferência do pedido {pedido.numero_pedido} com a nota fiscal recebida, identificamos as seguintes divergências:

{chr(10).join(linhas_divergencia)}

Resumo financeiro:
- Total do pedido: R$ {resumo.get("total_pedido", 0):.2f}
- Total da NF:     R$ {resumo.get("total_nf", 0):.2f}
- Diferença:       R$ {abs(dif_total):.2f} {sinal}

Solicitamos gentilmente que nos informem o motivo das divergências e, se aplicável, o prazo para envio dos itens faltantes ou emissão de nota de crédito pela diferença de valores.

Ficamos à disposição para esclarecimentos.

Atenciosamente,
[Seu nome]
"""

    return {"texto": corpo, "divergencias_count": len(divergencias)}


@router.post("/{pedido_id}/finalizar-confronto")
def finalizar_confronto(
    pedido_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Finaliza o confronto, criando vínculo permanente entre pedido e NF (1-para-1)."""
    current_user, tenant_id = current_user_and_tenant
    pedido = (
        db.query(PedidoCompra)
        .filter(PedidoCompra.id == pedido_id, PedidoCompra.tenant_id == tenant_id)
        .first()
    )
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    _garantir_vinculo_legado(db, pedido, tenant_id, current_user.id)
    notas = _obter_notas_vinculadas(db, pedido, tenant_id)
    if not notas or not pedido.resumo_confronto:
        raise HTTPException(
            status_code=400, detail="Pedido não possui confronto realizado"
        )
    if pedido.confronto_finalizado:
        raise HTTPException(status_code=400, detail="Confronto já foi finalizado")
    # Verificar se esta NF já está finalizada em outro pedido
    for nota in notas:
        outro_finalizado = _buscar_pedido_finalizado_da_nota(
            db, nota.id, pedido_id, tenant_id
        )
        if outro_finalizado:
            raise HTTPException(
                status_code=400,
                detail=f"Esta NF ja esta vinculada ao pedido {outro_finalizado.numero_pedido}. Uma NF so pode ser finalizada em um pedido.",
            )

    outro = (
        db.query(PedidoCompra)
        .filter(
            PedidoCompra.nota_entrada_id == pedido.nota_entrada_id,
            PedidoCompra.confronto_finalizado,
            PedidoCompra.id != pedido_id,
            PedidoCompra.tenant_id == tenant_id,
        )
        .first()
    )
    if outro:
        raise HTTPException(
            status_code=400,
            detail=f"Esta NF já está vinculada ao pedido {outro.numero_pedido}. Uma NF só pode ser confrontada com um pedido.",
        )
    pedido.confronto_finalizado = True
    pedido.updated_at = datetime.utcnow()
    db.commit()
    return {
        "message": "Confronto finalizado com sucesso",
        "pedido_id": pedido_id,
        "numero_pedido": pedido.numero_pedido,
        "nota_entrada_id": pedido.nota_entrada_id,
        "nota_entrada_ids": [n.id for n in notas],
        "notas_entrada": _resumir_notas_confronto(notas),
    }


@router.post("/{pedido_id}/sugerir-pedido-complementar")
def sugerir_pedido_complementar(
    pedido_id: int,
    db: Session = Depends(get_session),
    current_user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Cria pedido rascunho com os itens faltantes após o confronto."""
    current_user, tenant_id = current_user_and_tenant
    pedido = (
        db.query(PedidoCompra)
        .filter(PedidoCompra.id == pedido_id, PedidoCompra.tenant_id == tenant_id)
        .first()
    )
    if not pedido or not pedido.resumo_confronto:
        raise HTTPException(status_code=404, detail="Confronto não encontrado")

    confronto = json.loads(pedido.resumo_confronto)
    itens_faltantes = [
        i
        for i in confronto.get("itens", [])
        if i.get("status") in ("nao_encontrado", "divergencia_quantidade")
        and i.get("dif_qtd", 0) < 0
    ]

    if not itens_faltantes:
        raise HTTPException(
            status_code=400,
            detail="Não há itens faltantes para criar pedido complementar",
        )

    # Gerar número do pedido
    ultimo = db.query(PedidoCompra).order_by(desc(PedidoCompra.id)).first()
    numero = (ultimo.id + 1) if ultimo else 1
    numero_pedido = f"PC{datetime.now().year}{numero:05d}-C"

    valor_total = 0.0
    itens_novos = []
    for it in itens_faltantes:
        qtd_faltante = abs(it.get("dif_qtd", 0))
        preco = it.get("preco_pedido", 0)
        valor_item = qtd_faltante * preco
        valor_total += valor_item
        itens_novos.append(
            {
                "produto_id": it["produto_id"],
                "qtd": qtd_faltante,
                "preco": preco,
                "valor": valor_item,
            }
        )

    # Criar pedido complementar
    novo_pedido = PedidoCompra(
        numero_pedido=numero_pedido,
        fornecedor_id=pedido.fornecedor_id,
        status="rascunho",
        valor_total=valor_total,
        valor_frete=0,
        valor_desconto=0,
        valor_final=valor_total,
        data_pedido=datetime.utcnow(),
        observacoes=f"Pedido complementar gerado automaticamente após confronto com NF. Pedido original: {pedido.numero_pedido}",
        user_id=current_user.id,
        tenant_id=tenant_id,
    )
    db.add(novo_pedido)
    db.flush()

    for it in itens_novos:
        item = PedidoCompraItem(
            pedido_compra_id=novo_pedido.id,
            produto_id=it["produto_id"],
            quantidade_pedida=it["qtd"],
            quantidade_recebida=0,
            preco_unitario=it["preco"],
            desconto_item=0,
            valor_total=it["valor"],
            status="pendente",
            tenant_id=tenant_id,
        )
        db.add(item)

    db.commit()

    return {
        "message": "Pedido complementar criado em rascunho",
        "pedido_complementar_id": novo_pedido.id,
        "numero_pedido": numero_pedido,
        "itens_faltantes": len(itens_novos),
        "valor_total": valor_total,
    }
