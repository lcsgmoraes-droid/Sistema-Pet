"""Rotas administrativas do demonstrativo de comissoes."""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.comissoes_demonstrativo_fechamento import fechar_comissoes_pendentes
from app.comissoes_demonstrativo_schemas import FecharComissoesRequest
from app.db import SessionLocal, get_session
from app.utils.logger import StructuredLogger
from app.utils.tenant_safe_sql import execute_tenant_safe


logger = logging.getLogger(__name__)
struct_logger = StructuredLogger(__name__)
router = APIRouter()

__all__ = ["fechar_comissoes", "listar_funcionarios_comissoes", "router"]


@router.get("/funcionarios", summary="Listar funcionários com comissões")
async def listar_funcionarios_comissoes(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
) -> Dict[str, Any]:
    """
    Retorna lista de funcionários que possuem comissões registradas.

    🔒 SNAPSHOT IMUTÁVEL:
    - Busca APENAS funcionários que aparecem em comissoes_itens
    - NÃO recalcula valores
    - NÃO faz joins desnecessários

    Retorna:
    - lista: Array com id e nome dos funcionários
    - total: Quantidade de funcionários

    Critério: Funcionário possui registros em comissoes_itens OU
              possui configuração em comissoes_configuracao
    """

    struct_logger.info(
        "COMMISSION_EMPLOYEES_LIST", "Consulta de funcionários com comissões"
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

        logger.info(f"Retornando {len(funcionarios)} funcionários com comissões")

        return {"success": True, "lista": funcionarios, "total": len(funcionarios)}

    except Exception as e:
        logger.error(f"Erro ao listar funcionários com comissões: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao consultar funcionários: {str(e)}"
        )


@router.post("/fechar", summary="Fechar comissões (alterar status para pago)")
async def fechar_comissoes(
    request: FecharComissoesRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
) -> Dict[str, Any]:
    """
    Fecha comissões alterando status para 'pago'.

    ⚠️ IMPORTANTE:
    - NÃO recalcula valores (snapshot imutável)
    - Altera APENAS: status, data_pagamento, observacao_pagamento
    - Só processa comissões com status='pendente'
    - Ignora silenciosamente comissões já pagas/estornadas

    Regras:
    - Comissões já pagas: ignoradas
    - Comissões estornadas: ignoradas
    - Apenas status='pendente' são fechadas
    - Operação em transação única

    Returns:
    - total_processadas: Quantidade fechada com sucesso
    - total_ignoradas: Quantidade já paga/estornada
    - comissoes_fechadas: IDs das comissões processadas
    - comissoes_ignoradas: IDs ignorados
    """

    struct_logger.info(
        "COMMISSION_CLOSE_START",
        f"Iniciando fechamento de {len(request.comissoes_ids)} comissões",
        extra={
            "ids_count": len(request.comissoes_ids),
            "data_pagamento": str(request.data_pagamento),
            "has_observacao": bool(request.observacao),
        },
    )

    try:
        db = SessionLocal()

        try:
            resultado = fechar_comissoes_pendentes(
                db=db,
                request=request,
                current_user=user_and_tenant[0],
                struct_logger=struct_logger,
            )
        finally:
            db.close()

        return {
            "success": True,
            **resultado,
            "data_pagamento": str(request.data_pagamento),
            "message": f"{resultado['total_processadas']} comissão(ões) fechada(s) com sucesso",
        }

    except Exception as e:
        logger.error(f"Erro ao fechar comissões: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Erro ao fechar comissões: {str(e)}"
        )
