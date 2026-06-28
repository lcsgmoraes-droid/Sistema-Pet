from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import bindparam, text

from app.auth.dependencies import get_current_user_and_tenant
from app.comissoes_avancadas.common import logger, struct_logger
from app.comissoes_avancadas_models import (
    ComissaoItem,
    ConferenciaComFiltrosResponse,
    PeriodoSelecionado,
    ResumoComFiltros,
)
from app.db import SessionLocal
from app.utils.tenant_safe_sql import execute_tenant_safe

router = APIRouter()


@router.get(
    "/conferencia-avancada/{funcionario_id}",
    summary="Conferência avançada com filtros por produto e período",
)
def conferencia_com_filtros_avancados(
    funcionario_id: int,
    _user_and_tenant=Depends(get_current_user_and_tenant),
    grupo_produto: Optional[int] = Query(
        None, description="Filtro por grupo/categoria de produto"
    ),
    produto_id: Optional[int] = Query(
        None, description="Filtro por produto específico"
    ),
    data_inicio: Optional[date] = Query(None, description="Data inicial do período"),
    data_fim: Optional[date] = Query(None, description="Data final do período"),
) -> ConferenciaComFiltrosResponse:
    """
    SPRINT 6 - PASSO 6: CONFERÊNCIA COM FILTROS AVANÇADOS

    Retorna comissões pendentes de um funcionário com suporte a filtros avançados:
    - Por grupo/categoria de produto
    - Por produto específico
    - Por período de data

    Regras mantidas:
    - Snapshot imutável: valor_comissao NUNCA é recalculado
    - Status: apenas comissões pendentes
    - Sem alteração: apenas leitura
    - Transparência: todos os campos visíveis

    Retorna:
    - Período selecionado para auditoria
    - Resumo com totais do filtro aplicado
    - Lista completa de comissões visíveis
    """
    try:
        struct_logger.info(
            "CONFERENCE_ADVANCED_START",
            f"Conferência avançada para funcionário {funcionario_id}",
            extra={
                "funcionario_id": funcionario_id,
                "filtros_aplicados": {
                    "grupo_produto": grupo_produto,
                    "produto_id": produto_id,
                    "data_inicio": str(data_inicio) if data_inicio else None,
                    "data_fim": str(data_fim) if data_fim else None,
                },
            },
        )

        _, tenant_id = _user_and_tenant
        db = SessionLocal()

        try:
            # 1. Buscar dados do funcionário
            result = execute_tenant_safe(
                db,
                "SELECT id, nome, tipo_cadastro FROM clientes WHERE id = :funcionario_id AND {tenant_filter}",
                {"funcionario_id": funcionario_id},
                tenant_id=tenant_id,
            )
            func_row = result.fetchone()

            if not func_row:
                raise HTTPException(
                    status_code=404,
                    detail=f"Funcionário {funcionario_id} não encontrado",
                )

            # 2. Construir query com filtros
            query = """
                SELECT 
                    ci.id,
                    ci.venda_id,
                    ci.data_venda,
                    ci.produto_id,
                    ci.categoria_id,
                    ci.subcategoria_id,
                    ci.quantidade,
                    ci.valor_venda,
                    ci.valor_base_calculo,
                    ci.percentual_comissao,
                    ci.valor_comissao_gerada,
                    ci.tipo_calculo,
                    ci.status,
                    ci.forma_pagamento,
                    ci.valor_pago,
                    ci.saldo_restante,
                    p.nome as nome_produto,
                    cat.nome as nome_categoria,
                    v.cliente_id
                FROM comissoes_itens ci
                LEFT JOIN produtos p ON ci.produto_id = p.id AND p.tenant_id = ci.tenant_id
                LEFT JOIN categorias cat ON ci.categoria_id = cat.id AND cat.tenant_id = ci.tenant_id
                LEFT JOIN vendas v ON ci.venda_id = v.id AND v.tenant_id = ci.tenant_id
                WHERE ci.{tenant_filter}
                  AND ci.funcionario_id = :funcionario_id
                  AND ci.status = 'pendente'
            """

            params = {"funcionario_id": funcionario_id}

            # Aplicar filtros
            if grupo_produto:
                query += " AND ci.categoria_id = :grupo_produto"
                params["grupo_produto"] = grupo_produto

            if produto_id:
                query += " AND ci.produto_id = :produto_id"
                params["produto_id"] = produto_id

            if data_inicio:
                query += " AND DATE(ci.data_venda) >= :data_inicio"
                params["data_inicio"] = str(data_inicio)

            if data_fim:
                query += " AND DATE(ci.data_venda) <= :data_fim"
                params["data_fim"] = str(data_fim)

            query += " ORDER BY ci.data_venda ASC, ci.id ASC"

            result = execute_tenant_safe(db, query, params, tenant_id=tenant_id)
            rows = result.fetchall()

            # 3. Buscar nomes dos clientes
            cliente_ids = list(set([row.cliente_id for row in rows if row.cliente_id]))
            clientes_map = {}

            if cliente_ids:
                stmt_clientes = text(
                    "SELECT id, nome FROM clientes WHERE id IN :ids AND {tenant_filter}"
                ).bindparams(bindparam("ids", expanding=True))
                result_clientes = execute_tenant_safe(
                    db,
                    stmt_clientes,
                    {"ids": tuple(cliente_ids)},
                    tenant_id=tenant_id,
                )
                for cliente in result_clientes.fetchall():
                    clientes_map[cliente.id] = cliente.nome

            # 4. Buscar nome do grupo de produto se filtrado
            grupo_nome = None
            if grupo_produto:
                result_grupo = execute_tenant_safe(
                    db,
                    "SELECT nome FROM categorias WHERE id = :id AND {tenant_filter}",
                    {"id": grupo_produto},
                    tenant_id=tenant_id,
                )
                grupo_row = result_grupo.fetchone()
                grupo_nome = grupo_row.nome if grupo_row else None

            # 5. Buscar nome do produto se filtrado
            produto_nome = None
            if produto_id:
                result_produto = execute_tenant_safe(
                    db,
                    "SELECT nome FROM produtos WHERE id = :id AND {tenant_filter}",
                    {"id": produto_id},
                    tenant_id=tenant_id,
                )
                prod_row = result_produto.fetchone()
                produto_nome = prod_row.nome if prod_row else None

            # 6. Montar lista de comissões com calculo de saldo
            comissoes = []
            valor_total = 0.0
            valor_pago_total = 0.0
            saldo_total = 0.0

            for row in rows:
                cliente_nome = (
                    clientes_map.get(row.cliente_id, "Cliente não identificado")
                    if row.cliente_id
                    else "Venda sem cliente"
                )

                valor_comissao = (
                    float(row.valor_comissao_gerada)
                    if row.valor_comissao_gerada
                    else 0.0
                )
                valor_pago = float(row.valor_pago) if row.valor_pago else 0.0
                saldo_restante = (
                    float(row.saldo_restante)
                    if row.saldo_restante
                    else valor_comissao - valor_pago
                )

                comissao_dict = ComissaoItem(
                    id=row.id,
                    venda_id=row.venda_id,
                    data_venda=row.data_venda.isoformat() if row.data_venda else None,
                    produto_id=row.produto_id,
                    nome_produto=row.nome_produto or f"Produto #{row.produto_id}",
                    cliente_nome=cliente_nome,
                    quantidade=float(row.quantidade) if row.quantidade else 0.0,
                    valor_venda=float(row.valor_venda) if row.valor_venda else 0.0,
                    valor_base_calculo=float(row.valor_base_calculo)
                    if row.valor_base_calculo
                    else 0.0,
                    percentual_comissao=float(row.percentual_comissao)
                    if row.percentual_comissao
                    else 0.0,
                    valor_comissao=valor_comissao,
                    tipo_calculo=row.tipo_calculo,
                    status=row.status,
                    forma_pagamento=row.forma_pagamento,
                    valor_pago=valor_pago if valor_pago > 0 else None,
                    saldo_restante=saldo_restante if valor_pago > 0 else None,
                )

                comissoes.append(comissao_dict)
                valor_total += valor_comissao
                valor_pago_total += valor_pago
                saldo_total += saldo_restante

            # 7. Calcular percentual pago
            percentual_pago = (
                (valor_pago_total / valor_total * 100) if valor_total > 0 else 0.0
            )

            # 8. Montar resposta
            periodo = PeriodoSelecionado(
                data_inicio=data_inicio,
                data_fim=data_fim,
                grupo_produto=grupo_produto,
                produto_id=produto_id,
                grupo_produto_nome=grupo_nome,
                produto_nome=produto_nome,
            )

            resumo = ResumoComFiltros(
                quantidade_comissoes=len(comissoes),
                valor_total=round(valor_total, 2),
                valor_pago_total=round(valor_pago_total, 2),
                saldo_restante_total=round(saldo_total, 2),
                percentual_pago=round(percentual_pago, 2),
            )

            response = ConferenciaComFiltrosResponse(
                success=True,
                funcionario={
                    "id": func_row.id,
                    "nome": func_row.nome,
                    "tipo": func_row.tipo_cadastro,
                },
                periodo_selecionado=periodo,
                resumo=resumo,
                comissoes=comissoes,
            )

            struct_logger.info(
                "CONFERENCE_ADVANCED_SUCCESS",
                f"Conferência carregada: {len(comissoes)} comissões, R$ {valor_total:.2f}",
                extra={
                    "funcionario_id": funcionario_id,
                    "quantidade": len(comissoes),
                    "valor_total": valor_total,
                    "valor_pago_total": valor_pago_total,
                    "saldo_total": saldo_total,
                },
            )

            return response

        finally:
            db.close()

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro na conferência avançada: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao buscar conferência: {str(e)}"
        )


__all__ = ["conferencia_com_filtros_avancados", "router"]
