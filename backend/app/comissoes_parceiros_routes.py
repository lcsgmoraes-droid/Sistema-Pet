"""Rotas de parceiros e listagem de regras configuradas de comissoes."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from .auth.dependencies import get_current_user_and_tenant
from .comissoes_schema_guard import ensure_comissoes_config_schema
from .utils.tenant_safe_sql import execute_tenant_safe

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/funcionarios")
async def listar_funcionarios(user_and_tenant=Depends(get_current_user_and_tenant)):
    """
    Lista todas as pessoas parceiras ativas que podem receber comissÃµes
    """
    try:
        from .db import SessionLocal
        from .models import Cliente
        from sqlalchemy import and_

        db = SessionLocal()
        try:
            funcionarios_query = (
                db.query(
                    Cliente.id,
                    Cliente.nome,
                    Cliente.email,
                    Cliente.tipo_cadastro.label("cargo"),
                    Cliente.data_fechamento_comissao,
                )
                .filter(and_(Cliente.parceiro_ativo.is_(True), Cliente.ativo.is_(True)))
                .order_by(Cliente.nome)
            )

            funcionarios = []
            for row in funcionarios_query.all():
                funcionarios.append(
                    {
                        "id": row.id,
                        "nome": row.nome,
                        "email": row.email,
                        "cargo": row.cargo,
                        "data_fechamento_comissao": row.data_fechamento_comissao,
                    }
                )

            return {"success": True, "data": funcionarios}
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Erro ao listar parceiros: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar parceiros: {str(e)}",
        )


@router.get("/configuracoes/funcionarios")
async def listar_funcionarios_com_comissao(
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Lista todas as pessoas parceiras ativas com contagem de configuraÃ§Ãµes
    """
    try:
        from .db import SessionLocal
        from .tenancy.context import set_tenant_context

        # Extrair tenant_id do contexto
        _current_user, tenant_id = user_and_tenant

        # ðŸ”’ CRÃTICO: Garantir que contexto estÃ¡ configurado
        set_tenant_context(tenant_id)

        db = SessionLocal()
        try:
            ensure_comissoes_config_schema(db)
            # Query que conta as configuraÃ§Ãµes de cada parceiro ativo
            result = execute_tenant_safe(
                db,
                """
                SELECT 
                    c.id,
                    c.nome,
                    c.email,
                    c.tipo_cadastro as cargo,
                    COUNT(cc.id) as total_configuracoes,
                    COUNT(CASE WHEN cc.tipo = 'categoria' THEN 1 END) as categorias,
                    COUNT(CASE WHEN cc.tipo = 'subcategoria' THEN 1 END) as subcategorias,
                    COUNT(CASE WHEN cc.tipo = 'produto' THEN 1 END) as produtos,
                    COUNT(CASE WHEN cc.tipo = 'geral' THEN 1 END) as gerais
                FROM clientes c
                LEFT JOIN comissoes_configuracao cc ON cc.funcionario_id = c.id AND cc.ativo = true AND cc.tenant_id = c.tenant_id
                WHERE c.parceiro_ativo = true
                AND c.{tenant_filter}
                GROUP BY c.id, c.nome, c.email, c.tipo_cadastro
                ORDER BY c.nome
            """,
                {},
            )

            funcionarios = []
            for row in result:
                funcionarios.append(
                    {
                        "id": row[0],
                        "nome": row[1],
                        "email": row[2] or "",
                        "cargo": row[3] or "funcionario",
                        "total_configuracoes": row[4],
                        "categorias": row[5],
                        "subcategorias": row[6],
                        "produtos": row[7],
                        "gerais": row[8],
                    }
                )

            return {"success": True, "data": funcionarios}
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Erro ao listar parceiros: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar parceiros: {str(e)}",
        )


@router.get("/configuracoes/funcionario/{funcionario_id}")
async def buscar_configuracoes_funcionario(
    funcionario_id: int, user_and_tenant=Depends(get_current_user_and_tenant)
):
    """
    Busca todas as configuraÃ§Ãµes de comissÃ£o de um funcionÃ¡rio especÃ­fico
    """
    try:
        from .db import SessionLocal
        from .tenancy.context import set_tenant_context

        # Extrair tenant_id e configurar contexto
        _current_user, tenant_id = user_and_tenant
        set_tenant_context(tenant_id)

        db = SessionLocal()
        try:
            ensure_comissoes_config_schema(db)
            result = execute_tenant_safe(
                db,
                """
                SELECT 
                    cc.id,
                    cc.funcionario_id,
                    cc.tipo,
                    cc.referencia_id,
                    cc.percentual,
                    cc.ativo,
                    cc.tipo_calculo,
                    cc.desconta_taxa_cartao,
                    cc.desconta_impostos,
                    cc.desconta_custo_entrega,
                    cc.comissao_venda_parcial,
                    cc.percentual_loja,
                    cc.permite_edicao_venda,
                    cc.observacoes,
                    CASE 
                        WHEN cc.tipo = 'categoria' THEN c.nome
                        WHEN cc.tipo = 'subcategoria' THEN sc.nome
                        WHEN cc.tipo = 'produto' THEN p.nome
                        WHEN cc.tipo = 'geral' THEN 'Regra geral'
                    END as nome_item
                FROM comissoes_configuracao cc
                LEFT JOIN categorias c ON cc.tipo = 'categoria' AND cc.referencia_id = c.id AND c.tenant_id = cc.tenant_id
                LEFT JOIN categorias sc ON cc.tipo = 'subcategoria' AND cc.referencia_id = sc.id AND sc.tenant_id = cc.tenant_id
                LEFT JOIN produtos p ON cc.tipo = 'produto' AND cc.referencia_id = p.id AND p.tenant_id = cc.tenant_id
                WHERE cc.funcionario_id = :func_id AND cc.ativo = true
                AND cc.{tenant_filter}
                ORDER BY cc.tipo, nome_item
            """,
                {"func_id": funcionario_id},
            )

            configs = []
            for row in result:
                configs.append(
                    {
                        "id": row[0],
                        "funcionario_id": row[1],
                        "tipo": row[2],
                        "referencia_id": row[3],
                        "percentual": float(row[4]) if row[4] else 0,
                        "ativo": row[5],
                        "tipo_calculo": row[6] or "percentual",
                        "desconta_taxa_cartao": row[7] if row[7] is not None else True,
                        "desconta_impostos": row[8] if row[8] is not None else True,
                        "desconta_custo_entrega": row[9]
                        if row[9] is not None
                        else False,
                        "comissao_venda_parcial": row[10]
                        if row[10] is not None
                        else True,
                        "percentual_loja": float(row[11]) if row[11] else None,
                        "permite_edicao_venda": row[12]
                        if row[12] is not None
                        else False,
                        "observacoes": row[13] or "",
                        "nome_item": row[14] if row[14] else None,
                    }
                )

            return {"success": True, "data": configs, "total": len(configs)}
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Erro ao buscar configuraÃ§Ãµes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar configuraÃ§Ãµes: {str(e)}",
        )
