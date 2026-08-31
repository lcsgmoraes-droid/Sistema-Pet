"""Rotas de consulta e resumo de contas a receber."""

from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.orm import Session, joinedload

from .auth.dependencies import get_current_user_and_tenant
from .contas_receber_encargos import (
    calcular_encargos_automaticos,
    carregar_config_encargos,
    serializar_calculo_encargos,
)
from .contas_receber_schemas import ContaReceberResponse
from .db import get_session
from .clientes.common import _somente_digitos_coluna
from .financeiro.contas_pagar_common import (
    _expressao_texto_busca,
    _normalizar_texto_busca,
)
from .financeiro_models import ContaReceber
from .models import Cliente
from .utils.timezone import now_brasilia

router = APIRouter()

STATUS_CONTAS_RECEBER_EM_ABERTO = ("pendente", "parcial", "vencido", "vencida")


def _montar_condicao_busca_contas_receber(tenant_id, busca: str):
    """Monta a busca geral sem permitir resultados de outra empresa."""
    from .vendas_models import Venda

    termo_busca = (busca or "").strip()
    busca_pattern = f"%{_normalizar_texto_busca(termo_busca)}%"
    termo_digitos = "".join(ch for ch in termo_busca if ch.isdigit())

    filtros_cliente = [
        _expressao_texto_busca(Cliente.codigo).like(busca_pattern),
        _expressao_texto_busca(Cliente.nome).like(busca_pattern),
        _expressao_texto_busca(Cliente.nome_fantasia).like(busca_pattern),
        _expressao_texto_busca(Cliente.razao_social).like(busca_pattern),
        _expressao_texto_busca(Cliente.telefone).like(busca_pattern),
        _expressao_texto_busca(Cliente.celular).like(busca_pattern),
    ]
    if termo_digitos:
        digitos_pattern = f"%{termo_digitos}%"
        filtros_cliente.extend(
            [
                _somente_digitos_coluna(Cliente.telefone).like(digitos_pattern),
                _somente_digitos_coluna(Cliente.celular).like(digitos_pattern),
            ]
        )

    clientes_match = select(Cliente.id).where(
        Cliente.tenant_id == tenant_id,
        or_(*filtros_cliente),
    )
    vendas_match = select(Venda.id).where(
        Venda.tenant_id == tenant_id,
        _expressao_texto_busca(Venda.numero_venda).like(busca_pattern),
    )

    return or_(
        _expressao_texto_busca(ContaReceber.descricao).like(busca_pattern),
        _expressao_texto_busca(ContaReceber.documento).like(busca_pattern),
        ContaReceber.cliente_id.in_(clientes_match),
        ContaReceber.venda_id.in_(vendas_match),
    )


@router.get("/", response_model=List[ContaReceberResponse])
def listar_contas_receber(
    status: Optional[str] = Query(None),
    cliente_id: Optional[int] = Query(None),
    categoria_id: Optional[int] = Query(None),
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    apenas_vencidas: bool = Query(False),
    apenas_vencer: bool = Query(False),
    busca: Optional[str] = Query(None),
    numero_venda: Optional[str] = Query(None),  # Filtro por número da venda
    limit: int = Query(500, le=1000),  # Aumentado para 500 registros por padrão
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Lista contas a receber com filtros
    """
    _current_user, tenant_id = user_and_tenant
    hoje = now_brasilia().date()
    from app.vendas_models import Venda

    query = (
        db.query(ContaReceber)
        .options(
            joinedload(ContaReceber.categoria),
            joinedload(ContaReceber.forma_pagamento),
        )
        .filter(ContaReceber.tenant_id == tenant_id)
    )

    # Filtros
    if status:
        status_normalizado = status.strip().lower()
        if status_normalizado == "em_aberto":
            query = query.filter(
                ContaReceber.status.in_(STATUS_CONTAS_RECEBER_EM_ABERTO)
            )
        else:
            query = query.filter(ContaReceber.status == status_normalizado)
    if cliente_id:
        query = query.filter(ContaReceber.cliente_id == cliente_id)
    if categoria_id:
        query = query.filter(ContaReceber.categoria_id == categoria_id)
    if data_inicio:
        query = query.filter(ContaReceber.data_vencimento >= data_inicio)
    if data_fim:
        query = query.filter(ContaReceber.data_vencimento <= data_fim)

    termo_busca = (busca or "").strip()
    if termo_busca:
        query = query.filter(
            _montar_condicao_busca_contas_receber(tenant_id, termo_busca)
        )

    # Filtro por número de venda
    if numero_venda:
        vendas_ids = (
            db.query(Venda.id)
            .filter(
                Venda.tenant_id == tenant_id,
                Venda.numero_venda.like(f"%{numero_venda}%"),
            )
            .subquery()
        )
        query = query.filter(ContaReceber.venda_id.in_(vendas_ids))

    if apenas_vencidas:
        query = query.filter(
            and_(
                ContaReceber.status.in_(STATUS_CONTAS_RECEBER_EM_ABERTO),
                ContaReceber.data_vencimento < hoje,
            )
        )
    if apenas_vencer:
        query = query.filter(
            and_(
                ContaReceber.status.in_(STATUS_CONTAS_RECEBER_EM_ABERTO),
                ContaReceber.data_vencimento >= hoje,
            )
        )

    # Ordenar por ID DESC (mais recentes primeiro) e depois por data de vencimento
    query = query.order_by(desc(ContaReceber.id))
    contas = query.limit(limit).offset(offset).all()
    config_encargos = carregar_config_encargos(db, tenant_id)

    cliente_ids = {conta.cliente_id for conta in contas if conta.cliente_id}
    clientes_por_id = (
        {
            cliente.id: cliente
            for cliente in db.query(Cliente)
            .filter(Cliente.tenant_id == tenant_id, Cliente.id.in_(cliente_ids))
            .all()
        }
        if cliente_ids
        else {}
    )
    venda_ids = {conta.venda_id for conta in contas if conta.venda_id}
    numeros_venda_por_id = (
        {
            venda_id: numero
            for venda_id, numero in db.query(Venda.id, Venda.numero_venda)
            .filter(Venda.tenant_id == tenant_id, Venda.id.in_(venda_ids))
            .all()
        }
        if venda_ids
        else {}
    )

    # Montar response
    resultado = []
    for conta in contas:
        calculo_encargos = serializar_calculo_encargos(
            calcular_encargos_automaticos(conta, hoje, config_encargos)
        )
        # Calcular dias para vencimento
        dias_venc = None
        if conta.status == "pendente":
            dias_venc = (conta.data_vencimento - hoje).days

        # Buscar nome do cliente
        cliente = clientes_por_id.get(conta.cliente_id)
        cliente_nome = cliente.nome if cliente else None

        # Buscar número da venda se existir venda_id
        numero_venda = numeros_venda_por_id.get(conta.venda_id)

        resultado.append(
            {
                "id": conta.id,
                "descricao": conta.descricao,
                "cliente_id": conta.cliente_id,
                "cliente_nome": cliente_nome,
                "categoria_nome": conta.categoria.nome if conta.categoria else None,
                "valor_original": float(conta.valor_original),
                "valor_recebido": float(conta.valor_recebido),
                "valor_final": float(conta.valor_final),
                "data_emissao": conta.data_emissao,
                "data_vencimento": conta.data_vencimento,
                "data_recebimento": conta.data_recebimento,
                "status": conta.status,
                "dias_vencimento": dias_venc,
                "eh_parcelado": conta.eh_parcelado,
                "numero_parcela": conta.numero_parcela,
                "total_parcelas": conta.total_parcelas,
                "documento": conta.documento,
                "venda_id": conta.venda_id,
                "numero_venda": numero_venda,
                "forma_pagamento_id": conta.forma_pagamento_id,
                "forma_pagamento_tipo": (
                    conta.forma_pagamento.tipo if conta.forma_pagamento else None
                ),
                **calculo_encargos,
                "observacoes": conta.observacoes,
                # Conciliação de cartão
                "nsu": conta.nsu,
                "adquirente": conta.adquirente,
                "conciliado": conta.conciliado,
                "data_conciliacao": conta.data_conciliacao,
            }
        )

    return resultado


# ============================================================================
# BUSCAR CONTA ESPECÍFICA
# ============================================================================


@router.get("/{conta_id}")
def buscar_conta_receber(
    conta_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Busca uma conta a receber específica com todos os detalhes
    """
    from .vendas_models import Venda
    from .financeiro_models import ContaBancaria

    _current_user, tenant_id = user_and_tenant

    conta = (
        db.query(ContaReceber)
        .options(
            joinedload(ContaReceber.categoria),
            joinedload(ContaReceber.recebimentos),
            joinedload(ContaReceber.forma_pagamento),
        )
        .filter(
            ContaReceber.id == conta_id,
            ContaReceber.tenant_id == tenant_id,
        )
        .first()
    )

    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")

    calculo_encargos = serializar_calculo_encargos(
        calcular_encargos_automaticos(
            conta,
            now_brasilia().date(),
            carregar_config_encargos(db, tenant_id),
        )
    )

    # Buscar cliente
    cliente = None
    if conta.cliente_id:
        cliente = (
            db.query(Cliente)
            .filter(
                Cliente.id == conta.cliente_id,
                Cliente.tenant_id == tenant_id,
            )
            .first()
        )

    # Buscar venda (se houver)
    venda = None
    if conta.venda_id:
        venda = (
            db.query(Venda)
            .filter(
                Venda.id == conta.venda_id,
                Venda.tenant_id == tenant_id,
            )
            .first()
        )

    # Buscar recebimentos com conta bancária
    recebimentos_detalhados = []
    for r in conta.recebimentos:
        conta_bancaria = None
        conta_bancaria_id = getattr(r, "conta_bancaria_id", None)
        if conta_bancaria_id:
            conta_bancaria = (
                db.query(ContaBancaria)
                .filter(
                    ContaBancaria.id == conta_bancaria_id,
                    ContaBancaria.tenant_id == tenant_id,
                )
                .first()
            )

        recebimentos_detalhados.append(
            {
                "id": r.id,
                "valor": float(r.valor_recebido),
                "data": r.data_recebimento,
                "forma_pagamento_id": r.forma_pagamento_id,
                "conta_bancaria_id": conta_bancaria_id,
                "conta_bancaria_nome": conta_bancaria.nome if conta_bancaria else None,
                "observacoes": r.observacoes,
            }
        )

    return {
        "id": conta.id,
        "descricao": conta.descricao,
        "cliente": (
            {
                "id": cliente.id if cliente else None,
                "nome": cliente.nome if cliente else None,
                "cpf": cliente.cpf if cliente else None,
            }
            if cliente
            else None
        ),
        "venda": (
            {
                "id": venda.id if venda else None,
                "numero_venda": venda.numero_venda if venda else None,
            }
            if venda
            else None
        ),
        "categoria": (
            {
                "id": conta.categoria.id if conta.categoria else None,
                "nome": conta.categoria.nome if conta.categoria else None,
                "cor": conta.categoria.cor if conta.categoria else None,
            }
            if conta.categoria
            else None
        ),
        "valores": {
            "original": float(conta.valor_original),
            "recebido": float(conta.valor_recebido),
            "desconto": float(conta.valor_desconto),
            "juros": float(conta.valor_juros),
            "multa": float(conta.valor_multa),
            "final": float(conta.valor_final),
            "saldo": float(conta.valor_final - conta.valor_recebido),
        },
        "datas": {
            "emissao": conta.data_emissao,
            "vencimento": conta.data_vencimento,
            "recebimento": conta.data_recebimento,
        },
        "status": conta.status,
        "encargos": calculo_encargos,
        "parcelamento": (
            {
                "eh_parcelado": conta.eh_parcelado,
                "numero_parcela": conta.numero_parcela,
                "total_parcelas": conta.total_parcelas,
            }
            if conta.eh_parcelado
            else None
        ),
        "documento": conta.documento,
        "observacoes": conta.observacoes,
        "recebimentos": recebimentos_detalhados,
    }


# ============================================================================
# REGISTRAR RECEBIMENTO
# ============================================================================


@router.get("/dashboard/resumo")
def dashboard_contas_receber(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    Resumo financeiro de contas a receber
    """
    _current_user, tenant_id = user_and_tenant
    hoje = date.today()

    # Total pendente
    total_pendente = (
        db.query(func.sum(ContaReceber.valor_final - ContaReceber.valor_recebido))
        .filter(
            and_(
                ContaReceber.tenant_id == tenant_id,
                ContaReceber.status.in_(["pendente", "parcial", "vencido"]),
            )
        )
        .scalar()
        or 0
    )

    # Vencidas
    total_vencido = (
        db.query(func.sum(ContaReceber.valor_final - ContaReceber.valor_recebido))
        .filter(
            and_(
                ContaReceber.tenant_id == tenant_id,
                ContaReceber.status == "pendente",
                ContaReceber.data_vencimento < hoje,
            )
        )
        .scalar()
        or 0
    )

    count_vencidas = (
        db.query(func.count(ContaReceber.id))
        .filter(
            and_(
                ContaReceber.tenant_id == tenant_id,
                ContaReceber.status == "pendente",
                ContaReceber.data_vencimento < hoje,
            )
        )
        .scalar()
    )

    # Vence hoje
    total_vence_hoje = (
        db.query(func.sum(ContaReceber.valor_final - ContaReceber.valor_recebido))
        .filter(
            and_(
                ContaReceber.tenant_id == tenant_id,
                ContaReceber.status == "pendente",
                ContaReceber.data_vencimento == hoje,
            )
        )
        .scalar()
        or 0
    )

    # Próximos 7 dias
    data_7dias = hoje + timedelta(days=7)
    total_7dias = (
        db.query(func.sum(ContaReceber.valor_final - ContaReceber.valor_recebido))
        .filter(
            and_(
                ContaReceber.tenant_id == tenant_id,
                ContaReceber.status == "pendente",
                ContaReceber.data_vencimento.between(hoje, data_7dias),
            )
        )
        .scalar()
        or 0
    )

    # Próximos 30 dias
    data_30dias = hoje + timedelta(days=30)
    total_30dias = (
        db.query(func.sum(ContaReceber.valor_final - ContaReceber.valor_recebido))
        .filter(
            and_(
                ContaReceber.tenant_id == tenant_id,
                ContaReceber.status == "pendente",
                ContaReceber.data_vencimento.between(hoje, data_30dias),
            )
        )
        .scalar()
        or 0
    )

    # Recebido no mês
    primeiro_dia_mes = hoje.replace(day=1)
    total_recebido_mes = (
        db.query(func.sum(ContaReceber.valor_recebido))
        .filter(
            and_(
                ContaReceber.tenant_id == tenant_id,
                ContaReceber.data_recebimento >= primeiro_dia_mes,
                ContaReceber.data_recebimento <= hoje,
            )
        )
        .scalar()
        or 0
    )

    return {
        "total_pendente": float(total_pendente),
        "vencidas": {"total": float(total_vencido), "quantidade": count_vencidas},
        "vence_hoje": float(total_vence_hoje),
        "proximos_7_dias": float(total_7dias),
        "proximos_30_dias": float(total_30dias),
        "recebido_mes_atual": float(total_recebido_mes),
    }


# ============================================================================
# PROCESSAR RECORRÊNCIAS
# ============================================================================
