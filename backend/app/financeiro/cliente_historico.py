"""Pagina referencias no banco e carrega apenas os movimentos exibidos."""

from datetime import datetime, time

from sqlalchemy import String, case, cast, func, literal, select, union_all
from sqlalchemy.orm import noload, selectinload

from app.clientes.historico_compras import status_pagamento_sql
from app.financeiro.recebimentos_historico import (
    carregar_lotes_recebimentos,
    serializar_recebimento,
)
from app.financeiro_models import ContaReceber, Recebimento
from app.models import CreditoLog
from app.services.venda_descontos import resumo_descontos_venda
from app.vendas_models import Venda


def _data_evento(valor):
    if valor is None:
        return None
    # Datas de baixa/emissao sao dias locais. Sem a hora, new Date no navegador
    # interpreta YYYY-MM-DD como UTC e pode exibir o dia anterior no Brasil.
    return (
        valor if isinstance(valor, datetime) else datetime.combine(valor, time.min)
    ).isoformat()


def consultar_movimentos_cliente(
    db,
    *,
    tenant_id,
    cliente_id,
    page,
    per_page,
    data_inicio=None,
    data_fim=None,
    tipo=None,
    status=None,
):
    consultas = []
    tipo_venda = case(
        (Venda.status.in_(("cancelada", "devolvida")), "devolucao"), else_="venda"
    )
    status_recebimento = case(
        (Recebimento.valor_recebido < 0, "estornado"), else_="efetivado"
    )
    pagamentos, contas, situacao_venda = status_pagamento_sql(tenant_id)
    situacao_venda = case(
        (Venda.status.in_(("cancelada", "cancelado")), "cancelado"),
        else_=situacao_venda,
    )
    status_conta = func.lower(func.trim(func.coalesce(ContaReceber.status, "pendente")))
    situacao_conta = case(
        (status_conta.in_(("cancelada", "cancelado")), "cancelado"),
        (
            ContaReceber.valor_final - func.coalesce(ContaReceber.valor_recebido, 0)
            <= 0,
            "recebido",
        ),
        (status_conta.in_(("pago", "paga", "recebido", "quitado")), "recebido"),
        (status_conta.in_(("vencido", "vencida")), "vencido"),
        (func.coalesce(ContaReceber.valor_recebido, 0) > 0, "parcial"),
        (status_conta.in_(("baixa_parcial", "parcial")), "parcial"),
        (status_conta.in_(("pendente", "aberto", "aberta", "em_aberto")), "em_aberto"),
        else_=status_conta,
    )
    fontes = [
        (
            Venda,
            Venda.data_venda,
            tipo_venda,
            situacao_venda,
            Venda.cliente_id == cliente_id,
        ),
        (
            Recebimento,
            Recebimento.data_recebimento,
            literal("recebimento"),
            status_recebimento,
            ContaReceber.cliente_id == cliente_id,
        ),
        (
            ContaReceber,
            ContaReceber.data_emissao,
            literal("conta_receber"),
            situacao_conta,
            ContaReceber.cliente_id == cliente_id,
        ),
        (
            CreditoLog,
            CreditoLog.created_at,
            literal("credito"),
            literal("efetivado"),
            CreditoLog.cliente_id == cliente_id,
        ),
    ]
    for modelo, data, tipo_expr, status_expr, filtro_cliente in fontes:
        consulta = select(
            modelo.id.label("id"),
            tipo_expr.label("tipo"),
            cast(data, String).label("data"),
            status_expr.label("situacao"),
        ).where(modelo.tenant_id == tenant_id, filtro_cliente)
        if modelo is Venda:
            consulta = consulta.outerjoin(
                pagamentos, pagamentos.c.venda_id == Venda.id
            ).outerjoin(contas, contas.c.venda_id == Venda.id)
        if modelo is Recebimento:
            consulta = consulta.join(
                ContaReceber, ContaReceber.id == Recebimento.conta_receber_id
            ).where(ContaReceber.tenant_id == tenant_id)
        if tipo:
            consulta = consulta.where(tipo_expr == tipo)
        if status:
            filtro_status = status
            if modelo is Venda and status in {"cancelada", "recebido"}:
                filtro_status = "cancelado" if status == "cancelada" else "pago"
            elif modelo is Recebimento and status == "recebido":
                filtro_status = "efetivado"
            elif modelo is ContaReceber:
                filtro_status = {
                    "pendente": "em_aberto",
                    "aberto": "em_aberto",
                    "aberta": "em_aberto",
                    "baixa_parcial": "parcial",
                    "vencida": "vencido",
                    "pago": "recebido",
                    "paga": "recebido",
                    "cancelada": "cancelado",
                }.get(status, status)
            consulta = consulta.where(status_expr == filtro_status)
        if data_inicio:
            consulta = consulta.where(data >= data_inicio)
        if data_fim:
            consulta = consulta.where(data < data_fim)
        consultas.append(consulta)

    movimentos = union_all(*consultas).subquery()
    total = db.execute(select(func.count()).select_from(movimentos)).scalar_one()
    referencias = (
        db.execute(
            select(movimentos)
            .order_by(
                movimentos.c.data.desc(),
                movimentos.c.tipo,
                movimentos.c.id.desc(),
            )
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        .mappings()
        .all()
    )

    por_tipo = {}
    for ref in referencias:
        por_tipo.setdefault(ref["tipo"], []).append(ref["id"])
    registros = {}
    for tipo_atual, ids in por_tipo.items():
        modelo = {
            "venda": Venda,
            "devolucao": Venda,
            "recebimento": Recebimento,
            "conta_receber": ContaReceber,
            "credito": CreditoLog,
        }[tipo_atual]
        consulta = db.query(modelo).filter(
            modelo.tenant_id == tenant_id, modelo.id.in_(ids)
        )
        if modelo is Venda:
            consulta = consulta.options(
                selectinload(Venda.pagamentos),
                selectinload(Venda.itens),
                noload(Venda.contas_receber),
            )
        elif modelo is Recebimento:
            consulta = consulta.options(
                selectinload(Recebimento.conta),
                selectinload(Recebimento.forma_pagamento),
            )
        registros[tipo_atual] = {item.id: item for item in consulta.all()}

    lotes_recebimentos = carregar_lotes_recebimentos(
        db, tenant_id, registros.get("recebimento", {}).values()
    )
    historico = []
    for ref in referencias:
        tipo_atual = ref["tipo"]
        item = registros[tipo_atual][ref["id"]]
        if tipo_atual in ("venda", "devolucao"):
            devolucao = tipo_atual == "devolucao"
            detalhes = {
                "venda_id": item.id,
                "numero_venda": item.numero_venda,
                "subtotal": float(item.subtotal or 0),
                "desconto": float(item.desconto_valor or 0),
                **resumo_descontos_venda(item),
                "cupom_discount_applied": float(item.cupom_discount_applied or 0),
                "total": float(item.total or 0),
                "canal": item.canal,
                "forma_pagamento": item.pagamentos[0].forma_pagamento
                if item.pagamentos
                else "Não informado",
                "observacoes": item.observacoes,
                "status_pagamento": ref["situacao"],
                "status_operacional": item.status,
            }
            historico.append(
                {
                    "tipo": tipo_atual,
                    "data": item.data_venda.isoformat() if item.data_venda else None,
                    "descricao": f"{'Devolução - ' if devolucao else ''}Venda #{item.numero_venda}",
                    "valor": float(item.total or 0) * (-1 if devolucao else 1),
                    "status": item.status,
                    "status_pagamento": ref["situacao"],
                    "status_operacional": item.status,
                    "detalhes": detalhes,
                }
            )
        elif tipo_atual == "recebimento":
            detalhes = serializar_recebimento(
                item, tenant_id, lotes_recebimentos.get(item.id)
            )
            detalhes["status_recebimento"] = detalhes["status"]
            historico.append(
                {
                    "tipo": tipo_atual,
                    "data": _data_evento(item.data_recebimento),
                    "descricao": f"Recebimento - {item.conta.descricao}",
                    "valor": float(item.valor_recebido),
                    "status": "estornado" if item.valor_recebido < 0 else "efetivado",
                    "detalhes": detalhes,
                }
            )
        elif tipo_atual == "conta_receber":
            historico.append(
                {
                    "tipo": tipo_atual,
                    "data": _data_evento(item.data_emissao),
                    "descricao": item.descricao,
                    "valor": float(item.valor_final or 0),
                    "status": ref["situacao"],
                    "detalhes": {
                        "conta_receber_id": item.id,
                        "venda_id": item.venda_id,
                        "data_vencimento": item.data_vencimento.isoformat()
                        if item.data_vencimento
                        else None,
                        "valor_recebido": float(item.valor_recebido or 0),
                        "observacoes": item.observacoes,
                    },
                }
            )
        else:
            historico.append(
                {
                    "tipo": tipo_atual,
                    "data": item.created_at.isoformat() if item.created_at else None,
                    "descricao": item.motivo or "Movimentação de crédito",
                    "valor": float(item.valor or 0),
                    "status": "efetivado",
                    "detalhes": {
                        "tipo": item.tipo,
                        "saldo_anterior": float(item.saldo_anterior or 0),
                        "saldo_atual": float(item.saldo_atual or 0),
                        "usuario": item.usuario_nome,
                    },
                }
            )
    return historico, total
