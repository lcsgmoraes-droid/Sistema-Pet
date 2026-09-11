"""API do registro rápido e relatório de atendimentos sem venda."""

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload, selectinload

from app.auth import get_current_user_and_tenant
from app.db import get_session
from app.evolucao_corepet import registrar_uso_funcionalidade
from app.models import EcommerceNotifyRequest, Tenant
from app.nao_venda_models import NaoVenda
from app.nao_venda_schemas import NaoVendaCreate
from app.pendencia_estoque_models import PendenciaEstoque
from app.produtos_models import Produto
from app.services.demanda_nao_atendida import montar_central_demanda_nao_atendida
from app.services.nao_venda_relatorio import montar_relatorio_nao_vendas
from app.services.nao_venda_service import registrar_nao_venda
from app.services.pendencia_estoque_service import STATUS_ATIVOS_LISTA_ESPERA

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


@router.get("/central-demanda", response_model=dict)
def central_demanda_nao_atendida(
    data_inicio: date | None = Query(default=None),
    data_fim: date | None = Query(default=None),
    busca: str | None = Query(default=None, max_length=120),
    origem: str = Query(default="todos", pattern="^(todos|pdv|ecommerce)$"),
    situacao: str = Query(
        default="todos",
        pattern=(
            "^(todos|aguardando|nao_cadastrado|ausente_ecommerce|bloqueado|"
            "esgotado|pendencias|pronto)$"
        ),
    ),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Central unificada de procuras no PDV e pessoas aguardando reposicao."""
    _user, tenant_id = user_and_tenant
    hoje = datetime.now(FUSO_LOJA).date()
    inicio = data_inicio or (hoje - timedelta(days=29))
    fim = data_fim or hoje
    if fim < inicio:
        inicio, fim = fim, inicio
    if (fim - inicio).days > 366:
        raise HTTPException(status_code=400, detail="O período máximo é de 367 dias")

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    registros = (
        db.query(NaoVenda)
        .options(joinedload(NaoVenda.itens))
        .filter(
            NaoVenda.tenant_id == tenant_id,
            NaoVenda.created_at >= _inicio_utc(inicio),
            NaoVenda.created_at < _inicio_utc(fim + timedelta(days=1)),
        )
        .all()
    )
    pendencias = (
        db.query(PendenciaEstoque)
        .options(
            joinedload(PendenciaEstoque.produto),
            joinedload(PendenciaEstoque.cliente),
        )
        .filter(
            PendenciaEstoque.tenant_id == tenant_id,
            PendenciaEstoque.status.in_(STATUS_ATIVOS_LISTA_ESPERA),
        )
        .all()
    )
    avisos = (
        db.query(EcommerceNotifyRequest)
        .filter(
            EcommerceNotifyRequest.tenant_id == tenant_id,
            EcommerceNotifyRequest.notified.is_(False),
        )
        .all()
    )

    produto_ids = {
        int(produto_id)
        for produto_id in [
            *(item.produto_id for registro in registros for item in registro.itens),
            *(pendencia.produto_id for pendencia in pendencias),
            *(aviso.product_id for aviso in avisos),
        ]
        if produto_id is not None
    }
    produtos = []
    if produto_ids:
        produtos = (
            db.query(Produto)
            .options(
                joinedload(Produto.marca),
                joinedload(Produto.fornecedor),
                selectinload(Produto.imagens),
            )
            .filter(Produto.tenant_id == tenant_id, Produto.id.in_(produto_ids))
            .all()
        )

    central = montar_central_demanda_nao_atendida(
        registros_pdv=registros,
        pendencias_pdv=pendencias,
        avisos_ecommerce=avisos,
        produtos=produtos,
        tenant=tenant,
        busca=busca,
        origem=origem,
        situacao=situacao,
    )
    central["itens"] = central["itens"][offset : offset + limit]
    central["periodo"] = {
        "data_inicio": inicio.isoformat(),
        "data_fim": fim.isoformat(),
        "observacao": (
            "O período filtra as procuras do PDV; as listas de espera mostram "
            "todas as inscrições ainda ativas."
        ),
    }
    return central


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
