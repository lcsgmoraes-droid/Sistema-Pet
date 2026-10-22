"""Recibos de títulos vinculados sem repetir suas partidas em VendaPagamento."""

from collections import defaultdict

from sqlalchemy.orm import joinedload

from app.contas_receber_encargos import dinheiro
from app.financeiro_models import Recebimento
from app.utils.pagamento_vinculos import pagamento_da_observacao
from app.vendas_models import VendaBaixaLoteItem


def carregar_recebimentos_independentes(
    db, *, venda, tenant_id, pagamentos_identificados, contas
):
    """Complementa eventos já identificados usando apenas vínculos por ID.

    Inclui baixas avulsas de previsões fora dos planos de crediário. Espelhos
    preservam o vínculo mesmo se o pagamento foi cancelado ou seu valor mudou.
    """
    from app.services.faturamento_composicao import data_local, eh_beneficio

    contas = [
        c
        for c in contas
        if str(c.tenant_id) == str(tenant_id)
        and c.venda_id == venda.id
        and str(c.status or "").strip().lower() not in {"cancelada", "cancelado"}
    ]
    if not contas:
        return []
    identificados = {str(p["id"]) for p in pagamentos_identificados}
    historico = [
        p
        for p in venda.pagamentos
        if str(p.tenant_id) == str(tenant_id) and p.venda_id == venda.id
    ]
    pagamentos_ids = {p.id for p in historico}
    lote_ids = {p.id for p in historico if p.baixa_lote_id is not None}
    espelhos = set()
    if lote_ids:
        vinculos = (
            db.query(VendaBaixaLoteItem)
            .filter(
                VendaBaixaLoteItem.tenant_id == tenant_id,
                VendaBaixaLoteItem.pagamento_id.in_(lote_ids),
            )
            .all()
        )
        espelhos = {
            v.efeitos.get("recebimento_id")
            for v in vinculos
            if isinstance(v.efeitos, dict)
        }
    recibos = (
        db.query(Recebimento)
        .options(joinedload(Recebimento.forma_pagamento))
        .filter(
            Recebimento.tenant_id == tenant_id,
            Recebimento.conta_receber_id.in_([c.id for c in contas]),
        )
        .populate_existing()
        .all()
    )
    por_conta = defaultdict(lambda: dinheiro(0))
    eventos = []
    for recibo in recibos:
        valor = dinheiro(recibo.valor_recebido)
        por_conta[recibo.conta_receber_id] += valor
        if (
            f"recebimento-{recibo.id}" in identificados
            or pagamento_da_observacao(recibo.observacoes) in pagamentos_ids
            or recibo.id in espelhos
        ):
            continue
        forma = getattr(recibo.forma_pagamento, "nome", None)
        eventos.append(
            {
                "id": f"recebimento-{recibo.id}",
                "origem": "recebimento",
                "forma_pagamento": forma or "Recebimento de parcela",
                "valor": float(valor),
                "data_pagamento": data_local(recibo.data_recebimento),
                "status": "recebido",
                "tipo": "beneficio" if eh_beneficio(forma) else "pagamento",
            }
        )
    for conta in contas:
        if (
            f"conta-{conta.id}" in identificados
            or pagamento_da_observacao(conta.observacoes) in pagamentos_ids
        ):
            continue
        legado = max(dinheiro(conta.valor_recebido) - por_conta[conta.id], dinheiro(0))
        if legado:
            eventos.append(
                {
                    "id": f"conta-{conta.id}",
                    "origem": "conta_legada",
                    "forma_pagamento": "Recebimento legado",
                    "valor": float(legado),
                    "data_pagamento": data_local(conta.data_recebimento),
                    "status": conta.status,
                    "tipo": "pagamento",
                }
            )
    return eventos
