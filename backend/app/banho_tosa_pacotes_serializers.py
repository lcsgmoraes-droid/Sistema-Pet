"""Serializadores do dominio de pacotes de Banho & Tosa."""

from datetime import date

from app.banho_tosa_pacotes import calcular_saldo_creditos


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
    }


def serializar_credito(credito) -> dict:
    saldo = calcular_saldo_creditos(credito.creditos_total, credito.creditos_usados, credito.creditos_cancelados)
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
        "saldo_creditos": saldo,
        "data_inicio": credito.data_inicio,
        "data_validade": credito.data_validade,
        "vencido": vencido,
        "disponivel": credito.status == "ativo" and not vencido and saldo > 0,
        "observacoes": credito.observacoes,
    }


def serializar_movimento(movimento) -> dict:
    return {
        "id": movimento.id,
        "credito_id": movimento.credito_id,
        "atendimento_id": movimento.atendimento_id,
        "movimento_origem_id": movimento.movimento_origem_id,
        "tipo": movimento.tipo,
        "quantidade": movimento.quantidade,
        "saldo_apos": movimento.saldo_apos,
        "observacoes": movimento.observacoes,
    }
