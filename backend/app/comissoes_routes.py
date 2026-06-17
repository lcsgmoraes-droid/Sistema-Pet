"""
Rotas para o módulo de Comissões
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel
import logging
from sqlalchemy import text

from .auth.dependencies import get_current_user_and_tenant
from .comissoes_models import ComissoesConfig, ComissoesItens, ComissoesConfigSistema
from .utils.tenant_safe_sql import execute_tenant_safe
from .tenancy.context import get_current_tenant_id
from .tenancy.rls import sync_rls_tenant

# Configurar logger
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/comissoes", tags=["comissoes"])
_comissoes_schema_checked = False
TIPOS_CONFIGURACAO_COMISSAO = {"categoria", "subcategoria", "produto", "geral"}


def ensure_comissoes_config_schema(db) -> None:
    """Garante coluna tenant_id em comissoes_configuracao para compatibilidade."""
    global _comissoes_schema_checked
    if _comissoes_schema_checked:
        return

    tenant_id = get_current_tenant_id()
    if tenant_id:
        sync_rls_tenant(db, tenant_id)

    db.execute(
        text(
            "ALTER TABLE comissoes_configuracao ADD COLUMN IF NOT EXISTS tenant_id uuid"
        )
    )
    if tenant_id:
        db.execute(
            text("""
                UPDATE comissoes_configuracao cc
                SET tenant_id = c.tenant_id
                FROM clientes c
                WHERE cc.funcionario_id = c.id
                  AND c.tenant_id = :tenant_id
                  AND cc.tenant_id IS NULL
            """),
            {"tenant_id": str(tenant_id)},
        )
    db.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_comissoes_configuracao_tenant_id "
            "ON comissoes_configuracao (tenant_id)"
        )
    )
    db.commit()
    _comissoes_schema_checked = True


# ==========================================
# SCHEMAS
# ==========================================


class ConfiguracaoComissaoCreate(BaseModel):
    """Schema para criar/atualizar uma configuração de comissão"""

    funcionario_id: int
    tipo: str  # 'categoria', 'subcategoria', 'produto', 'geral'
    referencia_id: int
    tipo_calculo: str  # 'percentual' ou 'lucro'
    percentual: float
    percentual_loja: Optional[float] = None
    desconta_taxa_cartao: bool = True
    desconta_impostos: bool = True
    desconta_custo_entrega: bool = False
    comissao_venda_parcial: bool = True
    permite_edicao_venda: bool = False
    observacoes: Optional[str] = None


class ConfiguracoesBatchCreate(BaseModel):
    """Schema para criar múltiplas configurações de uma vez"""

    configuracoes: List[ConfiguracaoComissaoCreate]


class ConfiguracaoComissaoResponse(BaseModel):
    """Schema de resposta para configuração"""

    id: int
    funcionario_id: int
    tipo: str
    referencia_id: int
    nome_item: Optional[str]
    tipo_calculo: str
    percentual: float
    percentual_loja: Optional[float]
    desconta_taxa_cartao: bool
    desconta_impostos: bool
    desconta_custo_entrega: bool
    permite_edicao_venda: bool
    ativo: bool
    observacoes: Optional[str]
    data_criacao: str


class ConfiguracaoSistemaUpdate(BaseModel):
    """Schema para atualizar configurações do sistema"""

    gerar_comissao_venda_parcial: Optional[bool] = None
    percentual_imposto_padrao: Optional[float] = None
    dias_vencimento_padrao: Optional[int] = None
    email_assunto_template: Optional[str] = None
    email_corpo_template: Optional[str] = None
    pdf_formato_padrao: Optional[str] = None


class DuplicarConfiguracaoRequest(BaseModel):
    """Schema para duplicar configuração"""

    funcionario_origem_id: int
    funcionario_destino_id: int


def _normalizar_configuracao_comissao(
    config: ConfiguracaoComissaoCreate,
) -> ConfiguracaoComissaoCreate:
    if config.tipo == "geral":
        config.referencia_id = 0
    return config


# ==========================================
# ENDPOINTS - CONFIGURAÇÕES
# ==========================================


@router.get("/funcionarios")
async def listar_funcionarios(user_and_tenant=Depends(get_current_user_and_tenant)):
    """
    Lista todas as pessoas parceiras ativas que podem receber comissões
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
    Lista todas as pessoas parceiras ativas com contagem de configurações
    """
    try:
        from .db import SessionLocal
        from .tenancy.context import set_tenant_context

        # Extrair tenant_id do contexto
        _current_user, tenant_id = user_and_tenant

        # 🔒 CRÍTICO: Garantir que contexto está configurado
        set_tenant_context(tenant_id)

        db = SessionLocal()
        try:
            ensure_comissoes_config_schema(db)
            # Query que conta as configurações de cada parceiro ativo
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
    Busca todas as configurações de comissão de um funcionário específico
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
        logger.error(f"Erro ao buscar configurações: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar configurações: {str(e)}",
        )


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
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Retorna as configurações globais do sistema de comissões
    """
    try:
        config = ComissoesConfigSistema.get_config()

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
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Atualiza as configurações globais do sistema de comissões
    """
    try:
        success = ComissoesConfigSistema.atualizar_config(
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

        return {"success": True, "message": "Configurações atualizadas com sucesso"}

    except HTTPException:
        raise
    except Exception as e:
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
