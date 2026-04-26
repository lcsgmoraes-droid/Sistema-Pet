"""Ponte entre atendimento de Banho & Tosa e venda do PDV."""

from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.banho_tosa_models import (
    BanhoTosaAgendamento,
    BanhoTosaAtendimento,
    BanhoTosaTaxiDog,
)
from app.vendas.service import VendaService
from app.vendas_models import Venda


def gerar_venda_atendimento(db: Session, tenant_id, user_id: int, atendimento_id: int) -> dict:
    atendimento = _obter_atendimento(db, tenant_id, atendimento_id)
    if not atendimento:
        raise HTTPException(status_code=404, detail="Atendimento nao encontrado")
    if atendimento.status in {"cancelado", "no_show"}:
        raise HTTPException(status_code=422, detail="Atendimento cancelado/no-show nao pode gerar venda")
    if atendimento.pacote_credito_id:
        raise HTTPException(status_code=422, detail="Atendimento ja foi quitado por pacote e nao deve gerar nova venda")

    venda_existente = _obter_venda_existente(db, tenant_id, atendimento)
    if venda_existente:
        return _resposta_venda(atendimento.id, venda_existente, ja_existia=True)

    itens = _montar_itens_venda(db, tenant_id, atendimento)
    if not itens:
        raise HTTPException(status_code=422, detail="Atendimento nao possui valor ou servicos para gerar venda")

    payload = {
        "cliente_id": atendimento.cliente_id,
        "vendedor_id": user_id,
        "itens": itens,
        "desconto_valor": 0,
        "desconto_percentual": 0,
        "observacoes": _montar_observacao(atendimento),
        "tem_entrega": False,
        "taxa_entrega": 0,
        "canal": "banho_tosa",
        "tenant_id": tenant_id,
    }
    venda_dict = VendaService.criar_venda(payload=payload, user_id=user_id, db=db)

    atendimento = db.query(BanhoTosaAtendimento).filter(
        BanhoTosaAtendimento.id == atendimento_id,
        BanhoTosaAtendimento.tenant_id == tenant_id,
    ).first()
    atendimento.venda_id = venda_dict["id"]
    db.commit()

    venda = db.query(Venda).filter(Venda.id == venda_dict["id"], Venda.tenant_id == tenant_id).first()
    return _resposta_venda(atendimento.id, venda, ja_existia=False)


def _obter_atendimento(db: Session, tenant_id, atendimento_id: int):
    return (
        db.query(BanhoTosaAtendimento)
        .options(
            joinedload(BanhoTosaAtendimento.agendamento).joinedload(BanhoTosaAgendamento.servicos),
            joinedload(BanhoTosaAtendimento.venda),
        )
        .filter(BanhoTosaAtendimento.id == atendimento_id, BanhoTosaAtendimento.tenant_id == tenant_id)
        .first()
    )


def _obter_venda_existente(db: Session, tenant_id, atendimento):
    if atendimento.venda_id and atendimento.venda:
        return atendimento.venda
    token = f"BT_ATENDIMENTO:{atendimento.id}"
    venda = db.query(Venda).filter(
        Venda.tenant_id == tenant_id,
        Venda.observacoes.contains(token),
        Venda.status != "cancelada",
    ).first()
    if venda and not atendimento.venda_id:
        atendimento.venda_id = venda.id
        db.commit()
    return venda


def _montar_itens_venda(db: Session, tenant_id, atendimento) -> list[dict]:
    itens = []
    agendamento = atendimento.agendamento
    if agendamento:
        for servico in agendamento.servicos or []:
            subtotal = _subtotal(servico.quantidade, servico.valor_unitario, servico.desconto)
            if subtotal <= 0:
                continue
            itens.append(_item_servico(servico.nome_servico_snapshot, servico.quantidade, servico.valor_unitario, servico.desconto, subtotal, atendimento.pet_id))
        itens.extend(_itens_taxi_dog(db, tenant_id, agendamento, atendimento.pet_id))

    if not itens:
        valor = Decimal(str(getattr(agendamento, "valor_previsto", 0) if agendamento else 0))
        if valor > 0:
            itens.append(_item_servico(f"Banho & Tosa - Atendimento #{atendimento.id}", 1, valor, 0, valor, atendimento.pet_id))
    return itens


def _itens_taxi_dog(db: Session, tenant_id, agendamento, pet_id: int) -> list[dict]:
    if not agendamento.taxi_dog_id:
        return []
    taxi = db.query(BanhoTosaTaxiDog).filter(
        BanhoTosaTaxiDog.id == agendamento.taxi_dog_id,
        BanhoTosaTaxiDog.tenant_id == tenant_id,
    ).first()
    valor = Decimal(str(taxi.valor_cobrado if taxi else 0))
    if valor <= 0:
        return []
    return [_item_servico("Taxi dog Banho & Tosa", 1, valor, 0, valor, pet_id)]


def _item_servico(nome, quantidade, valor_unitario, desconto, subtotal, pet_id: int) -> dict:
    return {
        "tipo": "servico",
        "servico_descricao": str(nome),
        "quantidade": float(quantidade or 1),
        "preco_unitario": float(valor_unitario or 0),
        "desconto_item": float(desconto or 0),
        "subtotal": float(subtotal),
        "pet_id": pet_id,
    }


def _subtotal(quantidade, valor_unitario, desconto) -> Decimal:
    return max((Decimal(str(quantidade or 0)) * Decimal(str(valor_unitario or 0))) - Decimal(str(desconto or 0)), Decimal("0"))


def _montar_observacao(atendimento) -> str:
    pet_nome = atendimento.pet.nome if atendimento.pet else f"Pet #{atendimento.pet_id}"
    return f"Banho & Tosa - atendimento #{atendimento.id} / {pet_nome} | BT_ATENDIMENTO:{atendimento.id}"


def _resposta_venda(atendimento_id: int, venda: Venda, ja_existia: bool) -> dict:
    return {
        "atendimento_id": atendimento_id,
        "venda_id": venda.id,
        "numero_venda": venda.numero_venda,
        "status_venda": venda.status,
        "total": venda.total,
        "pdv_url": f"/pdv?venda_id={venda.id}",
        "ja_existia": ja_existia,
        "mensagem": "Venda ja estava vinculada ao atendimento." if ja_existia else "Venda gerada para cobranca no PDV.",
    }
