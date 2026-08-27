"""API do registro rápido e relatório de atendimentos sem venda."""

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_user_and_tenant
from app.db import get_session
from app.evolucao_corepet import registrar_uso_funcionalidade
from app.nao_venda_models import NaoVenda
from app.nao_venda_schemas import NaoVendaCreate
from app.services.nao_venda_relatorio import montar_relatorio_nao_vendas
from app.services.nao_venda_service import registrar_nao_venda

router = APIRouter(prefix="/nao-vendas", tags=["PDV - Não vendas"])
FUSO_LOJA = ZoneInfo("America/Sao_Paulo")


def _inicio_utc(valor: date) -> datetime:
    return datetime.combine(valor, time.min, tzinfo=FUSO_LOJA).astimezone(timezone.utc)


@router.post("/", response_model=dict)
def criar_registro_nao_venda(
    dados: NaoVendaCreate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Registra um atendimento sem venda, com identificação e produtos opcionais."""
    user, tenant = user_and_tenant
    registro, adicionados, ignorados = registrar_nao_venda(
        db,
        tenant_id=tenant,
        usuario_id=user.id,
        dados=dados,
    )
    registrar_uso_funcionalidade(db, "registro-rapido-nao-venda")
    return {
        "message": "Atendimento sem venda registrado com sucesso",
        "registro_id": registro.id,
        "lista_espera_adicionados": adicionados,
        "lista_espera_ignorados": ignorados,
    }


@router.get("/relatorio", response_model=dict)
def relatorio_nao_vendas(
    data_inicio: date | None = Query(default=None),
    data_fim: date | None = Query(default=None),
    motivo: str | None = Query(default=None),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Consolida perdas por motivo, produto, marca e fornecedor."""
    _user, tenant = user_and_tenant
    hoje = datetime.now(FUSO_LOJA).date()
    inicio = data_inicio or hoje.replace(day=1)
    fim = data_fim or hoje
    if fim < inicio:
        inicio, fim = fim, inicio

    query = (
        db.query(NaoVenda)
        .options(joinedload(NaoVenda.itens), joinedload(NaoVenda.usuario_registrou))
        .filter(
            NaoVenda.tenant_id == tenant,
            NaoVenda.created_at >= _inicio_utc(inicio),
            NaoVenda.created_at < _inicio_utc(fim + timedelta(days=1)),
        )
    )
    if motivo:
        query = query.filter(NaoVenda.motivo == motivo)

    registros = query.order_by(NaoVenda.created_at.desc()).all()
    relatorio = montar_relatorio_nao_vendas(registros)
    relatorio["periodo"] = {
        "data_inicio": inicio.isoformat(),
        "data_fim": fim.isoformat(),
        "motivo": motivo,
    }
    return relatorio
