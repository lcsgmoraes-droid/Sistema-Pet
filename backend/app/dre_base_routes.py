"""Endpoints principais da DRE."""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, extract
from sqlalchemy.orm import Session

from .auth.dependencies import get_current_user_and_tenant
from .db import get_session
from .dre_calculos import (
    calcular_cmv,
    calcular_frete_notas_entrada,
    calcular_taxas_cartao,
    obter_despesas_por_categoria,
)
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

    # Nome do mês
    _current_user, tenant_id = user_and_tenant

    meses = [
        "",
        "Janeiro",
        "Fevereiro",
        "Março",
        "Abril",
        "Maio",
        "Junho",
        "Julho",
        "Agosto",
        "Setembro",
        "Outubro",
        "Novembro",
        "Dezembro",
    ]
    periodo = f"{meses[mes]}/{ano}"

    # ========== 1. RECEITAS ==========

    # Vendas de produtos e serviços
    vendas = (
        db.query(Venda)
        .filter(
            and_(
                extract("month", Venda.data_venda) == mes,
                extract("year", Venda.data_venda) == ano,
                Venda.tenant_id == tenant_id,
                Venda.status.in_(["finalizada", "pago_nf", "baixa_parcial"]),
            )
        )
        .all()
    )

    receita_bruta = sum([v.subtotal + (v.taxa_entrega or 0) for v in vendas])
    vendas_produtos = receita_bruta  # Por enquanto, tudo como produtos
    vendas_servicos = Decimal("0")
    outras_receitas = Decimal("0")  # Pode buscar de lançamentos manuais

    # ========== 2. DEDUÇÕES ==========

    descontos = sum([v.desconto_valor or 0 for v in vendas])
    devolucoes = Decimal("0")  # Implementar quando tiver sistema de devoluções
    deducoes_total = descontos + devolucoes

    # ========== 3. RECEITA LÍQUIDA ==========

    receita_liquida = receita_bruta - deducoes_total

    # ========== 4. CMV ==========

    cmv = calcular_cmv(db, mes, ano, tenant_id)

    # ========== 5. LUCRO BRUTO ==========

    lucro_bruto = receita_liquida - cmv
    margem_bruta = float(
        (lucro_bruto / receita_bruta * 100) if receita_bruta > 0 else 0
    )

    # ========== 6. DESPESAS OPERACIONAIS ==========

    categorias_despesas = obter_despesas_por_categoria(db, mes, ano, tenant_id)
    taxas_cartao = calcular_taxas_cartao(db, mes, ano, tenant_id)
    frete_compras = calcular_frete_notas_entrada(
        db, mes, ano, tenant_id
    )  # Frete de notas de entrada

    despesas_pessoal = categorias_despesas["Despesas com Pessoal"]
    despesas_administrativas = (
        categorias_despesas["Despesas Administrativas"]
        + categorias_despesas["Despesas com Ocupação"]
    )
    outras_despesas = (
        categorias_despesas["Despesas com Vendas"]
        + categorias_despesas["Outras Despesas"]
        + frete_compras  # Adiciona frete das notas de entrada
    )

    despesas_operacionais = (
        despesas_pessoal + despesas_administrativas + taxas_cartao + outras_despesas
    )

    # ========== 7. RESULTADO OPERACIONAL ==========

    resultado_operacional = lucro_bruto - despesas_operacionais
    margem_operacional = float(
        (resultado_operacional / receita_bruta * 100) if receita_bruta > 0 else 0
    )

    # ========== 8. RESULTADO FINANCEIRO ==========

    receitas_financeiras = Decimal("0")  # Juros recebidos, etc
    despesas_financeiras = Decimal("0")  # Juros pagos, multas, etc
    resultado_financeiro = receitas_financeiras - despesas_financeiras

    # ========== 9. LUCRO LÍQUIDO ==========

    lucro_liquido = resultado_operacional + resultado_financeiro
    margem_liquida = float(
        (lucro_liquido / receita_bruta * 100) if receita_bruta > 0 else 0
    )

    # ========== RETORNO ==========

    dre = DREResponse(
        periodo=periodo,
        mes=mes,
        ano=ano,
        receita_bruta=receita_bruta,
        vendas_produtos=vendas_produtos,
        vendas_servicos=vendas_servicos,
        outras_receitas=outras_receitas,
        deducoes_total=deducoes_total,
        descontos=descontos,
        devolucoes=devolucoes,
        receita_liquida=receita_liquida,
        cmv=cmv,
        lucro_bruto=lucro_bruto,
        margem_bruta=margem_bruta,
        despesas_operacionais=despesas_operacionais,
        despesas_pessoal=despesas_pessoal,
        despesas_administrativas=despesas_administrativas,
        taxas_cartao=taxas_cartao,
        outras_despesas=outras_despesas,
        resultado_operacional=resultado_operacional,
        margem_operacional=margem_operacional,
        resultado_financeiro=resultado_financeiro,
        receitas_financeiras=receitas_financeiras,
        despesas_financeiras=despesas_financeiras,
        lucro_liquido=lucro_liquido,
        margem_liquida=margem_liquida,
    )

    return dre


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

    # Busca detalhes das despesas (EXCLUINDO fornecedores)
    # ✅ USA DATA_EMISSAO (regime de competência)
    contas_pagar = (
        db.query(ContaPagar)
        .filter(
            and_(
                extract("month", ContaPagar.data_emissao) == mes,  # ✅ Competência
                extract("year", ContaPagar.data_emissao) == ano,
                ContaPagar.tenant_id == tenant_id,
                ContaPagar.fornecedor_id.is_(None),  # EXCLUI pagamentos a fornecedores
                ContaPagar.status != "cancelado",
            )
        )
        .all()
    )

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
    ]

    # Busca detalhes das receitas (vendas)
    vendas = (
        db.query(Venda)
        .filter(
            and_(
                extract("month", Venda.data_venda) == mes,
                extract("year", Venda.data_venda) == ano,
                Venda.tenant_id == tenant_id,
                Venda.status.in_(["finalizada", "pago_nf", "baixa_parcial"]),
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
