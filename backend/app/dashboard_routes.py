"""
Rotas para Dashboard Financeiro
Endpoints para dados consolidados do sistema
"""

# ruff: noqa: F401

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from typing import Optional
import logging

from .db import get_session
from .auth.dependencies import get_current_user_and_tenant
from .models import Cliente
from .vendas_models import Venda, VendaItem
from .financeiro_models import ContaReceber, ContaPagar
from .produtos_models import Produto
from .utils.tenant_safe_sql import execute_tenant_safe
from .dashboard.ponto_equilibrio_routes import (
    router as ponto_equilibrio_router,
    obter_ponto_equilibrio,
    obter_ponto_equilibrio_detalhes,
)
from .dashboard.ponto_equilibrio import (
    MARGEM_PONTO_EQUILIBRIO_OPCOES,
    MARGEM_PONTO_EQUILIBRIO_PADRAO,
    MODO_CUSTO_FISCAL_PE_OPCOES,
    MODO_CUSTO_FISCAL_PE_PADRAO,
    PE_TERMOS_FIXOS,
    PE_TERMOS_FOLHA,
    PE_TERMOS_VARIAVEIS,
    PONTO_EQUILIBRIO_GRUPOS_CLASSIFICACAO,
    _adicionar_meses,
    _ajustar_snapshot_custo_fiscal_pe,
    _calcular_complemento_folha_gerencial,
    _calcular_despesas_variaveis_margem_pe,
    _calcular_folha_gerencial_estimada,
    _calcular_margem_periodo_ponto_equilibrio,
    _calcular_margem_referencia_ponto_equilibrio,
    _classificar_conta_ponto_equilibrio,
    _classificar_texto_ponto_equilibrio,
    _conta_eh_compra_estoque_para_pe,
    _conta_eh_folha_para_pe,
    _conta_variavel_ja_coberta_pelo_snapshot_pe,
    _detalhe_conta_pe,
    _detalhe_sintetico_pe,
    _detalhe_venda_margem_pe,
    _filtro_status_venda_relatorio,
    _formatar_data_br_ponto_equilibrio,
    _normalizar_item_detalhe_ponto_equilibrio,
    _normalizar_texto_pe,
    _normalizar_tipo_custo_dre,
    _paginar_detalhes_ponto_equilibrio,
    _periodo_meses_fechados_para_margem,
    _preparar_snapshots_margem_vendas_pe,
    _round_money,
    _snapshot_float,
    _somar_componentes_margem_vendas_pe,
    _venda_tem_documento_fiscal_pe,
)

logger = logging.getLogger(__name__)

router = APIRouter()
router.include_router(ponto_equilibrio_router)


def _dashboard_fetchone(db: Session, sql: str, tenant_id, params=None):
    return execute_tenant_safe(db, sql, params or {}, tenant_id=tenant_id).fetchone()


@router.get("/dashboard/resumo")
async def obter_resumo_dashboard(
    periodo_dias: int = 30,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Retorna resumo consolidado para o dashboard financeiro
    """
    current_user, tenant_id = user_and_tenant
    try:
        hoje = datetime.now()
        inicio_periodo = hoje - timedelta(days=periodo_dias)

        # ========================================
        # 1. SALDO ATUAL (Baseado em vendas pagas)
        # ========================================
        vendas_pagas = (
            db.query(func.sum(Venda.total))
            .filter(and_(Venda.tenant_id == tenant_id, Venda.status == "finalizada"))
            .scalar()
            or 0
        )

        contas_pagas_total = (
            db.query(func.sum(ContaPagar.valor_pago))
            .filter(ContaPagar.tenant_id == tenant_id)
            .scalar()
            or 0
        )

        saldo_atual = vendas_pagas - contas_pagas_total

        # ========================================
        # 2. CONTAS A RECEBER
        # ========================================
        contas_receber_total = (
            db.query(func.sum(ContaReceber.valor_final - ContaReceber.valor_recebido))
            .filter(
                and_(
                    ContaReceber.tenant_id == tenant_id,
                    ContaReceber.status.in_(["pendente", "parcial", "vencida"]),
                )
            )
            .scalar()
            or 0
        )

        # Contas vencidas a receber
        contas_receber_vencidas = (
            db.query(func.sum(ContaReceber.valor_final - ContaReceber.valor_recebido))
            .filter(
                and_(
                    ContaReceber.tenant_id == tenant_id,
                    ContaReceber.status.in_(["pendente", "parcial", "vencida"]),
                    ContaReceber.data_vencimento < hoje,
                )
            )
            .scalar()
            or 0
        )

        # ========================================
        # 3. CONTAS A PAGAR
        # ========================================
        contas_pagar_total = (
            db.query(func.sum(ContaPagar.valor_final - ContaPagar.valor_pago))
            .filter(
                and_(
                    ContaPagar.tenant_id == tenant_id,
                    ContaPagar.status.in_(["pendente", "parcial", "vencida"]),
                )
            )
            .scalar()
            or 0
        )

        # Contas vencidas a pagar
        contas_pagar_vencidas = (
            db.query(func.sum(ContaPagar.valor_final - ContaPagar.valor_pago))
            .filter(
                and_(
                    ContaPagar.tenant_id == tenant_id,
                    ContaPagar.status.in_(["pendente", "parcial", "vencida"]),
                    ContaPagar.data_vencimento < hoje,
                )
            )
            .scalar()
            or 0
        )

        # ========================================
        # 4. VENDAS DO PERÍODO
        # ========================================
        vendas_periodo = (
            db.query(
                func.count(Venda.id).label("quantidade"),
                func.sum(Venda.total).label("valor_total"),
                func.sum(Venda.subtotal).label("faturamento_bruto"),
            )
            .filter(
                and_(Venda.tenant_id == tenant_id, Venda.data_venda >= inicio_periodo)
            )
            .first()
        )

        total_vendas_periodo = vendas_periodo.valor_total or 0
        quantidade_vendas_periodo = vendas_periodo.quantidade or 0
        faturamento_bruto_periodo = vendas_periodo.faturamento_bruto or 0

        # Vendas finalizadas
        vendas_finalizadas = (
            db.query(func.sum(Venda.total))
            .filter(
                and_(
                    Venda.tenant_id == tenant_id,
                    Venda.data_venda >= inicio_periodo,
                    Venda.status == "finalizada",
                )
            )
            .scalar()
            or 0
        )

        # ========================================
        # 5. ENTRADAS E SAÍDAS DO PERÍODO (baseado em vendas e contas)
        # ========================================
        entradas_periodo = (
            db.query(func.sum(Venda.total))
            .filter(
                and_(
                    Venda.tenant_id == tenant_id,
                    Venda.data_venda >= inicio_periodo,
                    Venda.status == "finalizada",
                )
            )
            .scalar()
            or 0
        )

        saidas_periodo = (
            db.query(func.sum(ContaPagar.valor_pago))
            .filter(
                and_(
                    ContaPagar.tenant_id == tenant_id,
                    ContaPagar.data_pagamento >= inicio_periodo,
                )
            )
            .scalar()
            or 0
        )

        # ========================================
        # 6. LUCRO DO PERÍODO
        # ========================================
        lucro_periodo = entradas_periodo - saidas_periodo

        # ========================================
        # 7. TICKET MÉDIO
        # ========================================
        ticket_medio = (
            (total_vendas_periodo / quantidade_vendas_periodo)
            if quantidade_vendas_periodo > 0
            else 0
        )

        # ========================================
        # RETORNO
        # ========================================
        return {
            "saldo_atual": round(saldo_atual, 2),
            "contas_receber": {
                "total": round(contas_receber_total, 2),
                "vencidas": round(contas_receber_vencidas, 2),
            },
            "contas_pagar": {
                "total": round(contas_pagar_total, 2),
                "vencidas": round(contas_pagar_vencidas, 2),
            },
            "vendas_periodo": {
                "quantidade": quantidade_vendas_periodo,
                "valor_total": round(total_vendas_periodo, 2),
                "faturamento_bruto": round(float(faturamento_bruto_periodo), 2),
                "finalizadas": round(vendas_finalizadas, 2),
                "ticket_medio": round(ticket_medio, 2),
            },
            "fluxo_periodo": {
                "entradas": round(entradas_periodo, 2),
                "saidas": round(saidas_periodo, 2),
                "lucro": round(lucro_periodo, 2),
            },
            "periodo_dias": periodo_dias,
        }

    except Exception as e:
        logger.error(f"Erro ao obter resumo do dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/entradas-saidas")
async def obter_entradas_saidas_por_dia(
    periodo_dias: int = Query(30, ge=0, le=366),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Retorna entradas e saídas agrupadas por dia para gráfico
    """
    current_user, tenant_id = user_and_tenant
    try:
        hoje = datetime.now()
        inicio_periodo = hoje - timedelta(days=periodo_dias)

        # Buscar vendas por dia
        vendas = (
            db.query(
                func.date(Venda.data_venda).label("data"),
                func.sum(Venda.total).label("total"),
            )
            .filter(
                and_(
                    Venda.tenant_id == tenant_id,
                    Venda.data_venda >= inicio_periodo,
                    Venda.status == "finalizada",
                )
            )
            .group_by(func.date(Venda.data_venda))
            .all()
        )

        # Buscar pagamentos por dia
        pagamentos = (
            db.query(
                func.date(ContaPagar.data_pagamento).label("data"),
                func.sum(ContaPagar.valor_pago).label("total"),
            )
            .filter(
                and_(
                    ContaPagar.tenant_id == tenant_id,
                    ContaPagar.data_pagamento >= inicio_periodo,
                )
            )
            .group_by(func.date(ContaPagar.data_pagamento))
            .all()
        )

        # Organizar por data
        dados_por_dia = {}

        # Inicializar todos os dias com zero
        for i in range(periodo_dias + 1):
            data = (inicio_periodo + timedelta(days=i)).strftime("%Y-%m-%d")
            dados_por_dia[data] = {"data": data, "entradas": 0, "saidas": 0}

        # Preencher com vendas
        for venda in vendas:
            data_obj = venda[0] if isinstance(venda, tuple) else venda.data
            data_str = (
                data_obj.strftime("%Y-%m-%d")
                if hasattr(data_obj, "strftime")
                else str(data_obj)
            )
            if data_str in dados_por_dia:
                dados_por_dia[data_str]["entradas"] = float(venda.total or 0)

        # Preencher com pagamentos
        for pagamento in pagamentos:
            data_obj = pagamento[0] if isinstance(pagamento, tuple) else pagamento.data
            data_str = (
                data_obj.strftime("%Y-%m-%d")
                if hasattr(data_obj, "strftime")
                else str(data_obj)
            )
            if data_str in dados_por_dia:
                dados_por_dia[data_str]["saidas"] = float(pagamento.total or 0)

        # Converter para lista ordenada
        resultado = sorted(dados_por_dia.values(), key=lambda x: x["data"])

        return resultado

    except Exception as e:
        logger.error(f"Erro ao obter entradas/saídas por dia: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/vendas-por-dia")
async def obter_vendas_por_dia(
    periodo_dias: int = Query(30, ge=0, le=366),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Retorna vendas agrupadas por dia para gráfico
    """
    current_user, tenant_id = user_and_tenant
    try:
        hoje = datetime.now()
        inicio_periodo = hoje - timedelta(days=periodo_dias)

        # Buscar vendas do período
        vendas = (
            db.query(
                func.date(Venda.data_venda).label("data"),
                func.count(Venda.id).label("quantidade"),
                func.sum(Venda.total).label("valor_total"),
            )
            .filter(
                and_(Venda.tenant_id == tenant_id, Venda.data_venda >= inicio_periodo)
            )
            .group_by(func.date(Venda.data_venda))
            .all()
        )

        # Organizar por data
        dados_por_dia = {}

        # Inicializar todos os dias com zero
        for i in range(periodo_dias + 1):
            data = (inicio_periodo + timedelta(days=i)).strftime("%Y-%m-%d")
            dados_por_dia[data] = {"data": data, "quantidade": 0, "valor_total": 0}

        # Preencher com dados reais
        for venda in vendas:
            # venda é um resultado de query com labels, não um objeto Venda
            data_obj = venda[0] if isinstance(venda, tuple) else venda.data
            data_str = (
                data_obj.strftime("%Y-%m-%d")
                if hasattr(data_obj, "strftime")
                else str(data_obj)
            )
            if data_str in dados_por_dia:
                dados_por_dia[data_str]["quantidade"] = (
                    int(venda.quantidade) if venda.quantidade else 0
                )
                dados_por_dia[data_str]["valor_total"] = float(venda.valor_total or 0)

        # Converter para lista ordenada
        resultado = sorted(dados_por_dia.values(), key=lambda x: x["data"])

        return resultado

    except Exception as e:
        logger.error(f"Erro ao obter vendas por dia: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/contas-vencidas")
async def obter_contas_vencidas(
    limite: int = 10,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Retorna contas a receber e pagar vencidas (não pagas)
    """
    current_user, tenant_id = user_and_tenant

    try:
        hoje = datetime.now().date()
        logger.info("[contas-vencidas] Buscando contas vencidas")

        # Contas a receber vencidas
        try:
            contas_receber = (
                db.query(ContaReceber)
                .filter(
                    and_(
                        ContaReceber.tenant_id == tenant_id,
                        ContaReceber.status.in_(["pendente", "parcial", "vencido"]),
                        ContaReceber.data_vencimento < hoje,
                    )
                )
                .order_by(ContaReceber.data_vencimento.asc())
                .limit(limite)
                .all()
            )
            logger.info(
                f"[contas-vencidas] Encontradas {len(contas_receber)} contas a receber vencidas"
            )
        except Exception as e:
            logger.error(f"[contas-vencidas] Erro ao buscar contas a receber: {e}")
            contas_receber = []

        # Contas a pagar vencidas
        try:
            contas_pagar = (
                db.query(ContaPagar)
                .filter(
                    and_(
                        ContaPagar.tenant_id == tenant_id,
                        ContaPagar.status.in_(["pendente", "parcial", "vencido"]),
                        ContaPagar.data_vencimento < hoje,
                    )
                )
                .order_by(ContaPagar.data_vencimento.asc())
                .limit(limite)
                .all()
            )
            logger.info(
                f"[contas-vencidas] Encontradas {len(contas_pagar)} contas a pagar vencidas"
            )
        except Exception as e:
            logger.error(f"[contas-vencidas] Erro ao buscar contas a pagar: {e}")
            contas_pagar = []

        # Serializar contas a receber
        contas_receber_list = []
        for c in contas_receber:
            try:
                # Acessar relacionamentos com segurança
                cliente_nome = None
                try:
                    if hasattr(c, "cliente") and c.cliente:
                        cliente_nome = c.cliente.nome
                except Exception:
                    pass

                valor_final = float(c.valor_final) if c.valor_final else 0
                valor_recebido = float(c.valor_recebido) if c.valor_recebido else 0

                contas_receber_list.append(
                    {
                        "id": c.id,
                        "descricao": c.descricao or "Sem descrição",
                        "cliente": cliente_nome,
                        "valor_total": valor_final,
                        "valor_pago": valor_recebido,
                        "saldo": valor_final - valor_recebido,
                        "data_vencimento": c.data_vencimento.isoformat()
                        if c.data_vencimento
                        else None,
                        "dias_vencido": (hoje - c.data_vencimento).days
                        if c.data_vencimento
                        else 0,
                        "status": c.status,
                    }
                )
            except Exception as e:
                logger.error(
                    f"[contas-vencidas] Erro ao serializar conta a receber {c.id}: {e}"
                )
                continue

        # Serializar contas a pagar
        contas_pagar_list = []
        for c in contas_pagar:
            try:
                # Acessar relacionamentos com segurança
                fornecedor_nome = None
                try:
                    if hasattr(c, "fornecedor") and c.fornecedor:
                        fornecedor_nome = c.fornecedor.nome
                except Exception:
                    pass

                valor_final = float(c.valor_final) if c.valor_final else 0
                valor_pago = float(c.valor_pago) if c.valor_pago else 0

                contas_pagar_list.append(
                    {
                        "id": c.id,
                        "descricao": c.descricao or "Sem descrição",
                        "fornecedor": fornecedor_nome,
                        "valor_total": valor_final,
                        "valor_pago": valor_pago,
                        "saldo": valor_final - valor_pago,
                        "data_vencimento": c.data_vencimento.isoformat()
                        if c.data_vencimento
                        else None,
                        "dias_vencido": (hoje - c.data_vencimento).days
                        if c.data_vencimento
                        else 0,
                        "status": c.status,
                    }
                )
            except Exception as e:
                logger.error(
                    f"[contas-vencidas] Erro ao serializar conta a pagar {c.id}: {e}"
                )
                continue

        return {
            "contas_receber": contas_receber_list,
            "contas_pagar": contas_pagar_list,
        }

    except Exception as e:
        logger.error(f"Erro ao obter contas vencidas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/gerencial")
async def obter_metricas_gerencial(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Retorna métricas consolidadas para o Dashboard Gerencial.
    Calcula diretamente do banco, sem depender de client-side logic.
    """
    current_user, tenant_id = user_and_tenant
    try:
        # 1. VIPs inativos — segmento VIP com mais de 20 dias sem compra
        vips_result = _dashboard_fetchone(
            db,
            """
            SELECT
                COUNT(*) AS qtd,
                COALESCE(SUM(CAST(cs.metricas->>'total_compras_90d' AS FLOAT)), 0) AS impacto
            FROM cliente_segmentos cs
            JOIN clientes c ON c.id = cs.cliente_id AND c.{tenant_filter}
            WHERE cs.{tenant_filter}
              AND cs.segmento = 'VIP'
              AND CAST(cs.metricas->>'ultima_compra_dias' AS INTEGER) > 20
              AND c.ativo = true
        """,
            tenant_id,
        )

        # 2. Clientes inativos — sem compra há mais de 90 dias
        inativos_result = _dashboard_fetchone(
            db,
            """
            SELECT COUNT(DISTINCT c.id) AS qtd
            FROM clientes c
            LEFT JOIN (
                SELECT cliente_id, MAX(data_venda) AS ultima_venda
                FROM vendas
                WHERE {tenant_filter} AND status = 'finalizada'
                GROUP BY cliente_id
            ) v ON v.cliente_id = c.id
            WHERE c.{tenant_filter}
              AND c.tipo_cadastro = 'cliente'
              AND c.ativo = true
              AND (v.ultima_venda IS NULL OR v.ultima_venda < NOW() - INTERVAL '90 days')
        """,
            tenant_id,
        )

        # 3. Clientes endividados — contas a receber em aberto com saldo > 0
        endividados_result = _dashboard_fetchone(
            db,
            """
            SELECT
                COUNT(DISTINCT cr.cliente_id) AS qtd,
                COALESCE(SUM(cr.valor_final - COALESCE(cr.valor_recebido, 0)), 0) AS total_dividas
            FROM contas_receber cr
            WHERE cr.{tenant_filter}
              AND cr.status IN ('pendente', 'vencido', 'parcial')
              AND cr.cliente_id IS NOT NULL
              AND (cr.valor_final - COALESCE(cr.valor_recebido, 0)) > 0
        """,
            tenant_id,
        )

        # 4. Novos promissores — segmento Novo com ticket médio > R$ 200
        novos_result = _dashboard_fetchone(
            db,
            """
            SELECT
                COUNT(*) AS qtd,
                COALESCE(SUM(CAST(cs.metricas->>'ticket_medio' AS FLOAT)), 0) AS potencial
            FROM cliente_segmentos cs
            JOIN clientes c ON c.id = cs.cliente_id AND c.{tenant_filter}
            WHERE cs.{tenant_filter}
              AND cs.segmento = 'Novo'
              AND CAST(cs.metricas->>'ticket_medio' AS FLOAT) > 200
              AND c.ativo = true
        """,
            tenant_id,
        )

        # 5. WhatsApp faltando — clientes sem celular cadastrado
        sem_whatsapp_result = _dashboard_fetchone(
            db,
            """
            SELECT COUNT(*) AS qtd
            FROM clientes
            WHERE {tenant_filter}
              AND tipo_cadastro = 'cliente'
              AND ativo = true
              AND (celular IS NULL OR TRIM(celular) = '')
        """,
            tenant_id,
        )

        # 6. Total de clientes ativos (tipo cliente)
        total_result = _dashboard_fetchone(
            db,
            """
            SELECT COUNT(*) AS qtd
            FROM clientes
            WHERE {tenant_filter}
              AND tipo_cadastro = 'cliente'
              AND ativo = true
        """,
            tenant_id,
        )

        def fmt_brl(value: float) -> str:
            return f"R$ {value:_.2f}".replace(".", ",").replace("_", ".")

        total_dividas = float(endividados_result.total_dividas or 0)
        potencial_novos = float(novos_result.potencial or 0)
        impacto_vips = float(vips_result.impacto or 0)

        return {
            "vips_inativos": {
                "quantidade": int(vips_result.qtd or 0),
                "impacto": fmt_brl(impacto_vips),
            },
            "clientes_inativos": {
                "quantidade": int(inativos_result.qtd or 0),
                "impacto": "Reativação pendente",
            },
            "clientes_endividados": {
                "quantidade": int(endividados_result.qtd or 0),
                "impacto": fmt_brl(total_dividas),
            },
            "oportunidades_novos": {
                "quantidade": int(novos_result.qtd or 0),
                "impacto": f"~R$ {potencial_novos:_.0f}/mês".replace("_", "."),
            },
            "pets_sem_eventos": {"quantidade": 0, "impacto": "Em breve"},
            "whatsapp_inativo": {
                "quantidade": int(sem_whatsapp_result.qtd or 0),
                "impacto": "Canal perdido",
            },
            "total_clientes": int(total_result.qtd or 0),
        }

    except Exception as e:
        logger.error(f"Erro ao obter métricas gerenciais: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/top-produtos")
async def obter_top_produtos(
    periodo_dias: int = 30,
    limite: int = 10,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Retorna os produtos mais vendidos no período
    """
    current_user, tenant_id = user_and_tenant
    try:
        from .vendas_models import VendaItem
        from .produtos_models import Produto

        hoje = datetime.now()
        inicio_periodo = hoje - timedelta(days=periodo_dias)

        # Buscar produtos mais vendidos
        top_produtos = (
            db.query(
                Produto.nome,
                func.sum(VendaItem.quantidade).label("total_vendido"),
                func.sum(VendaItem.subtotal).label("receita_total"),
            )
            .join(VendaItem, Produto.id == VendaItem.produto_id)
            .join(Venda, VendaItem.venda_id == Venda.id)
            .filter(
                and_(
                    Venda.tenant_id == tenant_id,
                    Produto.tenant_id == tenant_id,
                    Venda.data_venda >= inicio_periodo,
                )
            )
            .group_by(Produto.id, Produto.nome)
            .order_by(func.sum(VendaItem.quantidade).desc())
            .limit(limite)
            .all()
        )

        return [
            {
                "nome": p.nome,
                "quantidade_vendida": int(p.total_vendido),
                "receita_total": float(p.receita_total or 0),
            }
            for p in top_produtos
        ]

    except Exception as e:
        logger.error(f"Erro ao obter top produtos: {e}")
        raise HTTPException(status_code=500, detail=str(e))
