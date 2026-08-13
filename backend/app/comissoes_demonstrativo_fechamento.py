"""Serviço transacional de fechamento de comissões sem pagamento imediato."""

import logging
from typing import Any, Dict

from fastapi import HTTPException
from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.comissoes_demonstrativo_calculo import decimal_to_float
from app.utils.tenant_safe_sql import execute_tenant_safe

logger = logging.getLogger(__name__)


def fechar_comissoes_pendentes(
    *,
    db: Session,
    request: Any,
    current_user: Any,
    struct_logger: Any,
) -> Dict[str, Any]:
    """Fecha comissões em uma única transação, sem gerar nova despesa."""
    del current_user  # A conta a pagar já foi criada no provisionamento da venda.

    ids_solicitados = list(dict.fromkeys(request.comissoes_ids))
    if not ids_solicitados:
        raise HTTPException(status_code=400, detail="Nenhuma comissão selecionada")

    lock_clause = (
        " FOR UPDATE" if db.bind and db.bind.dialect.name == "postgresql" else ""
    )
    stmt = text(
        f"""
        SELECT
            ci.id,
            ci.status,
            ci.valor_comissao_gerada,
            ci.funcionario_id,
            ci.conta_pagar_id,
            COALESCE(ci.comissao_provisionada, false) AS provisionada,
            cp.status AS conta_status
        FROM comissoes_itens ci
        LEFT JOIN contas_pagar cp
          ON cp.id = ci.conta_pagar_id
         AND cp.tenant_id = ci.tenant_id
        WHERE ci.id IN :ids
          AND ci.{{tenant_filter}}
        {lock_clause}
        """
    ).bindparams(bindparam("ids", expanding=True))
    rows = execute_tenant_safe(db, stmt, {"ids": tuple(ids_solicitados)}).fetchall()

    encontrados = {row.id for row in rows}
    ids_ignorados = [
        item_id for item_id in ids_solicitados if item_id not in encontrados
    ]
    pendentes = []
    for row in rows:
        if row.status == "pendente":
            pendentes.append(row)
        else:
            ids_ignorados.append(row.id)

    if not pendentes:
        return {
            "total_processadas": 0,
            "total_ignoradas": len(ids_ignorados),
            "comissoes_fechadas": [],
            "comissoes_ignoradas": ids_ignorados,
            "valor_total_fechamento": 0.0,
        }

    funcionarios = {row.funcionario_id for row in pendentes}
    if len(funcionarios) != 1:
        raise HTTPException(
            status_code=400,
            detail="Selecione comissões de apenas um funcionário por fechamento.",
        )

    sem_provisao = [
        row.id
        for row in pendentes
        if not row.provisionada
        or not row.conta_pagar_id
        or row.conta_status not in {"pendente", "vencido"}
    ]
    if sem_provisao:
        raise HTTPException(
            status_code=409,
            detail=(
                "Existem comissões sem uma conta a pagar pendente e válida: "
                + ", ".join(str(item_id) for item_id in sem_provisao)
                + ". Reprovisione essas comissões antes do fechamento."
            ),
        )

    ids_pendentes = [row.id for row in pendentes]
    update_stmt = text(
        """
        UPDATE comissoes_itens
        SET status = 'fechada',
            data_fechamento = :data_fechamento,
            observacao_pagamento = :observacao,
            data_atualizacao = CURRENT_TIMESTAMP
        WHERE id IN :ids
          AND status = 'pendente'
          AND {tenant_filter}
        """
    ).bindparams(bindparam("ids", expanding=True))
    execute_tenant_safe(
        db,
        update_stmt,
        {
            "ids": tuple(ids_pendentes),
            "data_fechamento": request.data_pagamento,
            "observacao": request.observacao,
        },
    )

    valor_total = sum(decimal_to_float(row.valor_comissao_gerada) for row in pendentes)
    for comissao_id in ids_pendentes:
        struct_logger.info(
            "COMMISSION_CLOSED",
            f"Comissão {comissao_id} fechada sem pagamento",
            extra={
                "comissao_id": comissao_id,
                "data_fechamento": str(request.data_pagamento),
            },
        )

    db.commit()
    logger.info("%s comissões fechadas sem duplicar o financeiro", len(ids_pendentes))
    return {
        "total_processadas": len(ids_pendentes),
        "total_ignoradas": len(ids_ignorados),
        "comissoes_fechadas": ids_pendentes,
        "comissoes_ignoradas": ids_ignorados,
        "valor_total_fechamento": valor_total,
    }
