from sqlalchemy.orm import Session, joinedload

from app.banho_tosa_models import BanhoTosaAgendamento, BanhoTosaAtendimento, BanhoTosaPacoteCredito


def buscar_agendamento_completo(db: Session, tenant_id, agendamento_id: int):
    return (
        db.query(BanhoTosaAgendamento)
        .options(
            joinedload(BanhoTosaAgendamento.cliente),
            joinedload(BanhoTosaAgendamento.pet),
            joinedload(BanhoTosaAgendamento.recurso),
            joinedload(BanhoTosaAgendamento.servicos),
        )
        .filter(BanhoTosaAgendamento.id == agendamento_id, BanhoTosaAgendamento.tenant_id == tenant_id)
        .first()
    )


def buscar_atendimento_completo(db: Session, tenant_id, atendimento_id: int):
    return (
        db.query(BanhoTosaAtendimento)
        .options(
            joinedload(BanhoTosaAtendimento.cliente),
            joinedload(BanhoTosaAtendimento.pet),
            joinedload(BanhoTosaAtendimento.agendamento),
            joinedload(BanhoTosaAtendimento.pacote_credito).joinedload(BanhoTosaPacoteCredito.pacote),
        )
        .filter(BanhoTosaAtendimento.id == atendimento_id, BanhoTosaAtendimento.tenant_id == tenant_id)
        .first()
    )
