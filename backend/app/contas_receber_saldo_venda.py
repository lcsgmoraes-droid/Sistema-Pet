"""Limita baixas diretas ao saldo comprovado, sem conceder exceções do PDV."""

from collections import defaultdict

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from app.contas_receber_encargos import dinheiro
from app.financeiro_models import ContaReceber
from app.vendas.edicao_pagamentos import fotografar_pagamentos_edicao
from app.vendas.recebimentos_independentes import pagamentos_representados_pelas_contas
from app.vendas.status_pagamento import pagamento_valido_para_saldo
from app.vendas_models import Venda


def bloquear_contas_e_vendas(db, *, tenant_id, conta_ids):
    """Todos os callers seguem Venda por ID → Contas por ID, inclusive no lote."""
    referencias = dict(
        db.query(ContaReceber.id, ContaReceber.venda_id)
        .filter(ContaReceber.tenant_id == tenant_id, ContaReceber.id.in_(conta_ids))
        .all()
    )
    faltantes = sorted(set(conta_ids) - referencias.keys())
    if faltantes:
        raise HTTPException(
            404, "Conta(s) não encontrada(s): " + ", ".join(map(str, faltantes))
        )
    venda_ids = {ident for ident in referencias.values() if ident is not None}
    vendas = (
        db.query(Venda)
        .filter(Venda.tenant_id == tenant_id, Venda.id.in_(venda_ids))
        .order_by(Venda.id)
        .populate_existing()
        .with_for_update(of=Venda)
        .all()
        if venda_ids
        else []
    )
    if {v.id for v in vendas} != venda_ids:
        raise HTTPException(
            409,
            "A venda vinculada não está disponível. Revise a conta antes de receber.",
        )
    contas = (
        db.query(ContaReceber)
        .options(joinedload(ContaReceber.forma_pagamento))
        .filter(
            ContaReceber.tenant_id == tenant_id,
            or_(ContaReceber.id.in_(conta_ids), ContaReceber.venda_id.in_(venda_ids)),
        )
        .order_by(ContaReceber.id)
        .populate_existing()
        .with_for_update(of=ContaReceber)
        .all()
    )
    por_id = {c.id: c for c in contas}
    if any(
        ident not in por_id or por_id[ident].venda_id != venda_id
        for ident, venda_id in referencias.items()
    ):
        raise HTTPException(
            409, "O vínculo da conta mudou. Atualize a página antes de receber."
        )
    return por_id, {v.id: v for v in vendas}


def validar_saldo_vendas(db, *, tenant_id, vendas, contas, baixas):
    """Valida o lote inteiro antes de alterar qualquer título ou criar recibos.

    ``baixas`` contém (conta real, prévia isolada, valor recebido). Encargos
    cumulativos já persistidos são substituídos pelos da prévia, sem ratear
    juros entre recibos nem presumir que eles compõem o preço da venda.
    """
    por_venda = defaultdict(list)
    for conta in contas.values():
        if conta.venda_id in vendas and str(conta.status).lower() not in {
            "cancelado",
            "cancelada",
        }:
            por_venda[conta.venda_id].append(conta)
    novas_baixas = defaultdict(lambda: dinheiro(0))
    previas = {}
    repasses = {}
    fotografias = {}
    for venda_id, venda in vendas.items():
        if str(venda.status or "").strip().lower() in {"cancelada", "cancelado"}:
            raise HTTPException(
                409,
                "A venda vinculada está cancelada. Revise a venda pelo PDV antes de receber.",
            )
        # Carrega o histórico sob o lock da venda antes de distinguir repasse.
        fotografias[venda_id] = fotografar_pagamentos_edicao(
            db, venda=venda, tenant_id=tenant_id
        )
        repasses[venda_id] = pagamentos_representados_pelas_contas(
            venda, por_venda[venda_id]
        )
    for conta, previa, valor in baixas:
        if conta.venda_id in vendas:
            partida = repasses[conta.venda_id].get(conta.id)
            if partida is not None:
                if (
                    not pagamento_valido_para_saldo(partida)
                    or dinheiro(partida.valor) <= 0
                ):
                    raise HTTPException(
                        409,
                        "A partida do repasse não está ativa. Revise a venda pelo PDV antes de receber.",
                    )
            else:
                novas_baixas[conta.venda_id] += dinheiro(valor)
            previas[conta.id] = previa
    for venda_id, venda in vendas.items():
        if novas_baixas[venda_id] == 0:
            continue
        fotografia = fotografias[venda_id]
        titulos = [c for c in por_venda[venda_id] if c.id not in repasses[venda_id]]
        recebido = fotografia["total_ja_pago"]
        encargos = sum(
            (
                dinheiro(getattr(previas.get(c.id, c), "valor_juros"))
                + dinheiro(getattr(previas.get(c.id, c), "valor_multa"))
                - dinheiro(getattr(previas.get(c.id, c), "valor_desconto"))
                for c in titulos
            ),
            dinheiro(0),
        )
        limite = max(dinheiro(venda.total) + encargos, dinheiro(0))
        if max(recebido, dinheiro(0)) + novas_baixas[venda_id] > limite:
            raise HTTPException(
                409,
                f"O recebimento ultrapassa o saldo da venda {venda.numero_venda}. Revise a venda e os pagamentos pelo PDV; uma exceção de recebimento exige justificativa nesse fluxo.",
            )
