"""Relatorio consolidado das sugestoes inteligentes de racoes."""

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.produtos_models import Produto
from app.racoes_sugestoes_common import _validar_tenant_e_obter_usuario
from app.racoes_sugestoes_duplicatas_routes import detectar_duplicatas
from app.racoes_sugestoes_gaps_routes import identificar_gaps_estoque
from app.racoes_sugestoes_padronizacao_routes import sugerir_padronizacao_nomes


router = APIRouter()


@router.get("/relatorio-completo")
async def obter_relatorio_completo(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    total_produtos = (
        db.query(func.count(Produto.id))
        .filter(
            Produto.tenant_id == tenant_id,
            Produto.tipo == "ração",
            Produto.ativo.is_(True),
        )
        .scalar()
        or 0
    )

    duplicatas_response = await detectar_duplicatas(
        threshold_similaridade=0.85,
        apenas_ativas=True,
        user_and_tenant=user_and_tenant,
        db=db,
    )
    padronizacao_response = await sugerir_padronizacao_nomes(
        limite=100, user_and_tenant=user_and_tenant, db=db
    )
    gaps_response = await identificar_gaps_estoque(
        tipo_segmento="porte", dias_analise=90, user_and_tenant=user_and_tenant, db=db
    )

    total_duplicatas = len(duplicatas_response)
    total_padronizacoes = len(padronizacao_response)
    gaps_criticos = [g for g in gaps_response if g.importancia == "Alta"]
    score_saude = _calcular_score_saude(
        total_produtos=total_produtos,
        total_duplicatas=total_duplicatas,
        total_padronizacoes=total_padronizacoes,
        total_gaps_criticos=len(gaps_criticos),
    )
    classificacao, cor = _classificar_score_saude(score_saude)

    return {
        "score_saude": round(score_saude, 1),
        "classificacao": classificacao,
        "cor": cor,
        "total_produtos": total_produtos,
        "resumo": {
            "duplicatas_detectadas": total_duplicatas,
            "nomes_padronizar": total_padronizacoes,
            "gaps_criticos": len(gaps_criticos),
        },
        "top_duplicatas": duplicatas_response[:5] if duplicatas_response else [],
        "top_padronizacoes": padronizacao_response[:10]
        if padronizacao_response
        else [],
        "gaps_estoque": gaps_criticos,
        "recomendacoes": [
            f"Revisar {total_duplicatas} possíveis duplicatas"
            if total_duplicatas > 0
            else None,
            f"Padronizar {total_padronizacoes} nomes de produtos"
            if total_padronizacoes > 0
            else None,
            f"Repor estoque em {len(gaps_criticos)} segmentos críticos"
            if len(gaps_criticos) > 0
            else None,
        ],
    }


def _calcular_score_saude(
    *,
    total_produtos: int,
    total_duplicatas: int,
    total_padronizacoes: int,
    total_gaps_criticos: int,
) -> float:
    score_saude = 100.0
    if total_produtos > 0:
        percentual_duplicatas = (total_duplicatas / total_produtos) * 100
        percentual_padronizacao = (total_padronizacoes / total_produtos) * 100
        score_saude -= min(percentual_duplicatas * 3, 30)
        score_saude -= min(percentual_padronizacao * 2, 20)

    score_saude -= min(total_gaps_criticos * 10, 50)
    return max(score_saude, 0)


def _classificar_score_saude(score_saude: float) -> tuple[str, str]:
    if score_saude >= 90:
        return "Excelente", "green"
    if score_saude >= 70:
        return "Bom", "blue"
    if score_saude >= 50:
        return "Regular", "yellow"
    return "Crítico", "red"


__all__ = ["obter_relatorio_completo", "router"]
