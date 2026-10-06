"""Endpoints principais da DRE."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, extract
from sqlalchemy.orm import Session

from .auth.dependencies import get_current_user_and_tenant
from .db import get_session
from .dre_canais.base import CANAIS_CONFIG, _filtro_status_venda_dre
from .dre_canais.contas import (
    classificacoes_contas_pagar,
    eh_compra_estoque,
    ids_fretes_sobre_compras,
)
from .dre_export_routes import _dre_para_exportacao
from .dre_schemas import DREDetalhado, DREResponse
from .financeiro_models import ContaPagar
from .vendas_models import Venda

router = APIRouter(prefix="/financeiro/dre", tags=["DRE"])


@router.get("", response_model=DREResponse)
def gerar_dre(
    ano: int = Query(..., description="Ano do DRE"),
    mes: int = Query(..., description="Mês do DRE (1-12)"),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Gera DRE (Demonstração do Resultado do Exercício) automaticamente

    O sistema categoriza automaticamente todas as transações e gera
    um relatório contábil completo seguindo as normas brasileiras.
    """

    if mes < 1 or mes > 12:
        raise HTTPException(status_code=400, detail="Mês deve estar entre 1 e 12")

    # O formato antigo continua estável; os valores vêm da DRE por canais.
    return _dre_para_exportacao(
        ano=ano,
        mes=mes,
        mes_inicial=mes,
        data_final=None,
        canais=",".join(CANAIS_CONFIG),
        db=db,
        user_and_tenant=user_and_tenant,
    )


@router.get("/detalhado", response_model=DREDetalhado)
def gerar_dre_detalhado(
    ano: int = Query(..., description="Ano do DRE"),
    mes: int = Query(..., description="Mês do DRE (1-12)"),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Gera DRE com detalhamento de cada categoria de despesa e receita
    """

    # Gera o DRE básico
    _current_user, tenant_id = user_and_tenant
    dre = gerar_dre(ano=ano, mes=mes, db=db, user_and_tenant=user_and_tenant)

    # Busca detalhes das despesas pela mesma elegibilidade do total.
    # ✅ USA DATA_EMISSAO (regime de competência)
    contas_pagar = (
        db.query(ContaPagar)
        .filter(
            and_(
                extract("month", ContaPagar.data_emissao) == mes,  # ✅ Competência
                extract("year", ContaPagar.data_emissao) == ano,
                ContaPagar.tenant_id == tenant_id,
                ContaPagar.status != "cancelado",
                ContaPagar.status != "parcelado",
                ContaPagar.afeta_dre.is_(True),
                ContaPagar.nota_entrada_id.is_(None),
            )
        )
        .all()
    )
    tipos, categorias = classificacoes_contas_pagar(db, tenant_id, contas_pagar)
    frete_ids = ids_fretes_sobre_compras(db, tenant_id)

    detalhes_despesas = [
        {
            "descricao": conta.descricao,
            "valor": float(conta.valor_original),
            "vencimento": conta.data_vencimento.isoformat()
            if conta.data_vencimento
            else None,
            "pago": conta.status == "pago",
        }
        for conta in contas_pagar
        if conta.dre_subcategoria_id in frete_ids
        or not eh_compra_estoque(conta, tipos, categorias)
    ]

    # Busca detalhes das receitas (vendas)
    vendas = (
        db.query(Venda)
        .filter(
            and_(
                extract("month", Venda.data_venda) == mes,
                extract("year", Venda.data_venda) == ano,
                Venda.tenant_id == tenant_id,
                _filtro_status_venda_dre(),
            )
        )
        .all()
    )

    detalhes_receitas = [
        {
            "numero_venda": venda.numero_venda,
            "data": venda.data_venda.isoformat(),
            "valor_bruto": float(venda.subtotal + (venda.taxa_entrega or 0)),
            "desconto": float(venda.desconto or 0),
            "valor_liquido": float(venda.total),
        }
        for venda in vendas
    ]

    # Comparação com mês anterior (opcional)
    mes_anterior = mes - 1 if mes > 1 else 12
    ano_anterior = ano if mes > 1 else ano - 1

    try:
        dre_anterior = gerar_dre(
            ano=ano_anterior,
            mes=mes_anterior,
            db=db,
            user_and_tenant=user_and_tenant,
        )
        comparacao = {
            "receita_bruta_variacao": float(
                dre.receita_bruta - dre_anterior.receita_bruta
            ),
            "lucro_liquido_variacao": float(
                dre.lucro_liquido - dre_anterior.lucro_liquido
            ),
            "margem_liquida_variacao": dre.margem_liquida - dre_anterior.margem_liquida,
        }
    except Exception:
        comparacao = None

    return DREDetalhado(
        dre=dre,
        detalhes_despesas=detalhes_despesas,
        detalhes_receitas=detalhes_receitas,
        comparacao_mes_anterior=comparacao,
    )
