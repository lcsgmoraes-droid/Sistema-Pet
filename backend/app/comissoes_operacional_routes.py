"""Rotas operacionais e de apoio do modulo de comissoes."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .auth.dependencies import get_current_user_and_tenant
from .comissoes_models import ComissoesConfigSistema, ComissoesItens
from .comissoes_schemas import ConfiguracaoSistemaUpdate
from .db import get_session
from .security.permissions_decorator import require_permission_dependency
from .utils.tenant_safe_sql import execute_tenant_safe

logger = logging.getLogger(__name__)
router = APIRouter(
    dependencies=[Depends(require_permission_dependency("comissoes.configurar"))]
)


@router.get("/itens/pendentes")
async def listar_itens_pendentes(
    funcionario_id: Optional[int] = None,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Lista itens de comissão pendentes (ainda não fechados)
    """
    try:
        itens = ComissoesItens.listar_pendentes(
            funcionario_id=funcionario_id, data_inicio=data_inicio, data_fim=data_fim
        )

        # Calcular totais
        total_comissao = sum(item["valor_comissao_gerada"] for item in itens)
        total_vendas = len(set(item["venda_id"] for item in itens))

        return {
            "success": True,
            "data": itens,
            "resumo": {
                "total_itens": len(itens),
                "total_vendas": total_vendas,
                "total_comissao": round(total_comissao, 2),
            },
        }

    except Exception as e:
        logger.error(f"Erro ao listar itens pendentes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar itens: {str(e)}",
        )


# ==========================================
# ENDPOINTS - CONFIGURAÇÕES DO SISTEMA
# ==========================================


@router.get("/config-sistema")
async def get_configuracoes_sistema(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Retorna as configurações globais do sistema de comissões
    """
    try:
        _current_user, tenant_id = user_and_tenant
        config = ComissoesConfigSistema.get_config(db, tenant_id)

        return {"success": True, "data": config}

    except Exception as e:
        logger.error(f"Erro ao buscar configurações do sistema: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar configurações: {str(e)}",
        )


@router.put("/config-sistema")
async def atualizar_configuracoes_sistema(
    config: ConfiguracaoSistemaUpdate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Atualiza as configurações globais do sistema de comissões
    """
    try:
        _current_user, tenant_id = user_and_tenant
        success = ComissoesConfigSistema.atualizar_config(
            db=db,
            tenant_id=tenant_id,
            gerar_comissao_venda_parcial=config.gerar_comissao_venda_parcial,
            percentual_imposto_padrao=config.percentual_imposto_padrao,
            dias_vencimento_padrao=config.dias_vencimento_padrao,
            email_assunto_template=config.email_assunto_template,
            email_corpo_template=config.email_corpo_template,
            pdf_formato_padrao=config.pdf_formato_padrao,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nenhuma configuração foi atualizada",
            )

        db.commit()
        return {"success": True, "message": "Configurações atualizadas com sucesso"}

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao atualizar configurações: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar configurações: {str(e)}",
        )


# ==========================================
# ENDPOINTS - ÁRVORE DE CATEGORIAS/PRODUTOS
# ==========================================


@router.get("/arvore-produtos")
async def get_arvore_produtos(user_and_tenant=Depends(get_current_user_and_tenant)):
    """
    Retorna uma árvore hierárquica de categorias > subcategorias > produtos
    Para uso no modal de configuração de comissões
    Suporta até 4 níveis de hierarquia de categorias
    """
    try:
        from .db import SessionLocal
        from .tenancy.context import set_tenant_context

        # Extrair tenant_id e configurar contexto
        current_user, tenant_id = user_and_tenant
        set_tenant_context(tenant_id)

        db = SessionLocal()
        try:

            def construir_arvore_recursiva(categoria_pai_id=None, nivel=1, max_nivel=4):
                """Constrói árvore de categorias recursivamente"""
                if nivel > max_nivel:
                    return []

                # Buscar categorias deste nível
                if categoria_pai_id is None:
                    result = execute_tenant_safe(
                        db,
                        """
                        SELECT id, nome, descricao
                        FROM categorias
                        WHERE categoria_pai_id IS NULL
                        AND ativo = true
                        AND {tenant_filter}
                        ORDER BY ordem, nome
                    """,
                        {},
                    )
                else:
                    result = execute_tenant_safe(
                        db,
                        """
                        SELECT id, nome, descricao
                        FROM categorias
                        WHERE categoria_pai_id = :pai_id
                        AND ativo = true
                        AND {tenant_filter}
                        ORDER BY ordem, nome
                    """,
                        {"pai_id": categoria_pai_id},
                    )

                categorias = []
                for row in result:
                    cat_id = row[0]
                    categoria = {
                        "id": row[0],
                        "nome": row[1],
                        "descricao": row[2],
                        "nivel": nivel,
                    }

                    # Buscar filhas recursivamente
                    categoria["filhas"] = construir_arvore_recursiva(
                        cat_id, nivel + 1, max_nivel
                    )

                    # Buscar produtos desta categoria
                    result_prod = execute_tenant_safe(
                        db,
                        """
                        SELECT id, nome, codigo, preco_venda as preco, preco_custo as custo
                        FROM produtos
                        WHERE categoria_id = :cat_id AND situacao = true
                        AND {tenant_filter}
                        ORDER BY nome
                        LIMIT 100
                    """,
                        {"cat_id": cat_id},
                    )

                    categoria["produtos"] = [
                        {
                            "id": p[0],
                            "nome": p[1],
                            "codigo": p[2],
                            "preco": float(p[3]) if p[3] else 0,
                            "custo": float(p[4]) if p[4] else 0,
                        }
                        for p in result_prod
                    ]

                    categorias.append(categoria)

                return categorias

            # Construir árvore completa a partir das raízes
            arvore = construir_arvore_recursiva(
                categoria_pai_id=None, nivel=1, max_nivel=4
            )

            return {"success": True, "data": arvore}
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Erro ao buscar árvore de produtos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar produtos: {str(e)}",
        )
