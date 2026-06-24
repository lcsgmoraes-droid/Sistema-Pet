import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.comissoes_demonstrativo_calculo import decimal_to_float
from app.financeiro_models import CategoriaFinanceira, ContaPagar, LancamentoManual
from app.models import Cliente
from app.utils.tenant_safe_sql import execute_tenant_safe

logger = logging.getLogger(__name__)


def fechar_comissoes_pendentes(
    *,
    db: Session,
    request: Any,
    current_user: Any,
    struct_logger: Any,
) -> Dict[str, Any]:
    from sqlalchemy import bindparam

    stmt = text("""
        SELECT id, status, valor_comissao_gerada
        FROM comissoes_itens
        WHERE id IN :ids
        AND {tenant_filter}
    """).bindparams(bindparam("ids", expanding=True))

    result = execute_tenant_safe(db, stmt, {"ids": tuple(request.comissoes_ids)})
    rows = result.fetchall()

    ids_pendentes = []
    ids_ignorados = []
    valor_total_fechamento = 0.0

    for row in rows:
        if row[1] == "pendente":
            ids_pendentes.append(row[0])
            valor_total_fechamento += decimal_to_float(row[2])
        else:
            ids_ignorados.append(row[0])

    logger.info("Pendentes: %s, Ignorados: %s", len(ids_pendentes), len(ids_ignorados))

    comissoes_fechadas = []
    if ids_pendentes:
        _marcar_comissoes_como_pagas(
            db=db,
            ids_pendentes=ids_pendentes,
            request=request,
            struct_logger=struct_logger,
        )
        comissoes_fechadas = list(ids_pendentes)
        db.commit()
        logger.info("%s comissoes fechadas com sucesso", len(comissoes_fechadas))

        _gerar_financeiro_fechamento(
            db=db,
            ids_pendentes=ids_pendentes,
            request=request,
            current_user=current_user,
            valor_total_fechamento=valor_total_fechamento,
        )
        db.commit()

    return {
        "total_processadas": len(comissoes_fechadas),
        "total_ignoradas": len(ids_ignorados),
        "comissoes_fechadas": comissoes_fechadas,
        "comissoes_ignoradas": ids_ignorados,
        "valor_total_fechamento": valor_total_fechamento,
    }


def _marcar_comissoes_como_pagas(
    *,
    db: Session,
    ids_pendentes: list[int],
    request: Any,
    struct_logger: Any,
) -> None:
    data_agora = datetime.now().isoformat()

    for comissao_id in ids_pendentes:
        execute_tenant_safe(
            db,
            """
            UPDATE comissoes_itens
            SET
                status = 'paga',
                data_pagamento = :data_pagamento,
                observacao_pagamento = :observacao,
                data_atualizacao = :data_atualizacao
            WHERE id = :comissao_id
            AND {tenant_filter}
        """,
            {
                "data_pagamento": str(request.data_pagamento),
                "observacao": request.observacao,
                "data_atualizacao": data_agora,
                "comissao_id": comissao_id,
            },
        )

        struct_logger.info(
            "COMMISSION_CLOSED",
            f"Comissão {comissao_id} fechada",
            extra={
                "comissao_id": comissao_id,
                "data_pagamento": str(request.data_pagamento),
            },
        )


def _gerar_financeiro_fechamento(
    *,
    db: Session,
    ids_pendentes: list[int],
    request: Any,
    current_user: Any,
    valor_total_fechamento: float,
) -> None:
    funcionario_id = _buscar_funcionario_id_da_comissao(db, ids_pendentes[0])
    funcionario_nome = _buscar_nome_funcionario(db, funcionario_id)
    categoria_comissao = _obter_categoria_comissao(db, current_user)
    periodo = request.data_pagamento.strftime("%m/%Y")

    conta_pagar = ContaPagar(
        descricao=f"Comissão - {funcionario_nome} - {periodo}",
        fornecedor_id=funcionario_id,
        categoria_id=categoria_comissao.id,
        valor_original=Decimal(str(valor_total_fechamento)),
        valor_final=Decimal(str(valor_total_fechamento)),
        data_emissao=request.data_pagamento,
        data_vencimento=request.data_pagamento,
        status="pendente",
        observacoes=(
            "Gerado automaticamente pelo fechamento de comissão. "
            f"{request.observacao or ''}"
        ),
        user_id=current_user.id,
    )
    db.add(conta_pagar)
    db.flush()

    lancamento = LancamentoManual(
        tipo="saida",
        valor=Decimal(str(valor_total_fechamento)),
        descricao=f"Pagamento de comissão - {funcionario_nome}",
        data_lancamento=request.data_pagamento,
        status="previsto",
        categoria_id=categoria_comissao.id,
        gerado_automaticamente=True,
        observacoes=(
            "Previsto gerado no fechamento de comissão "
            f"(Conta a Pagar #{conta_pagar.id})"
        ),
        user_id=current_user.id,
    )
    db.add(lancamento)

    logger.info(
        "Conta a pagar criada automaticamente: #%s - R$ %.2f - %s",
        conta_pagar.id,
        valor_total_fechamento,
        funcionario_nome,
    )
    logger.info(
        "Lançamento previsto criado: #%s - R$ %.2f",
        lancamento.id,
        valor_total_fechamento,
    )


def _buscar_funcionario_id_da_comissao(db: Session, comissao_id: int) -> int | None:
    result = execute_tenant_safe(
        db,
        "SELECT funcionario_id FROM comissoes_itens WHERE id = :id AND {tenant_filter}",
        {"id": comissao_id},
    )
    funcionario_row = result.fetchone()
    return funcionario_row[0] if funcionario_row else None


def _buscar_nome_funcionario(db: Session, funcionario_id: int | None) -> str:
    if not funcionario_id:
        return "Funcionário"

    funcionario = db.query(Cliente).filter(Cliente.id == funcionario_id).first()
    return funcionario.nome if funcionario else "Funcionário"


def _obter_categoria_comissao(db: Session, current_user: Any) -> CategoriaFinanceira:
    categoria_comissao = (
        db.query(CategoriaFinanceira)
        .filter(CategoriaFinanceira.nome.ilike("%comis%"))
        .first()
    )

    if categoria_comissao:
        return categoria_comissao

    categoria_comissao = CategoriaFinanceira(
        nome="Comissões",
        tipo="despesa",
        descricao="Comissões de vendas",
        user_id=current_user.id,
    )
    db.add(categoria_comissao)
    db.flush()
    return categoria_comissao
