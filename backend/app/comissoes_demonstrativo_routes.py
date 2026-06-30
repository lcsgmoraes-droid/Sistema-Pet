"""
DEMONSTRATIVO DE COMISSÕES - ROTAS (SOMENTE LEITURA)

⚠️ PRINCÍPIO FUNDAMENTAL:
Estas rotas servem EXCLUSIVAMENTE para CONSULTA de snapshots imutáveis.
NÃO recalculam, NÃO atualizam, NÃO modificam dados.
Apenas LEEM a tabela comissoes_itens.

Criado em: 22/01/2026
"""

import logging
from datetime import date
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.comissoes_demonstrativo_calculo import (
    decimal_to_float,
    montar_demonstrativo_calculo_comissao,
)
from app.comissoes_demonstrativo_admin_routes import (
    fechar_comissoes,
    listar_funcionarios_comissoes,
    router as admin_router,
)
from app.comissoes_demonstrativo_detail import montar_detalhe_comissao_snapshot
from app.comissoes_demonstrativo_historico_routes import (
    detalhe_fechamento,
    listar_historico_fechamentos,
    router as historico_router,
)
from app.db import SessionLocal, get_session
from app.utils.tenant_safe_sql import execute_tenant_safe

from app.utils.logger import StructuredLogger

# Logger padrão para logs simples
logger = logging.getLogger(__name__)

# Logger estruturado para eventos
struct_logger = StructuredLogger(__name__)

# Router com prefixo /comissoes
router = APIRouter(prefix="/comissoes", tags=["Comissões - Demonstrativo"])
router.include_router(admin_router)
router.include_router(historico_router)

__all__ = [
    "decimal_to_float",
    "detalhe_fechamento",
    "fechar_comissoes",
    "listar_funcionarios_comissoes",
    "listar_historico_fechamentos",
    "montar_demonstrativo_calculo_comissao",
    "router",
]


# ==================== ENDPOINTS DE LEITURA ====================


@router.get("", summary="Listar comissões (histórico)")
async def listar_comissoes(
    funcionario_id: Optional[int] = Query(None, description="Filtrar por funcionário"),
    data_inicio: Optional[date] = Query(None, description="Data inicial (YYYY-MM-DD)"),
    data_fim: Optional[date] = Query(None, description="Data final (YYYY-MM-DD)"),
    status: Optional[str] = Query(
        None, description="Status: pendente, pago ou estornado"
    ),
    venda_id: Optional[int] = Query(None, description="Filtrar por venda específica"),
    user_and_tenant=Depends(get_current_user_and_tenant),
) -> Dict[str, Any]:
    """
    Lista comissões com filtros opcionais.

    🔒 SNAPSHOT IMUTÁVEL:
    - Retorna dados direto de comissoes_itens
    - NÃO recalcula valores
    - NÃO consulta outras tabelas

    Retorna:
    - lista: Array de comissões
    - total: Total de registros
    - filtros_aplicados: Resumo dos filtros
    """

    # Log estruturado
    struct_logger.info(
        "COMMISSION_LIST_REQUEST",
        "Consulta de histórico de comissões",
        funcionario_id=funcionario_id,
        data_inicio=str(data_inicio) if data_inicio else None,
        data_fim=str(data_fim) if data_fim else None,
        status=status,
        venda_id=venda_id,
    )

    try:
        from app.tenancy.context import set_tenant_context
        from app.db import SessionLocal

        # Configurar tenant context
        current_user, tenant_id = user_and_tenant
        set_tenant_context(tenant_id)

        db = SessionLocal()
        # Construir query dinâmica
        query = """
            SELECT 
                ci.id,
                ci.venda_id,
                v.numero_venda,
                COALESCE(v.data_finalizacao, v.data_venda, ci.data_venda) as data_venda,
                ci.funcionario_id,
                ci.produto_id,
                ci.parcela_numero,
                ci.valor_base_calculo,
                ci.percentual_comissao,
                ci.valor_comissao_gerada,
                ci.status,
                ci.data_estorno,
                ci.motivo_estorno,
                ci.tipo_calculo,
                ci.quantidade
            FROM comissoes_itens ci
            INNER JOIN vendas v ON v.id = ci.venda_id AND v.tenant_id = ci.tenant_id
            WHERE ci.{tenant_filter}
        """

        params = {}

        # Aplicar filtros
        if funcionario_id is not None:
            query += " AND funcionario_id = :funcionario_id"
            params["funcionario_id"] = funcionario_id

        if data_inicio:
            query += " AND ci.data_venda >= :data_inicio"
            params["data_inicio"] = data_inicio

        if data_fim:
            query += " AND ci.data_venda <= :data_fim"
            params["data_fim"] = data_fim

        if status:
            query += " AND status = :status"
            params["status"] = status.lower()

        if venda_id is not None:
            query += " AND venda_id = :venda_id"
            params["venda_id"] = venda_id

        # Ordenar por mais recente
        query += " ORDER BY COALESCE(v.data_finalizacao, v.data_venda, ci.data_venda) DESC, ci.id DESC"

        result = execute_tenant_safe(db, query, params)
        rows = result.fetchall()

        # Converter para lista de dicts
        comissoes = []
        for row in rows:
            comissoes.append(
                {
                    "id": row[0],
                    "venda_id": row[1],
                    "numero_venda": row[2],
                    "data_venda": str(row[3]) if row[3] else None,
                    "funcionario_id": row[4],
                    "produto_id": row[5],
                    "parcela_numero": row[6],
                    "valor_base_calculo": decimal_to_float(row[7]),
                    "percentual_comissao": decimal_to_float(row[8]),
                    "valor_comissao_gerada": decimal_to_float(row[9]),
                    "status": row[10],
                    "data_estorno": str(row[11]) if row[11] else None,
                    "motivo_estorno": row[12],
                    "tipo_calculo": row[13],
                    "quantidade": decimal_to_float(row[14]),
                }
            )

        logger.info(f"Retornando {len(comissoes)} comissões")

        return {
            "success": True,
            "lista": comissoes,
            "total": len(comissoes),
            "filtros_aplicados": {
                "funcionario_id": funcionario_id,
                "data_inicio": str(data_inicio) if data_inicio else None,
                "data_fim": str(data_fim) if data_fim else None,
                "status": status,
                "venda_id": venda_id,
            },
        }

    except Exception as e:
        logger.error(f"Erro ao listar comissões: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao consultar comissões: {str(e)}"
        )


@router.get("/resumo", summary="Resumo financeiro de comissões")
async def resumo_comissoes(
    funcionario_id: int = Query(..., description="ID do funcionário (obrigatório)"),
    data_inicio: Optional[date] = Query(None, description="Data inicial (YYYY-MM-DD)"),
    data_fim: Optional[date] = Query(None, description="Data final (YYYY-MM-DD)"),
    user_and_tenant=Depends(get_current_user_and_tenant),
) -> Dict[str, Any]:
    """
    Retorna resumo financeiro das comissões (totalizadores para cards).

    🔒 SNAPSHOT IMUTÁVEL:
    - Usa SUM() direto em comissoes_itens
    - NÃO recalcula valores

    Retorna:
    - total_gerado: Soma de todas comissões (exceto estornadas)
    - total_pago: Soma de comissões com status=pago
    - total_pendente: Soma de comissões com status=pendente
    - total_estornado: Soma de comissões estornadas
    - saldo_a_pagar: total_pendente
    """

    struct_logger.info(
        "COMMISSION_SUMMARY_REQUEST",
        "Consulta de resumo financeiro de comissões",
        funcionario_id=funcionario_id,
        data_inicio=str(data_inicio) if data_inicio else None,
        data_fim=str(data_fim) if data_fim else None,
    )

    try:
        from app.tenancy.context import set_tenant_context
        from app.db import SessionLocal

        # Configurar tenant context
        current_user, tenant_id = user_and_tenant
        set_tenant_context(tenant_id)

        db = SessionLocal()

        # Query base para filtros de data
        where_clause = "WHERE funcionario_id = :funcionario_id AND {tenant_filter}"
        params = {"funcionario_id": funcionario_id}

        if data_inicio:
            where_clause += " AND data_venda >= :data_inicio"
            params["data_inicio"] = data_inicio

        if data_fim:
            where_clause += " AND data_venda <= :data_fim"
            params["data_fim"] = data_fim

        # Total gerado (pendente + pago, excluindo estornado)
        result = execute_tenant_safe(
            db,
            f"""
            SELECT COALESCE(SUM(valor_comissao_gerada), 0) as total
            FROM comissoes_itens
            {where_clause} AND status != 'estornado'
        """,
            params,
        )
        total_gerado = decimal_to_float(result.scalar())

        # Total pago
        result = execute_tenant_safe(
            db,
            f"""
            SELECT COALESCE(SUM(valor_comissao_gerada), 0) as total
            FROM comissoes_itens
            {where_clause} AND status = 'pago'
        """,
            params,
        )
        total_pago = decimal_to_float(result.scalar())

        # Total pendente
        result = execute_tenant_safe(
            db,
            f"""
            SELECT COALESCE(SUM(valor_comissao_gerada), 0) as total
            FROM comissoes_itens
            {where_clause} AND status = 'pendente'
        """,
            params,
        )
        total_pendente = decimal_to_float(result.scalar())

        # Total estornado
        result = execute_tenant_safe(
            db,
            f"""
            SELECT COALESCE(SUM(valor_comissao_gerada), 0) as total
            FROM comissoes_itens
            {where_clause} AND status = 'estornado'
        """,
            params,
        )
        total_estornado = decimal_to_float(result.scalar())

        # Quantidade de comissões
        result = execute_tenant_safe(
            db,
            f"""
            SELECT COUNT(*) as total
            FROM comissoes_itens
            {where_clause}
        """,
            params,
        )
        quantidade_comissoes = result.scalar()

        # Saldo a pagar = total pendente
        saldo_a_pagar = total_pendente

        logger.info(
            f"Resumo: funcionario={funcionario_id}, gerado={total_gerado}, pago={total_pago}, pendente={total_pendente}"
        )

        return {
            "success": True,
            "funcionario_id": funcionario_id,
            "resumo": {
                "total_gerado": total_gerado,
                "total_pago": total_pago,
                "total_pendente": total_pendente,
                "total_estornado": total_estornado,
                "saldo_a_pagar": saldo_a_pagar,
                "quantidade_comissoes": quantidade_comissoes,
            },
            "periodo": {
                "data_inicio": str(data_inicio) if data_inicio else None,
                "data_fim": str(data_fim) if data_fim else None,
            },
        }

    except Exception as e:
        logger.error(f"Erro ao calcular resumo: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao calcular resumo: {str(e)}"
        )


# ==================== ENDPOINT: COMISSÕES EM ABERTO ====================


@router.get("/abertas", summary="Listar funcionários com comissões pendentes")
def listar_comissoes_abertas(user_and_tenant=Depends(get_current_user_and_tenant)):
    """
    SPRINT 6 - PASSO 1/5: COMISSÕES EM ABERTO

    Lista funcionários que possuem comissões pendentes com resumo financeiro.

    Regras:
    - Usa EXCLUSIVAMENTE a tabela comissoes_itens
    - Considera apenas status='pendente'
    - NÃO recalcula valores
    - Agrupa por funcionario_id

    Retorna:
    - funcionario_id
    - nome_funcionario
    - total_pendente (soma dos valores)
    - quantidade_comissoes
    - data_ultima_venda

    Ordenação: total_pendente DESC
    """
    try:
        # Extrair tenant_id e configurar contexto
        from app.tenancy.context import set_tenant_context

        current_user, tenant_id = user_and_tenant
        set_tenant_context(tenant_id)

        struct_logger.info(
            "COMMISSION_OPEN_LIST", "Consultando funcionários com comissões em aberto"
        )

        db = SessionLocal()

        try:
            # Query agrupada por funcionário (APENAS LEITURA)
            # CORRIGIDO: funcionario_id refere-se à tabela clientes, não users
            query = """
                SELECT 
                    ci.funcionario_id,
                    c.nome as nome_funcionario,
                    SUM(ci.valor_comissao_gerada) as total_pendente,
                    COUNT(ci.id) as quantidade_comissoes,
                    MAX(ci.data_venda) as data_ultima_venda
                FROM comissoes_itens ci
                LEFT JOIN clientes c ON ci.funcionario_id = c.id AND c.{tenant_filter}
                WHERE ci.{tenant_filter} AND ci.status = 'pendente'
                GROUP BY ci.funcionario_id, c.nome
                ORDER BY total_pendente DESC
            """

            result = execute_tenant_safe(db, query, {})
            rows = result.fetchall()

            # Converter para lista de dicionários
            funcionarios = []
            for row in rows:
                funcionarios.append(
                    {
                        "funcionario_id": row[0],
                        "nome_funcionario": row[1] or "Funcionário não encontrado",
                        "total_pendente": float(row[2]) if row[2] else 0.0,
                        "quantidade_comissoes": row[3],
                        "data_ultima_venda": row[4],
                    }
                )

            struct_logger.info(
                "COMMISSION_OPEN_LIST_SUCCESS",
                f"{len(funcionarios)} funcionário(s) com comissões pendentes",
                extra={"total_funcionarios": len(funcionarios)},
            )

            return {
                "success": True,
                "total_funcionarios": len(funcionarios),
                "funcionarios": funcionarios,
            }
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Erro ao listar comissões abertas: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao listar comissões abertas: {str(e)}"
        )


# ==================== ENDPOINT: CONFERÊNCIA POR FUNCIONÁRIO ====================


@router.get(
    "/fechamento/{funcionario_id}",
    summary="Comissões pendentes de um funcionário para conferência",
)
def listar_comissoes_funcionario_para_fechamento(
    funcionario_id: int,
    data_inicio: Optional[date] = Query(None, description="Data inicial do filtro"),
    data_fim: Optional[date] = Query(None, description="Data final do filtro"),
    _user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    SPRINT 6 - PASSO 2/5: CONFERÊNCIA POR FUNCIONÁRIO

    Lista todas as comissões pendentes de um funcionário específico.

    Regras:
    - Usa EXCLUSIVAMENTE a tabela comissoes_itens
    - Considera apenas status='pendente'
    - NÃO recalcula valores
    - Permite filtro por período

    Retorna:
    - Dados completos de cada comissão
    - Informações de venda, produto, cliente
    - Valores de base de cálculo e comissão

    Ordenação: data_venda ASC
    """
    try:
        struct_logger.info(
            "COMMISSION_EMPLOYEE_LIST",
            f"Consultando comissões pendentes do funcionário {funcionario_id}",
            extra={"funcionario_id": funcionario_id},
        )

        db = SessionLocal()

        try:
            # Buscar nome do funcionário (CORRIGIDO: busca na tabela clientes)
            result = execute_tenant_safe(
                db,
                "SELECT nome FROM clientes WHERE id = :id AND {tenant_filter}",
                {"id": funcionario_id},
            )
            funcionario_row = result.fetchone()

            if not funcionario_row:
                raise HTTPException(
                    status_code=404,
                    detail=f"Funcionário {funcionario_id} não encontrado",
                )

            nome_funcionario = funcionario_row[0]

            # Query para listar comissões (APENAS LEITURA)
            query = """
                SELECT 
                    ci.id,
                    ci.venda_id,
                    ci.data_venda,
                    ci.produto_id,
                    ci.quantidade,
                    ci.valor_base_calculo,
                    ci.percentual_comissao,
                    ci.valor_comissao_gerada,
                    ci.tipo_calculo,
                    ci.parcela_numero,
                    p.nome as nome_produto,
                    v.cliente_id
                FROM comissoes_itens ci
                LEFT JOIN produtos p ON ci.produto_id = p.id AND {tenant_filter_p}
                LEFT JOIN vendas v ON ci.venda_id = v.id AND {tenant_filter_v}
                WHERE {tenant_filter_ci} AND ci.funcionario_id = :funcionario_id AND ci.status = 'pendente'
            """

            params = {"funcionario_id": funcionario_id}

            # Aplicar filtros de data
            if data_inicio:
                query += " AND DATE(ci.data_venda) >= :data_inicio"
                params["data_inicio"] = str(data_inicio)

            if data_fim:
                query += " AND DATE(ci.data_venda) <= :data_fim"
                params["data_fim"] = str(data_fim)

            query += " ORDER BY ci.data_venda ASC, ci.id ASC"

            result = execute_tenant_safe(db, query, params)
            rows = result.fetchall()

            # Buscar nomes dos clientes (se houver)
            cliente_ids = list(set([row[11] for row in rows if row[11]]))
            clientes_map = {}

            if cliente_ids:
                from sqlalchemy import bindparam

                stmt = text(
                    "SELECT id, nome FROM clientes WHERE id IN :ids AND {tenant_filter}"
                ).bindparams(bindparam("ids", expanding=True))
                result = execute_tenant_safe(db, stmt, {"ids": tuple(cliente_ids)})
                for cliente in result.fetchall():
                    clientes_map[cliente[0]] = cliente[1]

            # Converter para lista de dicionários
            comissoes = []
            total_geral = 0.0

            for row in rows:
                cliente_nome = (
                    clientes_map.get(row[11], "Cliente não identificado")
                    if row[11]
                    else "Venda sem cliente"
                )

                comissao = {
                    "id": row[0],
                    "venda_id": row[1],
                    "data_venda": row[2],
                    "produto_id": row[3],
                    "nome_produto": row[10] or f"Produto #{row[3]}",
                    "cliente_nome": cliente_nome,
                    "quantidade": float(row[4]) if row[4] else 0.0,
                    "valor_base_calculo": float(row[5]) if row[5] else 0.0,
                    "percentual_comissao": float(row[6]) if row[6] else 0.0,
                    "valor_comissao_gerada": float(row[7]) if row[7] else 0.0,
                    "tipo_calculo": row[8],
                    "parcela_numero": row[9],
                }

                comissoes.append(comissao)
                total_geral += comissao["valor_comissao_gerada"]

            struct_logger.info(
                "COMMISSION_EMPLOYEE_LIST_SUCCESS",
                f"{len(comissoes)} comissão(ões) encontrada(s) para funcionário {funcionario_id}",
                extra={
                    "funcionario_id": funcionario_id,
                    "total_comissoes": len(comissoes),
                    "valor_total": total_geral,
                },
            )

            return {
                "success": True,
                "funcionario": {"id": funcionario_id, "nome": nome_funcionario},
                "filtros": {
                    "data_inicio": str(data_inicio) if data_inicio else None,
                    "data_fim": str(data_fim) if data_fim else None,
                },
                "total_comissoes": len(comissoes),
                "valor_total": total_geral,
                "comissoes": comissoes,
            }
        finally:
            db.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Erro ao listar comissões do funcionário {funcionario_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=500, detail=f"Erro ao listar comissões: {str(e)}"
        )


@router.get(
    "/comissao/{comissao_id}",
    summary="Detalhe completo de uma comissão (transparência total)",
)
async def detalhe_comissao(
    comissao_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
) -> Dict[str, Any]:
    """
    Retorna TODOS os campos financeiros do snapshot de uma comissão específica.

    🔒 SNAPSHOT IMUTÁVEL:
    - Mostra exatamente como a comissão foi calculada
    - Valores refletem o momento da venda
    - NÃO recalcula nada

    Use este endpoint para responder:
    "Como essa comissão foi calculada?"

    Retorna todos os campos:
    - Valores financeiros (venda, custo, base de cálculo)
    - Divisões proporcionais (desconto, taxas, impostos)
    - Cálculo da comissão (tipo, percentual, valor gerado)
    - Status e controle
    """

    # Extrair tenant_id e configurar contexto
    from app.tenancy.context import set_tenant_context

    current_user, tenant_id = user_and_tenant
    set_tenant_context(tenant_id)

    struct_logger.info(
        "COMMISSION_DETAIL_REQUEST",
        "Consulta de detalhes de comissão específica",
        comissao_id=comissao_id,
    )

    try:
        # Buscar TODOS os campos do snapshot usando SQLAlchemy
        result = execute_tenant_safe(
            db,
            """
            SELECT 
                ci.id,
                ci.venda_id,
                v.numero_venda,
                v.total as total_venda,
                v.desconto_valor as desconto_total_venda,
                v.cupom_discount_applied,
                v.rentabilidade_snapshot,
                COALESCE(v.data_finalizacao, v.data_venda, ci.data_venda) as data_venda,
                ci.funcionario_id,
                ci.produto_id,
                ci.venda_item_id,
                ci.quantidade,
                ci.parcela_numero,
                vi.preco_unitario as item_preco_unitario,
                vi.quantidade as item_quantidade,
                vi.desconto_item as item_desconto,
                vi.subtotal as item_subtotal,
                -- Valores financeiros
                ci.valor_venda,
                ci.valor_custo,
                ci.valor_base_original,
                ci.valor_base_comissionada,
                -- Cálculo da comissão
                ci.tipo_calculo,
                ci.valor_base_calculo,
                ci.percentual_comissao,
                ci.percentual_aplicado,
                ci.valor_comissao,
                ci.valor_comissao_gerada,
                -- Controle de pagamento
                ci.percentual_pago,
                ci.valor_pago_referencia,
                ci.valor_pago,
                ci.saldo_restante,
                ci.data_pagamento,
                ci.forma_pagamento,
                -- Status
                ci.status,
                ci.data_estorno,
                ci.motivo_estorno,
                ci.observacao_pagamento,
                -- Informações da forma de pagamento (para mostrar "Taxa Cartão 3x", etc)
                vp.forma_pagamento as forma_pagamento_venda,
                vp.numero_parcelas,
                fp.taxa_percentual,
                fp.taxas_por_parcela,
                -- Deduções detalhadas (snapshot)
                ci.taxa_cartao_item,
                ci.impostos_item,
                ci.taxa_entregador_item,
                ci.custo_operacional_item,
                ci.receita_taxa_entrega_item,
                ci.percentual_impostos
            FROM comissoes_itens ci
            INNER JOIN vendas v ON v.id = ci.venda_id AND v.tenant_id = ci.tenant_id
            LEFT JOIN venda_itens vi ON vi.id = ci.venda_item_id AND vi.tenant_id = ci.tenant_id
            LEFT JOIN venda_pagamentos vp ON vp.venda_id = v.id AND vp.tenant_id = ci.tenant_id
            LEFT JOIN formas_pagamento fp ON fp.nome = vp.forma_pagamento AND fp.tenant_id = ci.tenant_id
            WHERE ci.{tenant_filter}
            AND ci.id = :comissao_id
            LIMIT 1
        """,
            {"comissao_id": comissao_id},
        )

        row = result.fetchone()

        if not row:
            raise HTTPException(
                status_code=404, detail=f"Comissão {comissao_id} não encontrada"
            )

        detalhe = montar_detalhe_comissao_snapshot(row._mapping)

        logger.info(f"Detalhes da comissão {comissao_id} retornados com sucesso")

        return {
            "success": True,
            "comissao": detalhe,
            "snapshot_imutavel": True,
            "mensagem": "Estes valores refletem o momento exato da venda e NÃO podem ser alterados",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar detalhes da comissão {comissao_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao consultar comissão: {str(e)}"
        )
