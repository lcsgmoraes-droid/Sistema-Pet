"""Pagina referencias no banco e carrega apenas os movimentos exibidos."""

from datetime import datetime, time

from sqlalchemy import String, case, cast, func, literal, select, union_all
from sqlalchemy.orm import noload, selectinload

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
    fontes = [
        (
            Venda,
            Venda.data_venda,
            tipo_venda,
            Venda.status,
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
            ContaReceber.status,
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
        ).where(modelo.tenant_id == tenant_id, filtro_cliente)
        if modelo is Recebimento:
            consulta = consulta.join(
                ContaReceber, ContaReceber.id == Recebimento.conta_receber_id
            ).where(ContaReceber.tenant_id == tenant_id)
        if tipo:
            consulta = consulta.where(tipo_expr == tipo)
        if status:
            consulta = consulta.where(status_expr == status)
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
            }
            historico.append(
                {
                    "tipo": tipo_atual,
                    "data": item.data_venda.isoformat() if item.data_venda else None,
                    "descricao": f"{'Devolução - ' if devolucao else ''}Venda #{item.numero_venda}",
                    "valor": float(item.total or 0) * (-1 if devolucao else 1),
                    "status": item.status,
                    "detalhes": detalhes,
                }
            )
        elif tipo_atual == "recebimento":
            historico.append(
                {
                    "tipo": tipo_atual,
                    "data": _data_evento(item.data_recebimento),
                    "descricao": f"Recebimento - {item.conta.descricao}",
                    "valor": float(item.valor_recebido),
                    "status": "estornado" if item.valor_recebido < 0 else "efetivado",
                    "detalhes": {
                        "recebimento_id": item.id,
                        "conta_receber_id": item.conta_receber_id,
                        "venda_id": item.conta.venda_id,
                        "data_baixa": item.data_recebimento.isoformat(),
                        "registrado_em": item.created_at.isoformat()
                        if item.created_at
                        else None,
                        "forma_pagamento": item.forma_pagamento.nome
                        if item.forma_pagamento
                        else "Não informado",
                        "observacoes": item.observacoes,
                    },
                }
            )
        elif tipo_atual == "conta_receber":
            historico.append(
                {
                    "tipo": tipo_atual,
                    "data": _data_evento(item.data_emissao),
                    "descricao": item.descricao,
                    "valor": float(item.valor_final or 0),
                    "status": item.status,
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
