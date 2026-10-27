"""Serializadores do dominio de pacotes de Banho & Tosa."""

from datetime import date
from decimal import Decimal

from app.banho_tosa_pacotes import calcular_saldo_creditos
from app.banho_tosa_pacote_reservas import saldos_por_servico
from app.vendas.status_pagamento import calcular_resumo_pagamento_venda


def resumo_financeiro_credito(credito) -> dict:
    venda = getattr(credito, "venda", None)
    valor_pacote = Decimal(str(getattr(credito, "valor_pacote", 0) or 0))
    total = Decimal(str(venda.total or 0)) if venda else valor_pacote
    resumo = calcular_resumo_pagamento_venda(
        total=total,
        pagamentos=getattr(venda, "pagamentos", []) or [],
        contas_receber=getattr(venda, "contas_receber", []) or [],
    )
    pago = resumo["valor_pago"]
    status = "sem_venda"
    if venda:
        status = (
            "cancelado"
            if venda.status == "cancelada"
            else (
                "pendente"
                if resumo["status_pagamento"] == "em_aberto"
                else resumo["status_pagamento"]
            )
        )
    return {
        "status_pagamento": status,
        "valor_pacote": valor_pacote,
        "valor_pago": pago,
        "valor_restante": max(total - pago, Decimal("0")),
        "venda_numero": venda.numero_venda if venda else None,
        "pdv_url": f"/pdv?venda_id={venda.id}" if venda else None,
    }


def serializar_pacote(pacote) -> dict:
    return {
        "id": pacote.id,
        "nome": pacote.nome,
        "descricao": pacote.descricao,
        "servico_id": pacote.servico_id,
        "servico_nome": pacote.servico.nome if pacote.servico else None,
        "quantidade_creditos": pacote.quantidade_creditos,
        "validade_dias": pacote.validade_dias,
        "preco": pacote.preco,
        "ativo": pacote.ativo,
        "servicos": pacote.servicos
        or (
            [
                {
                    "servico_id": pacote.servico_id,
                    "servico_nome": pacote.servico.nome if pacote.servico else None,
                    "quantidade_creditos": pacote.quantidade_creditos,
                }
            ]
            if pacote.servico_id
            else []
        ),
    }


def serializar_credito(credito) -> dict:
    saldo_total = calcular_saldo_creditos(
        credito.creditos_total, credito.creditos_usados, credito.creditos_cancelados
    )
    reservados = getattr(credito, "creditos_reservados", 0) or 0
    saldo = max(saldo_total - reservados, Decimal("0"))
    vencido = credito.data_validade < date.today()
    pacote = credito.pacote
    return {
        "id": credito.id,
        "pacote_id": credito.pacote_id,
        "pacote_nome": pacote.nome if pacote else "Pacote",
        "servico_id": pacote.servico_id if pacote else None,
        "servico_nome": pacote.servico.nome if pacote and pacote.servico else None,
        "cliente_id": credito.cliente_id,
        "cliente_nome": credito.cliente.nome if credito.cliente else None,
        "pet_id": credito.pet_id,
        "pet_nome": credito.pet.nome if credito.pet else None,
        "venda_id": credito.venda_id,
        "status": credito.status,
        "creditos_total": credito.creditos_total,
        "creditos_usados": credito.creditos_usados,
        "creditos_cancelados": credito.creditos_cancelados,
        "creditos_reservados": reservados,
        "saldo_creditos": saldo,
        "saldo_total_creditos": saldo_total,
        "servicos": saldos_por_servico(credito),
        "data_inicio": credito.data_inicio,
        "data_validade": credito.data_validade,
        "vencido": vencido,
        "disponivel": credito.status == "ativo"
        and not vencido
        and credito.data_inicio <= date.today()
        and saldo > 0,
        "observacoes": credito.observacoes,
        **resumo_financeiro_credito(credito),
    }


def serializar_movimento(movimento) -> dict:
    return {
        "id": movimento.id,
        "credito_id": movimento.credito_id,
        "atendimento_id": movimento.atendimento_id,
        "agendamento_id": getattr(movimento, "agendamento_id", None),
        "servico_id": getattr(movimento, "servico_id", None),
        "movimento_origem_id": movimento.movimento_origem_id,
        "tipo": movimento.tipo,
        "quantidade": movimento.quantidade,
        "saldo_apos": movimento.saldo_apos,
        "observacoes": movimento.observacoes,
        "created_at": getattr(movimento, "created_at", None),
        "created_by": getattr(movimento, "created_by", None),
    }
