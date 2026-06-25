import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text

from app.auth.dependencies import get_current_user_and_tenant
from app.db import SessionLocal
from app.utils.logger import StructuredLogger
from app.utils.tenant_safe_sql import execute_tenant_safe

logger = logging.getLogger(__name__)
struct_logger = StructuredLogger(__name__)
router = APIRouter()


# ==================== ENDPOINT: HISTÓRICO DE FECHAMENTOS ====================


@router.get("/fechamentos", summary="Histórico de fechamentos de comissões (auditoria)")
def listar_historico_fechamentos(
    data_inicio: Optional[date] = Query(
        None, description="Data inicial do filtro (data_pagamento)"
    ),
    data_fim: Optional[date] = Query(
        None, description="Data final do filtro (data_pagamento)"
    ),
    funcionario_id: Optional[int] = Query(
        None, description="Filtrar por funcionário específico"
    ),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    SPRINT 6 - PASSO 4/5: HISTÓRICO DE FECHAMENTOS

    Lista histórico de fechamentos realizados, agrupados por funcionário e data de pagamento.

    ⚠️ SOMENTE LEITURA - AUDITORIA:
    - Não permite alterações
    - Não recalcula valores
    - Snapshot imutável
    - Rastreabilidade completa

    Regras:
    - Agrupa comissões com status='paga'
    - Agrupa por funcionario_id + data_pagamento + observacao_pagamento
    - Retorna resumo de cada fechamento
    - Ordenação: data_pagamento DESC

    Retorna:
    - Lista de fechamentos com resumo financeiro
    - Cada fechamento pode ser expandido para ver detalhes
    """
    try:
        struct_logger.info(
            "COMMISSION_HISTORY_LIST",
            "Consultando histórico de fechamentos",
            extra={
                "data_inicio": str(data_inicio) if data_inicio else None,
                "data_fim": str(data_fim) if data_fim else None,
                "funcionario_id": funcionario_id,
            },
        )

        from app.tenancy.context import set_tenant_context

        # Configurar tenant context
        current_user, tenant_id = user_and_tenant
        set_tenant_context(tenant_id)

        db = SessionLocal()

        # Query para agrupar fechamentos
        # CORRIGIDO: funcionario_id refere-se à tabela clientes, não users
        query = """
            SELECT 
                ci.funcionario_id,
                c.nome as nome_funcionario,
                ci.data_pagamento,
                ci.observacao_pagamento,
                COUNT(ci.id) as quantidade_comissoes,
                SUM(ci.valor_comissao_gerada) as valor_total,
                MIN(ci.data_venda) as data_venda_mais_antiga,
                MAX(ci.data_venda) as data_venda_mais_recente,
                MIN(ci.data_atualizacao) as data_fechamento
            FROM comissoes_itens ci
            LEFT JOIN clientes c ON ci.funcionario_id = c.id AND c.{tenant_filter}
            WHERE ci.{tenant_filter} AND ci.status = 'paga'
        """

        params = {}

        # Aplicar filtros
        if data_inicio:
            query += " AND DATE(ci.data_pagamento) >= :data_inicio"
            params["data_inicio"] = str(data_inicio)

        if data_fim:
            query += " AND DATE(ci.data_pagamento) <= :data_fim"
            params["data_fim"] = str(data_fim)

        if funcionario_id is not None:
            query += " AND ci.funcionario_id = :funcionario_id"
            params["funcionario_id"] = funcionario_id

        # Agrupar por funcionário + data_pagamento + observação
        query += """
            GROUP BY ci.funcionario_id, c.nome, ci.data_pagamento, ci.observacao_pagamento
            ORDER BY ci.data_pagamento DESC, ci.funcionario_id ASC
        """

        result = execute_tenant_safe(db, query, params)
        rows = result.fetchall()

        try:
            # Converter para lista de dicionários
            fechamentos = []
            valor_total_geral = 0.0
            quantidade_total_geral = 0

            for row in rows:
                fechamento = {
                    "funcionario_id": row[0],
                    "nome_funcionario": row[1] or "Funcionário não encontrado",
                    "data_pagamento": row[2],
                    "data_fechamento": row[8],
                    "observacao": row[3],
                    "quantidade_comissoes": row[4],
                    "valor_total": float(row[5]) if row[5] else 0.0,
                    "periodo_vendas": {"data_inicio": row[6], "data_fim": row[7]},
                    # Identificador único do fechamento (para navegação)
                    "fechamento_id": f"{row[0]}_{row[2]}",
                }

                fechamentos.append(fechamento)
                valor_total_geral += fechamento["valor_total"]
                quantidade_total_geral += fechamento["quantidade_comissoes"]
        finally:
            db.close()

        struct_logger.info(
            "COMMISSION_HISTORY_LIST_SUCCESS",
            f"{len(fechamentos)} fechamento(s) encontrado(s)",
            extra={
                "total_fechamentos": len(fechamentos),
                "valor_total": valor_total_geral,
                "quantidade_total": quantidade_total_geral,
            },
        )

        return {
            "success": True,
            "filtros": {
                "data_inicio": str(data_inicio) if data_inicio else None,
                "data_fim": str(data_fim) if data_fim else None,
                "funcionario_id": funcionario_id,
            },
            "resumo": {
                "total_fechamentos": len(fechamentos),
                "valor_total_geral": valor_total_geral,
                "quantidade_total_geral": quantidade_total_geral,
            },
            "fechamentos": fechamentos,
        }

    except Exception as e:
        logger.error(f"Erro ao listar histórico de fechamentos: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao listar histórico: {str(e)}"
        )


@router.get(
    "/fechamentos/detalhe", summary="Detalhes de um fechamento específico (auditoria)"
)
def detalhe_fechamento(
    funcionario_id: int = Query(..., description="ID do funcionário"),
    data_pagamento: date = Query(..., description="Data do pagamento"),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    SPRINT 6 - PASSO 4/5: DETALHE DE UM FECHAMENTO

    Retorna todas as comissões incluídas em um fechamento específico.

    ⚠️ SOMENTE LEITURA - AUDITORIA:
    - Não permite alterações
    - Todas as informações são read-only
    - Snapshot imutável

    Identificação do fechamento:
    - funcionario_id + data_pagamento (chave composta)

    Retorna:
    - Dados do funcionário
    - Informações do fechamento
    - Lista completa de comissões incluídas
    """
    try:
        struct_logger.info(
            "COMMISSION_CLOSURE_DETAIL",
            f"Consultando detalhes do fechamento: funcionário {funcionario_id}, data {data_pagamento}",
            extra={
                "funcionario_id": funcionario_id,
                "data_pagamento": str(data_pagamento),
            },
        )

        from app.tenancy.context import set_tenant_context

        # Configurar tenant context
        current_user, tenant_id = user_and_tenant
        set_tenant_context(tenant_id)

        db = SessionLocal()

        try:
            # Buscar dados do funcionário (CORRIGIDO: busca em clientes)
            result = execute_tenant_safe(
                db,
                "SELECT nome FROM clientes WHERE id = :id AND {tenant_filter}",
                {"id": funcionario_id},
            )
            funcionario_row = result.fetchone()

            if not funcionario_row:
                raise HTTPException(
                    status_code=404, detail="Funcionário não encontrado"
                )

            nome_funcionario = funcionario_row[0]

            # Buscar comissões deste fechamento
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
                    ci.data_pagamento,
                    ci.observacao_pagamento,
                    ci.data_atualizacao,
                    p.nome as nome_produto,
                    v.cliente_id
                FROM comissoes_itens ci
                LEFT JOIN produtos p ON ci.produto_id = p.id AND {tenant_filter_p}
                LEFT JOIN vendas v ON ci.venda_id = v.id AND {tenant_filter_v}
                WHERE {tenant_filter_ci} 
                  AND ci.funcionario_id = :funcionario_id 
                  AND ci.data_pagamento = :data_pagamento
                  AND ci.status = 'paga'
                ORDER BY ci.data_venda ASC, ci.id ASC
            """

            result = execute_tenant_safe(
                db,
                query,
                {
                    "funcionario_id": funcionario_id,
                    "data_pagamento": str(data_pagamento),
                },
            )
            rows = result.fetchall()

            if not rows:
                raise HTTPException(
                    status_code=404,
                    detail="Fechamento não encontrado (sem comissões pagas nesta data)",
                )

            # Buscar nomes dos clientes
            cliente_ids = list(set([row[13] for row in rows if row[13]]))
            clientes_map = {}

            if cliente_ids:
                from sqlalchemy import bindparam

                stmt = text(
                    "SELECT id, nome FROM clientes WHERE {tenant_filter} AND id IN :ids"
                ).bindparams(bindparam("ids", expanding=True))
                result = execute_tenant_safe(db, stmt, {"ids": tuple(cliente_ids)})
                for cliente in result.fetchall():
                    clientes_map[cliente[0]] = cliente[1]

            # Converter para lista de dicionários
            comissoes = []
            valor_total = 0.0
            observacao = None
            data_fechamento = None

            for row in rows:
                if not observacao:
                    observacao = row[10]
                if not data_fechamento:
                    data_fechamento = row[11]

                cliente_nome = (
                    clientes_map.get(row[13], "Cliente não identificado")
                    if row[13]
                    else "Venda sem cliente"
                )

                comissao = {
                    "id": row[0],
                    "venda_id": row[1],
                    "data_venda": row[2],
                    "produto_id": row[3],
                    "nome_produto": row[12] or f"Produto #{row[3]}",
                    "cliente_nome": cliente_nome,
                    "quantidade": float(row[4]) if row[4] else 0.0,
                    "valor_base_calculo": float(row[5]) if row[5] else 0.0,
                    "percentual_comissao": float(row[6]) if row[6] else 0.0,
                    "valor_comissao_gerada": float(row[7]) if row[7] else 0.0,
                    "tipo_calculo": row[8],
                }

                comissoes.append(comissao)
                valor_total += comissao["valor_comissao_gerada"]

            struct_logger.info(
                "COMMISSION_CLOSURE_DETAIL_SUCCESS",
                f"Detalhes carregados: {len(comissoes)} comissão(ões)",
                extra={
                    "funcionario_id": funcionario_id,
                    "data_pagamento": str(data_pagamento),
                    "total_comissoes": len(comissoes),
                    "valor_total": valor_total,
                },
            )

            return {
                "success": True,
                "fechamento": {
                    "funcionario_id": funcionario_id,
                    "nome_funcionario": nome_funcionario,
                    "data_pagamento": str(data_pagamento),
                    "data_fechamento": data_fechamento,
                    "observacao": observacao,
                    "quantidade_comissoes": len(comissoes),
                    "valor_total": valor_total,
                },
                "comissoes": comissoes,
            }
        finally:
            db.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar detalhes do fechamento: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao buscar detalhes: {str(e)}"
        )
