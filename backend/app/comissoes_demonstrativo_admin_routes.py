"""Rotas administrativas do demonstrativo de comissoes."""

import logging
from typing import Annotated, Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.comissoes_demonstrativo_fechamento import fechar_comissoes_pendentes
from app.comissoes_demonstrativo_schemas import FecharComissoesRequest
from app.db import get_session
from app.utils.logger import StructuredLogger
from app.utils.tenant_safe_sql import execute_tenant_safe


logger = logging.getLogger(__name__)
struct_logger = StructuredLogger(__name__)
router = APIRouter()

__all__ = ["fechar_comissoes", "listar_funcionarios_comissoes", "router"]


@router.get(
    "/funcionarios",
    summary="Listar funcionarios com comissoes",
    responses={500: {"description": "Erro interno ao consultar funcionarios"}},
)
async def listar_funcionarios_comissoes(
    db: Annotated[Session, Depends(get_session)],
    user_and_tenant: Annotated[tuple[Any, Any], Depends(get_current_user_and_tenant)],
) -> Dict[str, Any]:
    """
    Retorna lista de funcionarios que possuem comissoes registradas.

    SNAPSHOT IMUTAVEL:
    - Busca APENAS funcionarios que aparecem em comissoes_itens
    - NAO recalcula valores
    - NAO faz joins desnecessarios

    Retorna:
    - lista: Array com id e nome dos funcionarios
    - total: Quantidade de funcionarios

    Criterio: Funcionario possui registros em comissoes_itens OU
              possui configuracao em comissoes_configuracao
    """

    _current_user, _tenant_id = user_and_tenant
    struct_logger.info(
        "COMMISSION_EMPLOYEES_LIST", "Consulta de funcionarios com comissoes"
    )

    try:
        result = execute_tenant_safe(
            db,
            """
            SELECT DISTINCT
                c.id,
                c.nome
            FROM clientes c
            WHERE c.id IN (
                SELECT DISTINCT funcionario_id
                FROM comissoes_itens
                WHERE funcionario_id IS NOT NULL
                AND {tenant_filter}
            )
            AND {tenant_filter}
            ORDER BY c.nome ASC
        """,
            {},
        )
        rows = result.fetchall()

        funcionarios = []
        for row in rows:
            funcionarios.append({"id": row[0], "nome": row[1]})

        logger.info(f"Retornando {len(funcionarios)} funcionarios com comissoes")

        return {"success": True, "lista": funcionarios, "total": len(funcionarios)}

    except Exception as e:
        logger.exception("Erro ao listar funcionarios com comissoes")
        raise HTTPException(
            status_code=500, detail=f"Erro ao consultar funcionarios: {str(e)}"
        ) from e


@router.post(
    "/fechar",
    summary="Fechar comissoes (alterar status para pago)",
    responses={500: {"description": "Erro interno ao fechar comissoes"}},
)
async def fechar_comissoes(
    request: FecharComissoesRequest,
    db: Annotated[Session, Depends(get_session)],
    user_and_tenant: Annotated[tuple[Any, Any], Depends(get_current_user_and_tenant)],
) -> Dict[str, Any]:
    """
    Fecha comissoes alterando status para 'pago'.

    IMPORTANTE:
    - NAO recalcula valores (snapshot imutavel)
    - Altera APENAS: status, data_pagamento, observacao_pagamento
    - So processa comissoes com status='pendente'
    - Ignora silenciosamente comissoes ja pagas/estornadas

    Regras:
    - Comissoes ja pagas: ignoradas
    - Comissoes estornadas: ignoradas
    - Apenas status='pendente' sao fechadas
    - Operacao em transacao unica

    Returns:
    - total_processadas: Quantidade fechada com sucesso
    - total_ignoradas: Quantidade ja paga/estornada
    - comissoes_fechadas: IDs das comissoes processadas
    - comissoes_ignoradas: IDs ignorados
    """

    struct_logger.info(
        "COMMISSION_CLOSE_START",
        f"Iniciando fechamento de {len(request.comissoes_ids)} comissoes",
        extra={
            "ids_count": len(request.comissoes_ids),
            "data_pagamento": str(request.data_pagamento),
            "has_observacao": bool(request.observacao),
        },
    )

    try:
        resultado = fechar_comissoes_pendentes(
            db=db,
            request=request,
            current_user=user_and_tenant[0],
            struct_logger=struct_logger,
        )

        return {
            "success": True,
            **resultado,
            "data_pagamento": str(request.data_pagamento),
            "message": f"{resultado['total_processadas']} comissao(oes) fechada(s) com sucesso",
        }

    except Exception as e:
        logger.exception("Erro ao fechar comissoes")
        raise HTTPException(
            status_code=500, detail=f"Erro ao fechar comissoes: {str(e)}"
        ) from e
