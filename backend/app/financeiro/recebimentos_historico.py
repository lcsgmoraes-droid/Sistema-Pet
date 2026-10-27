"""Histórico de recibos, enriquecido somente por vínculos explícitos do lote."""

from sqlalchemy.orm import joinedload

from app.financeiro_models import ContaReceber, Recebimento
from app.vendas_models import VendaBaixaLote, VendaBaixaLoteItem


def carregar_lotes_recebimentos(db, tenant_id, recebimentos):
    """Uma consulta por página; nunca associa recibos por data, valor ou texto."""
    por_id = {item.id: item for item in recebimentos}
    if not por_id:
        return {}
    vinculos = (
        db.query(VendaBaixaLoteItem, VendaBaixaLote)
        .join(VendaBaixaLote, VendaBaixaLote.id == VendaBaixaLoteItem.lote_id)
        .filter(
            VendaBaixaLoteItem.tenant_id == tenant_id,
            VendaBaixaLote.tenant_id == tenant_id,
            VendaBaixaLoteItem.venda_id.in_(
                {item.conta.venda_id for item in por_id.values() if item.conta.venda_id}
            ),
            VendaBaixaLoteItem.efeitos["recebimento_id"].as_integer().in_(por_id),
        )
        .all()
    )
    resultado = {}
    ambiguos = set()
    for item, lote in vinculos:
        efeitos = item.efeitos or {}
        recibo = por_id.get(efeitos.get("recebimento_id"))
        if (
            recibo is None
            or efeitos.get("conta_id") != recibo.conta_receber_id
            or item.venda_id != recibo.conta.venda_id
            or lote.cliente_id != recibo.conta.cliente_id
        ):
            continue
        if recibo.id in resultado:
            ambiguos.add(recibo.id)
        resultado[recibo.id] = lote
    return {chave: lote for chave, lote in resultado.items() if chave not in ambiguos}


def serializar_recebimento(item, tenant_id, lote=None):
    forma = item.forma_pagamento
    nome_forma = (
        forma.nome if forma and str(forma.tenant_id) == str(tenant_id) else None
    )
    observacoes = item.observacoes
    if lote:
        # Nos lotes anteriores, o recibo contém só "Baixa em lote - pix".
        # O texto digitado pelo operador está no lote, não nesse recibo.
        observacoes = (
            lote.observacoes
            or (lote.requisicao or {}).get("observacoes")
            or observacoes
        )
        nome_forma = nome_forma or lote.forma_pagamento
    return {
        "id": item.id,
        "recebimento_id": item.id,
        "conta_receber_id": item.conta_receber_id,
        "venda_id": item.conta.venda_id,
        "data_baixa": item.data_recebimento.isoformat(),
        "registrado_em": item.created_at.isoformat() if item.created_at else None,
        "valor": float(item.valor_recebido),
        "forma_pagamento": nome_forma or "Não informado",
        "observacoes": observacoes,
        "observacoes_recebimento": item.observacoes,
        "status": "estornado" if item.valor_recebido < 0 else "recebido",
        "origem": "baixa_lote" if lote else "recebimento",
        "baixa_lote_id": lote.id if lote else None,
    }


def consultar_recebimentos_venda(db, *, tenant_id, venda_id, page, per_page):
    consulta = (
        db.query(Recebimento)
        .join(ContaReceber, ContaReceber.id == Recebimento.conta_receber_id)
        .filter(
            Recebimento.tenant_id == tenant_id,
            ContaReceber.tenant_id == tenant_id,
            ContaReceber.venda_id == venda_id,
        )
    )
    total = consulta.count()
    recebimentos = (
        consulta.options(
            joinedload(Recebimento.conta), joinedload(Recebimento.forma_pagamento)
        )
        .order_by(Recebimento.data_recebimento.desc(), Recebimento.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    lotes = carregar_lotes_recebimentos(db, tenant_id, recebimentos)
    return {
        "venda_id": venda_id,
        "recebimentos": [
            serializar_recebimento(item, tenant_id, lotes.get(item.id))
            for item in recebimentos
        ],
        "paginacao": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": (total + per_page - 1) // per_page,
        },
    }
