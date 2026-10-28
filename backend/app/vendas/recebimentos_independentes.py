"""Recibos de títulos vinculados sem repetir suas partidas em VendaPagamento."""

from collections import defaultdict

from fastapi import HTTPException
from sqlalchemy.orm import joinedload

from app.contas_receber_encargos import dinheiro
from app.financeiro_models import Recebimento
from app.utils.pagamento_vinculos import pagamento_da_observacao
from app.vendas_models import VendaBaixaLoteItem


def _recusar_legado_sem_vinculo(conta_id):
    raise HTTPException(
        409,
        {
            "code": "PAGAMENTO_LEGADO_SEM_VINCULO",
            "mensagem": (
                f"A conta {conta_id} possui recebimento legado sem forma ou vínculo "
                "financeiro identificado. Confira os vínculos dos pagamentos antes "
                "de continuar; uma justificativa de excedente não resolve essa pendência."
            ),
            "conta_id": conta_id,
        },
    )


def pagamentos_representados_pelas_contas(venda, contas):
    """Partida monetária explícita de um repasse; plano não é recebimento."""
    from app.services.faturamento_composicao import eh_beneficio, eh_plano

    pagamentos = {
        p.id: p
        for p in venda.pagamentos
        if str(p.tenant_id) == str(venda.tenant_id)
        and p.venda_id == venda.id
        and not eh_plano(p)
        and not eh_beneficio(p.forma_pagamento)
    }
    return {
        conta.id: pagamentos[pagamento_id]
        for conta in contas
        if str(conta.tenant_id) == str(venda.tenant_id) and conta.venda_id == venda.id
        if (pagamento_id := pagamento_da_observacao(conta.observacoes)) in pagamentos
    }


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
    repasses = pagamentos_representados_pelas_contas(venda, contas)
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
    contas_por_id = {c.id: c for c in contas}
    eventos = []
    for recibo in recibos:
        valor = dinheiro(recibo.valor_recebido)
        por_conta[recibo.conta_receber_id] += valor
        if (
            f"recebimento-{recibo.id}" in identificados
            or recibo.conta_receber_id in repasses
            or pagamento_da_observacao(recibo.observacoes) in pagamentos_ids
            or recibo.id in espelhos
        ):
            continue
        conta = contas_por_id[recibo.conta_receber_id]
        if (
            pagamentos_ids
            and valor > 0
            and conta.forma_pagamento_id is None
            and recibo.forma_pagamento_id is None
        ):
            _recusar_legado_sem_vinculo(conta.id)
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
            if pagamentos_ids and conta.forma_pagamento_id is None:
                _recusar_legado_sem_vinculo(conta.id)
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
