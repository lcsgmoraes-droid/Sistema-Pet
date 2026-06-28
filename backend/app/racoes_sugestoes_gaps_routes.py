"""Rotas de identificacao de gaps de estoque de racoes."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.produtos_models import Produto
from app.racoes_sugestoes_common import _validar_tenant_e_obter_usuario
from app.racoes_sugestoes_schemas import GapEstoque
from app.vendas_models import Venda, VendaItem


router = APIRouter()

_CAMPO_SEGMENTO_MAP = {
    "porte": "porte_animal",
    "fase": "fase_publico",
    "sabor": "sabor_proteina",
    "linha": "linha_racao",
    "especie": "especie_animal",
}


@router.get("/gaps-estoque", response_model=list[GapEstoque])
async def identificar_gaps_estoque(
    tipo_segmento: str = Query("porte", description="porte, fase, sabor, linha"),
    dias_analise: int = Query(
        90, ge=30, le=365, description="Dias para cálculo de importância"
    ),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    if tipo_segmento not in _CAMPO_SEGMENTO_MAP:
        raise HTTPException(400, "Tipo de segmento inválido")

    produtos = (
        db.query(Produto)
        .filter(
            Produto.tenant_id == tenant_id,
            Produto.tipo == "ração",
            Produto.ativo.is_(True),
        )
        .all()
    )
    segmentos_dict = _agrupar_produtos_por_segmento(
        produtos, campo_nome=_CAMPO_SEGMENTO_MAP[tipo_segmento]
    )
    faturamento_total = _preencher_faturamento_segmentos(
        db,
        segmentos_dict,
        tenant_id=tenant_id,
        data_limite=datetime.now() - timedelta(days=dias_analise),
    )

    gaps = [
        gap
        for segmento, dados in segmentos_dict.items()
        if (
            gap := _montar_gap_segmento(
                segmento,
                dados,
                tipo_segmento=tipo_segmento,
                faturamento_total=faturamento_total,
            )
        )
    ]
    ordem_importancia = {"Alta": 3, "Média": 2, "Baixa": 1}
    gaps.sort(
        key=lambda x: (
            ordem_importancia.get(x.importancia, 0),
            x.percentual_sem_estoque,
        ),
        reverse=True,
    )
    return gaps


def _agrupar_produtos_por_segmento(
    produtos: list[Produto], *, campo_nome: str
) -> dict[str, dict]:
    segmentos_dict = {}
    for produto in produtos:
        valor_campo = getattr(produto, campo_nome)
        segmentos = valor_campo if isinstance(valor_campo, list) else []
        if not isinstance(valor_campo, list) and valor_campo:
            segmentos = [valor_campo]

        for segmento in segmentos:
            if not segmento:
                continue
            if segmento not in segmentos_dict:
                segmentos_dict[segmento] = {
                    "produtos": [],
                    "sem_estoque": 0,
                    "faturamento": 0,
                }

            segmentos_dict[segmento]["produtos"].append(produto.id)
            if not produto.estoque_atual or produto.estoque_atual <= 0:
                segmentos_dict[segmento]["sem_estoque"] += 1

    return segmentos_dict


def _preencher_faturamento_segmentos(
    db: Session,
    segmentos_dict: dict[str, dict],
    *,
    tenant_id: str,
    data_limite: datetime,
) -> float:
    faturamento_total = 0.0
    for dados in segmentos_dict.values():
        produto_ids = dados["produtos"]
        faturamento = (
            db.query(func.sum(VendaItem.preco_unitario * VendaItem.quantidade))
            .join(Venda, VendaItem.venda_id == Venda.id)
            .filter(
                Venda.tenant_id == tenant_id,
                VendaItem.produto_id.in_(produto_ids),
                Venda.data_venda >= data_limite,
                Venda.status != "cancelada",
            )
            .scalar()
            or 0
        )
        dados["faturamento"] = float(faturamento)
        faturamento_total += float(faturamento)

    return faturamento_total


def _montar_gap_segmento(
    segmento: str,
    dados: dict,
    *,
    tipo_segmento: str,
    faturamento_total: float,
) -> GapEstoque | None:
    total_produtos = len(dados["produtos"])
    sem_estoque = dados["sem_estoque"]
    percentual_sem_estoque = (
        (sem_estoque / total_produtos * 100) if total_produtos > 0 else 0
    )
    if percentual_sem_estoque < 50:
        return None

    faturamento = dados["faturamento"]
    percentual_faturamento = (
        (faturamento / faturamento_total * 100) if faturamento_total > 0 else 0
    )
    importancia = _classificar_importancia(percentual_faturamento)

    return GapEstoque(
        segmento_tipo=tipo_segmento,
        segmento_valor=segmento,
        total_produtos=total_produtos,
        produtos_sem_estoque=sem_estoque,
        percentual_sem_estoque=round(percentual_sem_estoque, 1),
        importancia=importancia,
        faturamento_historico=round(faturamento, 2),
        sugestao=_sugestao_gap(
            importancia, percentual_faturamento, percentual_sem_estoque
        ),
    )


def _classificar_importancia(percentual_faturamento: float) -> str:
    if percentual_faturamento >= 10:
        return "Alta"
    if percentual_faturamento >= 5:
        return "Média"
    return "Baixa"


def _sugestao_gap(
    importancia: str, percentual_faturamento: float, percentual_sem_estoque: float
) -> str:
    if importancia == "Alta":
        return f"URGENTE: Segmento gera {percentual_faturamento:.1f}% do faturamento. Repor estoque imediatamente!"
    if importancia == "Média":
        return f"ATENÇÃO: Segmento importante com {percentual_sem_estoque:.1f}% de produtos sem estoque."
    return "Considerar reposição ou descontinuar produtos."


__all__ = ["identificar_gaps_estoque", "router"]
