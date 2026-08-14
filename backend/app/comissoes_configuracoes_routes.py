"""Rotas de criacao, duplicacao e busca de configuracoes de comissoes."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from .auth.dependencies import get_current_user_and_tenant
from .comissoes_models import ComissoesConfig
from .comissoes_schemas import (
    ConfiguracaoComissaoCreate,
    ConfiguracoesBatchCreate,
    DuplicarConfiguracaoRequest,
    _normalizar_configuracao_comissao,
)
from .security.permissions_decorator import require_permission_dependency
from .utils.tenant_safe_sql import execute_tenant_safe

logger = logging.getLogger(__name__)
router = APIRouter(
    dependencies=[Depends(require_permission_dependency("comissoes.configurar"))]
)
TIPOS_CONFIGURACAO_COMISSAO = {"categoria", "subcategoria", "produto", "geral"}


@router.post("/configuracoes")
async def criar_configuracao(
    config: ConfiguracaoComissaoCreate,
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Cria ou atualiza uma configuração de comissão
    """
    try:
        from .db import SessionLocal
        from .models import Cliente
        from .tenancy.context import set_tenant_context

        # Extrair tenant_id e configurar contexto
        current_user, tenant_id = user_and_tenant
        set_tenant_context(tenant_id)

        db = SessionLocal()
        try:
            # 🔒 VALIDAR SE É PARCEIRO
            cliente = (
                db.query(Cliente).filter(Cliente.id == config.funcionario_id).first()
            )

            if not cliente:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Pessoa com ID {config.funcionario_id} não encontrada",
                )

            if not cliente.parceiro_ativo:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Somente parceiros podem ter comissão configurada.",
                )

            config = _normalizar_configuracao_comissao(config)

            # Validações
            if config.tipo not in TIPOS_CONFIGURACAO_COMISSAO:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Tipo inválido. Use: categoria, subcategoria, produto ou geral",
                )

            if config.percentual < 0 or config.percentual > 100:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Percentual deve estar entre 0 e 100",
                )

            # Verificar se já existe configuração
            result = execute_tenant_safe(
                db,
                """
                SELECT id FROM comissoes_configuracao
                WHERE funcionario_id = :func_id 
                AND tipo = :tipo 
                AND referencia_id = :ref_id
                AND {tenant_filter}
            """,
                {
                    "func_id": config.funcionario_id,
                    "tipo": config.tipo,
                    "ref_id": config.referencia_id,
                },
            ).fetchone()

            if result:
                # Atualizar TODOS os campos
                execute_tenant_safe(
                    db,
                    """
                    UPDATE comissoes_configuracao
                    SET percentual = :perc, 
                        percentual_loja = :perc_loja,
                        tipo_calculo = :tipo_calc,
                        desconta_taxa_cartao = :desc_cartao,
                        desconta_impostos = :desc_impostos,
                        desconta_custo_entrega = :desc_entrega,
                        comissao_venda_parcial = :venda_parcial,
                        permite_edicao_venda = :permite_edicao,
                        observacoes = :obs,
                        ativo = true
                    WHERE id = :id
                    AND {tenant_filter}
                """,
                    {
                        "perc": config.percentual,
                        "perc_loja": config.percentual_loja,
                        "tipo_calc": config.tipo_calculo,
                        "desc_cartao": config.desconta_taxa_cartao,
                        "desc_impostos": config.desconta_impostos,
                        "desc_entrega": config.desconta_custo_entrega,
                        "venda_parcial": config.comissao_venda_parcial,
                        "permite_edicao": config.permite_edicao_venda,
                        "obs": config.observacoes or "",
                        "id": result[0],
                    },
                )
                config_id = result[0]
            else:
                # Inserir TODOS os campos
                result = execute_tenant_safe(
                    db,
                    """
                    INSERT INTO comissoes_configuracao 
                    (funcionario_id, tipo, referencia_id, percentual, percentual_loja, tipo_calculo,
                     desconta_taxa_cartao, desconta_impostos, desconta_custo_entrega, comissao_venda_parcial,
                     permite_edicao_venda, observacoes, ativo, tenant_id)
                    VALUES (:func_id, :tipo, :ref_id, :perc, :perc_loja, :tipo_calc,
                            :desc_cartao, :desc_impostos, :desc_entrega, :venda_parcial,
                            :permite_edicao, :obs, true, :tenant_id)
                    RETURNING id
                """,
                    {
                        "func_id": config.funcionario_id,
                        "tipo": config.tipo,
                        "ref_id": config.referencia_id,
                        "perc": config.percentual,
                        "perc_loja": config.percentual_loja,
                        "tipo_calc": config.tipo_calculo,
                        "desc_cartao": config.desconta_taxa_cartao,
                        "desc_impostos": config.desconta_impostos,
                        "desc_entrega": config.desconta_custo_entrega,
                        "venda_parcial": config.comissao_venda_parcial,
                        "permite_edicao": config.permite_edicao_venda,
                        "obs": config.observacoes or "",
                        "tenant_id": tenant_id,
                    },
                    require_tenant=False,
                )
                config_id = result.fetchone()[0]

            db.commit()

            return {
                "success": True,
                "message": "Configuração salva com sucesso",
                "config_id": config_id,
            }
        finally:
            db.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao criar configuração: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao salvar configuração: {str(e)}",
        )


@router.post("/configuracoes/batch")
async def criar_configuracoes_batch(
    batch: ConfiguracoesBatchCreate,
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Cria ou atualiza múltiplas configurações de uma vez em uma única transação
    SOLUÇÃO CORRETA: with db.begin() para transação explícita
    """
    try:
        from .db import SessionLocal
        from sqlalchemy.exc import OperationalError
        from .tenancy.context import set_tenant_context

        # Extrair tenant_id e configurar contexto
        current_user, tenant_id = user_and_tenant
        set_tenant_context(tenant_id)

        if not batch.configuracoes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nenhuma configuração fornecida",
            )

        db = SessionLocal()
        config_ids = []

        try:
            # 🔥 VALIDAR SE TODOS OS FUNCIONÁRIOS SÃO PARCEIROS
            funcionarios_ids = list(
                set([c.funcionario_id for c in batch.configuracoes])
            )
            from .models import Cliente

            for func_id in funcionarios_ids:
                cliente = db.query(Cliente).filter(Cliente.id == func_id).first()

                if not cliente:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Pessoa com ID {func_id} não encontrada",
                    )

                if not cliente.parceiro_ativo:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Somente parceiros podem ter comissão configurada.",
                    )

            # Processar todas as configurações (SessionLocal já tem transação ativa)
            for config in batch.configuracoes:
                config = _normalizar_configuracao_comissao(config)
                # Validações
                if config.tipo not in TIPOS_CONFIGURACAO_COMISSAO:
                    raise ValueError(f"Tipo inválido: {config.tipo}")

                if config.percentual < 0 or config.percentual > 100:
                    raise ValueError(
                        f"Percentual deve estar entre 0 e 100: {config.percentual}"
                    )

                # Buscar se já existe
                result = execute_tenant_safe(
                    db,
                    """
                    SELECT id
                    FROM comissoes_configuracao
                    WHERE funcionario_id = :f
                      AND tipo = :t
                      AND referencia_id = :r
                      AND {tenant_filter}
                """,
                    {
                        "f": config.funcionario_id,
                        "t": config.tipo,
                        "r": config.referencia_id,
                    },
                    tenant_id=tenant_id,
                ).fetchone()

                if result:
                    # Atualizar
                    execute_tenant_safe(
                        db,
                        """
                        UPDATE comissoes_configuracao SET
                            percentual = :p,
                            percentual_loja = :pl,
                            tipo_calculo = :tc,
                            desconta_taxa_cartao = :dtc,
                            desconta_impostos = :di,
                            desconta_custo_entrega = :dce,
                            comissao_venda_parcial = :cvp,
                            permite_edicao_venda = :pev,
                            observacoes = :obs,
                            ativo = true
                            WHERE id = :id AND {tenant_filter}
                    """,
                        {
                            "p": config.percentual,
                            "pl": config.percentual_loja,
                            "tc": config.tipo_calculo,
                            "dtc": config.desconta_taxa_cartao,
                            "di": config.desconta_impostos,
                            "dce": config.desconta_custo_entrega,
                            "cvp": config.comissao_venda_parcial,
                            "pev": config.permite_edicao_venda,
                            "obs": config.observacoes or "",
                            "id": result[0],
                        },
                        tenant_id=tenant_id,
                    )
                    config_ids.append(result[0])
                else:
                    # Criar
                    result = execute_tenant_safe(
                        db,
                        """
                        INSERT INTO comissoes_configuracao (
                            funcionario_id, tipo, referencia_id, percentual, percentual_loja, tipo_calculo,
                            desconta_taxa_cartao, desconta_impostos, desconta_custo_entrega,
                            comissao_venda_parcial, permite_edicao_venda, observacoes, ativo, tenant_id
                        ) VALUES (
                            :f, :t, :r, :p, :pl, :tc, :dtc, :di, :dce, :cvp, :pev, :obs, true, :tenant_id
                        ) RETURNING id
                    """,
                        {
                            "f": config.funcionario_id,
                            "t": config.tipo,
                            "r": config.referencia_id,
                            "p": config.percentual,
                            "pl": config.percentual_loja,
                            "tc": config.tipo_calculo,
                            "dtc": config.desconta_taxa_cartao,
                            "di": config.desconta_impostos,
                            "dce": config.desconta_custo_entrega,
                            "cvp": config.comissao_venda_parcial,
                            "pev": config.permite_edicao_venda,
                            "obs": config.observacoes or "",
                            "tenant_id": tenant_id,
                        },
                        tenant_id=tenant_id,
                        require_tenant=False,
                    )
                    config_ids.append(result.fetchone()[0])

            db.commit()

            return {
                "success": True,
                "message": f"{len(config_ids)} configurações salvas com sucesso",
                "config_ids": config_ids,
                "total": len(config_ids),
            }

        except OperationalError as e:
            db.rollback()
            logger.error(f"Database locked ao salvar batch: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Banco de dados ocupado. Tente novamente em alguns segundos.",
            )
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Erro ao criar configurações em batch: {error_msg}")

        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao salvar configurações: {error_msg}",
        )


@router.delete("/configuracoes/{config_id}")
async def deletar_configuracao(
    config_id: int, user_and_tenant=Depends(get_current_user_and_tenant)
):
    """
    Deleta (desativa) uma configuração de comissão
    """
    try:
        # Extrair tenant_id e configurar contexto
        from .tenancy.context import set_tenant_context

        _current_user, tenant_id = user_and_tenant
        set_tenant_context(tenant_id)

        success = ComissoesConfig.deletar(config_id, tenant_id=tenant_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Configuração não encontrada",
            )

        return {"success": True, "message": "Configuração removida com sucesso"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao deletar configuração: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao remover configuração: {str(e)}",
        )


@router.post("/configuracoes/duplicar")
async def duplicar_configuracao(
    request: DuplicarConfiguracaoRequest,
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Duplica todas as configurações de um funcionário para outro
    """
    try:
        # 🔒 VALIDAR SE DESTINO É PARCEIRO
        from .db import SessionLocal
        from .tenancy.context import set_tenant_context

        # Extrair tenant_id e configurar contexto
        current_user, tenant_id = user_and_tenant
        set_tenant_context(tenant_id)

        db = SessionLocal()
        try:
            result = execute_tenant_safe(
                db,
                "SELECT id, nome, parceiro_ativo FROM clientes WHERE id = :id AND {tenant_filter}",
                {"id": request.funcionario_destino_id},
            )
            pessoa_destino = result.fetchone()
        finally:
            db.close()

        if not pessoa_destino:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pessoa destino com ID {request.funcionario_destino_id} não encontrada",
            )

        if not pessoa_destino[2]:  # parceiro_ativo
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Somente parceiros podem ter comissão configurada.",
            )

        count = ComissoesConfig.duplicar_configuracao(
            funcionario_origem_id=request.funcionario_origem_id,
            funcionario_destino_id=request.funcionario_destino_id,
            usuario_id=current_user.id,
            tenant_id=tenant_id,
        )

        return {
            "success": True,
            "message": f"{count} configurações duplicadas com sucesso",
            "total_duplicadas": count,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao duplicar configuração: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao duplicar configurações: {str(e)}",
        )


@router.get("/configuracoes/buscar-aplicavel")
async def buscar_configuracao_aplicavel(
    funcionario_id: int,
    produto_id: int,
    categoria_id: Optional[int] = None,
    subcategoria_id: Optional[int] = None,
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Busca a configuração de comissão aplicável para um produto específico
    Segue hierarquia: Produto > Subcategoria > Categoria
    """
    try:
        from .tenancy.context import set_tenant_context

        _current_user, tenant_id = user_and_tenant
        set_tenant_context(tenant_id)

        config = ComissoesConfig.buscar_configuracao(
            funcionario_id=funcionario_id,
            produto_id=produto_id,
            categoria_id=categoria_id,
            subcategoria_id=subcategoria_id,
            tenant_id=tenant_id,
        )

        if not config:
            return {
                "success": True,
                "data": None,
                "message": "Nenhuma configuração de comissão encontrada",
            }

        return {"success": True, "data": config}

    except Exception as e:
        logger.error(f"Erro ao buscar configuração aplicável: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar configuração: {str(e)}",
        )


# ==========================================
# ENDPOINTS - ITENS DE COMISSÃO
# ==========================================
