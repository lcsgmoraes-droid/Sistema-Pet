"""Central de sugestoes de retorno e lembretes do Banho & Tosa."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.banho_tosa_api.pacotes_helpers import query_creditos, query_recorrencias
from app.banho_tosa_models import BanhoTosaAtendimento, BanhoTosaRecorrencia
from app.banho_tosa_pacotes import calcular_saldo_creditos
from app.models import Cliente, Pet


def listar_sugestoes_retorno(
    db: Session,
    tenant_id,
    *,
    dias: int = 30,
    sem_banho_dias: int = 45,
    pacote_vencendo_dias: int = 15,
    saldo_baixo_creditos=1,
    limit: int = 200,
) -> dict:
    hoje = date.today()
    itens = []
    itens.extend(_sugestoes_recorrencias(db, tenant_id, hoje, dias))
    itens.extend(_sugestoes_pacotes(db, tenant_id, hoje, pacote_vencendo_dias, saldo_baixo_creditos))
    itens.extend(_sugestoes_sem_banho(db, tenant_id, hoje, sem_banho_dias))
    itens = sorted(itens, key=lambda item: (_ordem_prioridade(item["prioridade"]), item.get("dias_para_acao") or 9999))
    itens = _deduplicar_sugestoes(itens)[:limit]
    return {"total": len(itens), "itens": itens}


def avancar_recorrencia(db: Session, tenant_id, recorrencia_id: int, data_base: date | None = None, observacoes: str | None = None) -> dict:
    recorrencia = query_recorrencias(db, tenant_id).filter(BanhoTosaRecorrencia.id == recorrencia_id).first()
    if not recorrencia:
        raise HTTPException(status_code=404, detail="Recorrencia nao encontrada.")
    base = data_base or date.today()
    recorrencia.proxima_execucao = base + timedelta(days=max(int(recorrencia.intervalo_dias or 1), 1))
    if observacoes is not None:
        recorrencia.observacoes = observacoes
    db.commit()
    db.refresh(recorrencia)
    return {
        "id": recorrencia.id,
        "proxima_execucao": recorrencia.proxima_execucao,
        "intervalo_dias": recorrencia.intervalo_dias,
    }


def _sugestoes_recorrencias(db: Session, tenant_id, hoje: date, dias: int) -> list[dict]:
    limite = hoje + timedelta(days=max(dias, 0))
    recorrencias = query_recorrencias(db, tenant_id).filter(
        BanhoTosaRecorrencia.ativo == True,
        BanhoTosaRecorrencia.proxima_execucao <= limite,
    ).order_by(BanhoTosaRecorrencia.proxima_execucao.asc()).limit(200).all()
    itens = []
    for item in recorrencias:
        dias_para = _dias(hoje, item.proxima_execucao)
        itens.append(_base_sugestao(
            tipo="recorrencia",
            referencia_id=item.id,
            cliente=item.cliente,
            pet=item.pet,
            data_referencia=item.proxima_execucao,
            dias_para_acao=dias_para,
            titulo=f"Retorno de {item.pet.nome if item.pet else 'pet'}",
            mensagem=f"Esta na hora de agendar o retorno de Banho & Tosa de {item.pet.nome if item.pet else 'seu pet'}.",
            acao="Contato para reagendar e manter recorrencia ativa.",
            prioridade=_prioridade_por_dias(dias_para),
            recorrencia_id=item.id,
            servico_id=item.servico_id,
            servico_nome=item.servico.nome if item.servico else None,
            canal=item.canal_lembrete or "app",
        ))
    return itens

def _sugestoes_pacotes(db: Session, tenant_id, hoje: date, vencendo_dias: int, saldo_baixo_creditos) -> list[dict]:
    limite = hoje + timedelta(days=max(vencendo_dias, 0))
    creditos = query_creditos(db, tenant_id)
    itens = []
    for credito in creditos.filter_by(status="ativo").limit(300).all():
        saldo = calcular_saldo_creditos(credito.creditos_total, credito.creditos_usados, credito.creditos_cancelados)
        vencendo = credito.data_validade <= limite
        saldo_baixo = saldo <= Decimal(str(saldo_baixo_creditos))
        if not vencendo and not saldo_baixo:
            continue
        dias_para = _dias(hoje, credito.data_validade)
        motivo = "pacote_vencendo" if vencendo else "pacote_saldo_baixo"
        itens.append(_base_sugestao(
            tipo=motivo,
            referencia_id=credito.id,
            cliente=credito.cliente,
            pet=credito.pet,
            data_referencia=credito.data_validade,
            dias_para_acao=dias_para,
            titulo=f"{credito.pacote.nome if credito.pacote else 'Pacote'} em atencao",
            mensagem=_mensagem_pacote(credito, saldo, vencendo),
            acao="Oferecer renovacao de pacote ou agendar uso dos creditos restantes.",
            prioridade="alta" if dias_para <= 7 or saldo <= 0 else "media",
            pacote_credito_id=credito.id,
            pacote_nome=credito.pacote.nome if credito.pacote else None,
            servico_id=credito.pacote.servico_id if credito.pacote else None,
            servico_nome=credito.pacote.servico.nome if credito.pacote and credito.pacote.servico else None,
        ))
    return itens

def _sugestoes_sem_banho(db: Session, tenant_id, hoje: date, sem_banho_dias: int) -> list[dict]:
    corte = datetime.combine(hoje - timedelta(days=sem_banho_dias), time.max)
    ultimos = db.query(
        BanhoTosaAtendimento.pet_id.label("pet_id"),
        func.max(BanhoTosaAtendimento.entregue_em).label("ultima_entrega"),
    ).filter(
        BanhoTosaAtendimento.tenant_id == tenant_id,
        BanhoTosaAtendimento.status == "entregue",
        BanhoTosaAtendimento.entregue_em.isnot(None),
    ).group_by(BanhoTosaAtendimento.pet_id).subquery()

    rows = db.query(Pet, Cliente, ultimos.c.ultima_entrega).join(
        ultimos, ultimos.c.pet_id == Pet.id
    ).join(Cliente, Cliente.id == Pet.cliente_id).filter(
        Pet.tenant_id == tenant_id,
        Cliente.tenant_id == tenant_id,
        ultimos.c.ultima_entrega <= corte,
    ).limit(200).all()
    itens = []
    for pet, cliente, ultima in rows:
        dias_sem = (hoje - ultima.date()).days
        itens.append(_base_sugestao(
            tipo="sem_banho",
            referencia_id=pet.id,
            cliente=cliente,
            pet=pet,
            data_referencia=ultima.date(),
            dias_para_acao=-dias_sem,
            titulo=f"{pet.nome} sem banho ha {dias_sem} dias",
            mensagem=f"{pet.nome} nao tem atendimento de Banho & Tosa registrado ha {dias_sem} dias.",
            acao="Sugerir novo agendamento ou campanha de retorno.",
            prioridade="media" if dias_sem < sem_banho_dias + 20 else "alta",
        ))
    return itens


def _base_sugestao(**kwargs) -> dict:
    cliente = kwargs["cliente"]
    pet = kwargs.get("pet")
    tipo = kwargs["tipo"]
    referencia_id = kwargs["referencia_id"]
    return {
        "id": f"{tipo}:{referencia_id}",
        "tipo": tipo,
        "prioridade": kwargs["prioridade"],
        "cliente_id": cliente.id,
        "cliente_nome": cliente.nome,
        "pet_id": pet.id if pet else None,
        "pet_nome": pet.nome if pet else None,
        "servico_id": kwargs.get("servico_id"),
        "servico_nome": kwargs.get("servico_nome"),
        "pacote_credito_id": kwargs.get("pacote_credito_id"),
        "pacote_nome": kwargs.get("pacote_nome"),
        "recorrencia_id": kwargs.get("recorrencia_id"),
        "referencia_id": referencia_id,
        "data_referencia": kwargs.get("data_referencia"),
        "dias_para_acao": kwargs.get("dias_para_acao"),
        "titulo": kwargs["titulo"],
        "mensagem": kwargs["mensagem"],
        "acao_sugerida": kwargs["acao"],
        "canal_sugerido": kwargs.get("canal") or "app",
        "notificavel_app": True,
    }


def _mensagem_pacote(credito, saldo: Decimal, vencendo: bool) -> str:
    pet = credito.pet.nome if credito.pet else "seus pets"
    if vencendo:
        return f"O pacote de {pet} vence em {credito.data_validade.strftime('%d/%m/%Y')} e tem {saldo} credito(s)."
    return f"O pacote de {pet} esta com saldo baixo: {saldo} credito(s)."


def _deduplicar_sugestoes(itens: list[dict]) -> list[dict]:
    vistos = set()
    resultado = []
    for item in itens:
        chave = (item["tipo"], item.get("cliente_id"), item.get("pet_id"), item.get("referencia_id"))
        if chave in vistos:
            continue
        vistos.add(chave)
        resultado.append(item)
    return resultado


def _prioridade_por_dias(dias_para: int) -> str:
    if dias_para < 0:
        return "critica"
    if dias_para <= 7:
        return "alta"
    if dias_para <= 15:
        return "media"
    return "baixa"


def _ordem_prioridade(prioridade: str) -> int:
    return {"critica": 0, "alta": 1, "media": 2, "baixa": 3}.get(prioridade, 9)


def _dias(hoje: date, data_ref: date) -> int:
    return (data_ref - hoje).days
