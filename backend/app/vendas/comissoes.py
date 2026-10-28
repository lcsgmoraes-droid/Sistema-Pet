from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy.orm import Session

from ..utils.logger import logger as struct_logger
from ..utils.tenant_safe_sql import execute_tenant_safe
from .status_pagamento import pagamento_valido_para_saldo


logger = logging.getLogger(__name__)


def _listar_pagamentos_venda_para_comissao(db: Session, venda_id: int, tenant_id):
    return execute_tenant_safe(
        db,
        """
        SELECT vp.id, vp.forma_pagamento, vp.valor, vp.data_pagamento,
               vp.baixa_lote_id, vp.status
        FROM venda_pagamentos vp
        WHERE vp.venda_id = :venda_id
          AND vp.{tenant_filter}
        ORDER BY vp.data_pagamento ASC, vp.id ASC
    """,
        {"venda_id": venda_id},
        tenant_id=tenant_id,
    ).fetchall()


def _pagamentos_liquidos_para_comissao(pagamentos, *, total_venda=None):
    """Compensa o lote sem renumerar as parcelas históricas da comissão."""
    saldos_lotes = {}
    registros = []
    for parcela, pagamento in enumerate(pagamentos, start=1):
        lote_id = pagamento[4] if len(pagamento) > 4 else None
        status = pagamento[5] if len(pagamento) > 5 else None
        if not pagamento_valido_para_saldo({"status": status}):
            continue
        valor = Decimal(str(pagamento[2] or 0))
        chave_lote = (
            (lote_id, str(pagamento[1] or "").strip().casefold())
            if lote_id is not None
            else None
        )
        if chave_lote is not None:
            saldos_lotes[chave_lote] = (
                saldos_lotes.get(chave_lote, Decimal("0")) + valor
            )
        registros.append((parcela, pagamento, valor, chave_lote))

    disponivel = (
        max(Decimal(str(total_venda)), Decimal("0"))
        if total_venda is not None
        else None
    )
    for parcela, pagamento, valor, chave_lote in registros:
        if valor <= 0:
            continue
        if chave_lote is not None:
            valor = min(valor, max(saldos_lotes[chave_lote], Decimal("0")))
            saldos_lotes[chave_lote] -= valor
        # O recebimento pode ter excedente justificado. A comissão é da venda,
        # com teto compartilhado entre todas as parcelas, sem alterar o banco.
        if disponivel is not None:
            valor = min(valor, disponivel)
            disponivel -= valor
        if valor > 0:
            yield parcela, pagamento, valor


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


def _bloquear_venda_para_comissao(db: Session, venda_id: int, tenant_id):
    from app.vendas_models import Venda

    return (
        db.query(Venda)
        .filter_by(id=venda_id, tenant_id=tenant_id)
        .populate_existing()
        .with_for_update()
        .first()
    )


def _gerar_comissoes_pendentes_venda(
    db: Session,
    venda,
    tenant_id,
    trigger: str,
    pagamento_ids: set[int] | None = None,
) -> dict:
    """Gera comissoes somente para pagamentos ainda sem comissao."""
    if not venda.funcionario_id:
        return {"comissoes_geradas": 0, "total_comissoes": 0.0}

    from app.comissoes_service import gerar_comissoes_venda

    comissoes_geradas = 0
    total_comissoes = Decimal("0")
    tentados = set()
    venda_id = venda.id

    while True:
        # O gerador confirma cada parcela internamente. Reobtém o lock e lê o
        # saldo antes de cada geração para não usar pagamentos estornados entre
        # dois commits. A ordem Venda -> pagamentos é a mesma do estorno.
        venda = _bloquear_venda_para_comissao(db, venda_id, tenant_id)
        if not venda or not venda.funcionario_id:
            break
        todos_pagamentos = _listar_pagamentos_venda_para_comissao(
            db, venda.id, tenant_id
        )
        parcelas_com_comissao = _parcelas_com_comissao_funcionario(
            db, venda.id, venda.funcionario_id, tenant_id
        )
        pagamentos_efetivos = []
        recebido_anterior = Decimal("0")
        for parcela, pagamento, valor in _pagamentos_liquidos_para_comissao(
            todos_pagamentos, total_venda=venda.total
        ):
            pagamentos_efetivos.append((parcela, pagamento, valor, recebido_anterior))
            recebido_anterior += valor
        pendente = next(
            (
                (parcela, pagamento, valor, anterior)
                for parcela, pagamento, valor, anterior in pagamentos_efetivos
                if parcela not in parcelas_com_comissao
                and pagamento[0] not in tentados
                and (pagamento_ids is None or pagamento[0] in pagamento_ids)
            ),
            None,
        )
        if pendente is None:
            break
        parcela_numero, pagamento_row, valor_pagamento, valor_pago_anterior = pendente
        tentados.add(pagamento_row[0])
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
            tenant_id=tenant_id,
            valor_pago_anterior=valor_pago_anterior,
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
    from app.comissoes_financeiro_service import cancelar_provisoes_comissao_venda

    cancelar_provisoes_comissao_venda(
        db,
        venda_id=venda_id,
        tenant_id=tenant_id,
        motivo="Venda reaberta",
    )
