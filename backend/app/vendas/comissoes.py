from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy.orm import Session

from ..utils.logger import logger as struct_logger
from ..utils.tenant_safe_sql import execute_tenant_safe


logger = logging.getLogger(__name__)


def _listar_pagamentos_venda_para_comissao(db: Session, venda_id: int, tenant_id):
    return execute_tenant_safe(
        db,
        """
        SELECT vp.id, vp.forma_pagamento, vp.valor, vp.data_pagamento
        FROM venda_pagamentos vp
        WHERE vp.venda_id = :venda_id
          AND vp.{tenant_filter}
        ORDER BY vp.data_pagamento ASC
    """,
        {"venda_id": venda_id},
        tenant_id=tenant_id,
    ).fetchall()


def _parcelas_com_comissao_funcionario(
    db: Session,
    venda_id: int,
    funcionario_id: int,
    tenant_id,
) -> set:
    rows = execute_tenant_safe(
        db,
        """
        SELECT DISTINCT parcela_numero
        FROM comissoes_itens
        WHERE venda_id = :venda_id
          AND funcionario_id = :funcionario_id
          AND {tenant_filter}
    """,
        {
            "venda_id": venda_id,
            "funcionario_id": funcionario_id,
        },
        tenant_id=tenant_id,
    ).fetchall()
    return {row[0] for row in rows}


def _gerar_comissoes_pendentes_venda(
    db: Session,
    venda,
    tenant_id,
    trigger: str,
) -> dict:
    """Gera comissoes somente para pagamentos ainda sem comissao."""
    if not venda.funcionario_id:
        return {"comissoes_geradas": 0, "total_comissoes": 0.0}

    from app.comissoes_service import gerar_comissoes_venda

    todos_pagamentos = _listar_pagamentos_venda_para_comissao(db, venda.id, tenant_id)
    if not todos_pagamentos:
        logger.info(
            "Nenhum pagamento encontrado na venda %s para gerar comissao", venda.id
        )
        return {"comissoes_geradas": 0, "total_comissoes": 0.0}

    parcelas_com_comissao = _parcelas_com_comissao_funcionario(
        db,
        venda.id,
        venda.funcionario_id,
        tenant_id,
    )

    comissoes_geradas = 0
    total_comissoes = Decimal("0")

    for idx, pagamento_row in enumerate(todos_pagamentos, start=1):
        parcela_numero = idx
        if parcela_numero in parcelas_com_comissao:
            logger.info("Parcela %s ja tem comissao - pulando", parcela_numero)
            continue

        valor_pagamento = Decimal(str(pagamento_row[2]))
        forma_pagamento = pagamento_row[1]

        struct_logger.info(
            event="COMMISSION_START",
            message="Gerando comissao pendente para pagamento",
            venda_id=venda.id,
            funcionario_id=venda.funcionario_id,
            valor_pago=float(valor_pagamento),
            forma_pagamento=forma_pagamento,
            parcela_numero=parcela_numero,
            trigger=trigger,
        )

        resultado = gerar_comissoes_venda(
            venda_id=venda.id,
            funcionario_id=venda.funcionario_id,
            valor_pago=valor_pagamento,
            forma_pagamento=forma_pagamento,
            parcela_numero=parcela_numero,
            db=db,
        )

        if resultado and resultado.get("success") and not resultado.get("duplicated"):
            comissoes_geradas += 1
            total_comissoes += Decimal(str(resultado.get("total_comissao", 0)))

    return {
        "comissoes_geradas": comissoes_geradas,
        "total_comissoes": float(total_comissoes),
    }


def _total_pago_venda(db: Session, venda_id: int, tenant_id) -> Decimal:
    row = execute_tenant_safe(
        db,
        """
        SELECT COALESCE(SUM(valor), 0) as total_pago
        FROM venda_pagamentos
        WHERE venda_id = :venda_id
          AND {tenant_filter}
    """,
        {"venda_id": venda_id},
        tenant_id=tenant_id,
    ).fetchone()
    return Decimal(str(row[0])) if row else Decimal("0")


def _contar_comissoes_venda(db: Session, venda_id: int, tenant_id) -> int:
    return (
        execute_tenant_safe(
            db,
            """
        SELECT COUNT(*) FROM comissoes_itens
        WHERE venda_id = :venda_id
          AND {tenant_filter}
    """,
            {"venda_id": venda_id},
            tenant_id=tenant_id,
        ).scalar()
        or 0
    )


def _remover_comissoes_venda(db: Session, venda_id: int, tenant_id) -> None:
    execute_tenant_safe(
        db,
        """
        DELETE FROM comissoes_itens
        WHERE venda_id = :venda_id
          AND {tenant_filter}
    """,
        {"venda_id": venda_id},
        tenant_id=tenant_id,
    )


def _remover_provisoes_comissao_venda(db: Session, venda_id: int, tenant_id) -> None:
    execute_tenant_safe(
        db,
        """
        DELETE FROM contas_pagar
        WHERE {tenant_filter}
          AND descricao LIKE :descricao
          AND status = 'pendente'
    """,
        {"descricao": f"%Comiss\u00e3o - Venda #{venda_id}%"},
        tenant_id=tenant_id,
    )
