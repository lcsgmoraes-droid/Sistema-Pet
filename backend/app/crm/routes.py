"""Rotas do CRM. O modulo "crm" e exigido na montagem do router (main_routers).

Toda rota trabalha em UMA loja por vez: a atual, ou `loja_id` quando o usuario
tem acesso a outras lojas (ver app/crm/lojas.py). O quadro pode juntar varias.
"""

from datetime import datetime
from typing import Any
from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.crm import acoes_service, funil_service
from app.crm.funil_service import RegraDoCrm
from app.crm.leads_service import garantir_funil_padrao
from app.crm.lojas import (
    consultar_por_loja,
    exigir_loja,
    exigir_permissao_na_loja,
    lojas_permitidas,
    na_loja,
    resolver_lojas,
)
from app.crm.quadro_service import montar_quadro
from app.db import get_session
from app.security.permissions_decorator import require_permission_dependency

router = APIRouter(
    prefix="/crm",
    tags=["CRM"],
    dependencies=[Depends(require_permission_dependency("crm.visualizar"))],
)

PERM_LEADS = "crm.leads"
PERM_ATENDER = "crm.atender"
PERM_CONFIGURAR = "crm.configurar"


class ResultadoOportunidade(BaseModel):
    oportunidade_id: int
    estado: str
    motivo: str | None = None


class LeadNovo(BaseModel):
    loja_id: str | None = None
    nome: str | None = Field(default=None, max_length=200)
    telefone: str | None = Field(default=None, max_length=40)
    cliente_id: int | None = None
    valor_estimado: float | None = Field(default=None, ge=0)
    responsavel_user_id: int | None = None


class LeadMover(BaseModel):
    loja_id: str | None = None
    coluna_id: int
    nota: str | None = Field(default=None, max_length=1000)
    motivo_perda: str | None = Field(default=None, max_length=200)
    resultados: list[ResultadoOportunidade] = []


class AcaoNova(BaseModel):
    loja_id: str | None = None
    tipo: str
    observacao: str | None = Field(default=None, max_length=2000)


class PassoNovo(BaseModel):
    loja_id: str | None = None
    tipo: str
    agendado_para: datetime
    descricao: str | None = Field(default=None, max_length=300)
    responsavel_user_id: int | None = None


class Vinculo(BaseModel):
    loja_id: str | None = None
    cliente_id: int


class ColunaConfig(BaseModel):
    id: int | None = None
    nome: str
    tipo: str
    janela_dias: int | None = None


class FunilConfig(BaseModel):
    loja_id: str | None = None
    colunas: list[ColunaConfig]


def _executar(
    db: Session,
    user_and_tenant: Any,
    loja_id: str | None,
    permissao: str,
    acao: Callable[[Any], Any],
    *,
    gravar: bool = True,
):
    """Roda `acao(tenant_id)` na loja pedida, com permissao, tratando as regras."""
    usuario, tenant_atual = user_and_tenant
    loja = exigir_loja(db, usuario, tenant_atual, loja_id)
    with na_loja(db, loja, tenant_atual):
        exigir_permissao_na_loja(db, usuario, loja, permissao)
        try:
            resultado = acao(loja.id)
            if gravar:
                db.commit()
            return resultado
        except RegraDoCrm as erro:
            db.rollback()
            raise HTTPException(status_code=422, detail=str(erro)) from erro


@router.get("/lojas")
async def listar_lojas_do_crm(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lojas que o usuario pode ver no CRM (alimenta o filtro de lojas da tela)."""
    usuario, tenant_id = user_and_tenant
    lojas = lojas_permitidas(db, usuario, tenant_id)
    return {
        "loja_atual_id": str(tenant_id),
        "lojas": [{"id": str(loja.id), "nome": loja.nome} for loja in lojas],
    }


@router.get("/quadro")
async def quadro(
    lojas: list[str] | None = Query(default=None, description="ids das lojas"),
    busca: str | None = None,
    responsavel_id: int | None = None,
    origem: str | None = None,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Quadro de uma ou mais lojas (so as permitidas), cada uma com seu funil."""
    usuario, tenant_atual = user_and_tenant
    escolhidas = resolver_lojas(lojas_permitidas(db, usuario, tenant_atual), lojas)

    def _consulta(loja):
        dados = montar_quadro(
            db,
            loja.id,
            busca=busca,
            responsavel_id=responsavel_id,
            origem=origem,
        )
        db.commit()  # o funil padrao pode ter sido criado na primeira vez
        return [dados]

    return {"lojas": consultar_por_loja(db, escolhidas, _consulta, tenant_atual)}


@router.post("/importar-conversas")
async def importar_conversas(
    loja_id: str | None = None,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Cria o card das conversas de WhatsApp que ainda nao tem (pode repetir ate `ha_mais` ser falso)."""
    from app.crm.mensagens_service import criar_cards_das_conversas

    return _executar(
        db,
        user_and_tenant,
        loja_id,
        PERM_CONFIGURAR,
        lambda tenant_id: criar_cards_das_conversas(db, tenant_id),
    )


@router.get("/tutores")
async def buscar_tutores(
    busca: str = Query(min_length=2, max_length=100),
    loja_id: str | None = None,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Busca pessoas cadastradas da loja para criar ou vincular um card."""
    return _executar(
        db,
        user_and_tenant,
        loja_id,
        "crm.visualizar",
        lambda tenant_id: acoes_service.buscar_tutores(db, tenant_id, busca),
        gravar=False,
    )


@router.post("/leads/{lead_id}/vincular")
async def vincular_a_cadastro(
    lead_id: int,
    dados: Vinculo,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    usuario, _ = user_and_tenant

    def _vincular(tenant_id):
        lead = acoes_service.obter_lead(db, tenant_id, lead_id)
        acoes_service.vincular_a_cadastro(db, lead, dados.cliente_id, usuario.id)
        return {
            "id": lead.id,
            "cliente_id": lead.cliente_id,
            "nome": lead.nome_exibicao,
        }

    return _executar(db, user_and_tenant, dados.loja_id, PERM_LEADS, _vincular)


@router.get("/leads/{lead_id}/sugestao-vinculo")
async def sugestao_de_vinculo(
    lead_id: int,
    loja_id: str | None = None,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Pessoa cadastrada depois com o mesmo telefone do card (ou `sugestao: null`)."""
    return _executar(
        db,
        user_and_tenant,
        loja_id,
        "crm.visualizar",
        lambda tenant_id: {
            "sugestao": acoes_service.sugerir_vinculo(
                db, acoes_service.obter_lead(db, tenant_id, lead_id)
            )
        },
        gravar=False,
    )


@router.post("/leads/{lead_id}/sugestao-vinculo/ignorar")
async def ignorar_sugestao_de_vinculo(
    lead_id: int,
    dados: Vinculo,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Opção "Não perguntar novamente": a pessoa nunca mais é sugerida para este card."""
    usuario, _ = user_and_tenant

    def _ignorar(tenant_id):
        lead = acoes_service.obter_lead(db, tenant_id, lead_id)
        acoes_service.ignorar_sugestao_de_vinculo(db, lead, dados.cliente_id, usuario.id)
        return {"ok": True}

    return _executar(db, user_and_tenant, dados.loja_id, PERM_LEADS, _ignorar)


@router.post("/leads", status_code=201)
async def criar_lead(
    dados: LeadNovo,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    def _criar(tenant_id):
        lead = acoes_service.criar_lead_manual(
            db,
            tenant_id,
            nome=dados.nome,
            telefone=dados.telefone,
            cliente_id=dados.cliente_id,
            valor_estimado=dados.valor_estimado,
            responsavel_user_id=dados.responsavel_user_id,
        )
        return {"id": lead.id, "coluna_id": lead.coluna_id}

    return _executar(db, user_and_tenant, dados.loja_id, PERM_LEADS, _criar)


@router.get("/leads/{lead_id}")
async def detalhe_do_lead(
    lead_id: int,
    loja_id: str | None = None,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    def _ler(tenant_id):
        lead = acoes_service.obter_lead(db, tenant_id, lead_id)
        return acoes_service.detalhe_do_lead(db, lead)

    return _executar(db, user_and_tenant, loja_id, "crm.visualizar", _ler, gravar=False)


@router.post("/leads/{lead_id}/mover")
async def mover_lead(
    lead_id: int,
    dados: LeadMover,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    usuario, _ = user_and_tenant

    def _mover(tenant_id):
        lead = acoes_service.obter_lead(db, tenant_id, lead_id)
        funil_service.mover_lead(
            db,
            lead,
            dados.coluna_id,
            user_id=usuario.id,
            nota=dados.nota,
            motivo_perda=dados.motivo_perda,
            resultados={
                r.oportunidade_id: {"estado": r.estado, "motivo": r.motivo}
                for r in dados.resultados
            },
        )
        return {"id": lead.id, "coluna_id": lead.coluna_id, "ciclo": lead.ciclo_atual}

    return _executar(db, user_and_tenant, dados.loja_id, PERM_LEADS, _mover)


@router.post("/leads/{lead_id}/acoes", status_code=201)
async def registrar_acao(
    lead_id: int,
    dados: AcaoNova,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    usuario, _ = user_and_tenant

    def _registrar(tenant_id):
        lead = acoes_service.obter_lead(db, tenant_id, lead_id)
        acao = acoes_service.registrar_acao(
            db, lead, tipo=dados.tipo, observacao=dados.observacao, user_id=usuario.id
        )
        return {"id": acao.id}

    return _executar(db, user_and_tenant, dados.loja_id, PERM_ATENDER, _registrar)


@router.post("/leads/{lead_id}/proximo-passo", status_code=201)
async def agendar_passo(
    lead_id: int,
    dados: PassoNovo,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    def _agendar(tenant_id):
        lead = acoes_service.obter_lead(db, tenant_id, lead_id)
        passo = acoes_service.agendar_passo(
            db,
            lead,
            tipo=dados.tipo,
            agendado_para=dados.agendado_para,
            descricao=dados.descricao,
            responsavel_user_id=dados.responsavel_user_id,
        )
        return {"id": passo.id}

    return _executar(db, user_and_tenant, dados.loja_id, PERM_ATENDER, _agendar)


@router.put("/funil/colunas")
async def configurar_colunas(
    dados: FunilConfig,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    def _salvar(tenant_id):
        funil, _ = garantir_funil_padrao(db, tenant_id)
        colunas = funil_service.salvar_colunas(
            db, tenant_id, funil.id, [c.model_dump() for c in dados.colunas]
        )
        return {
            "colunas": [{"id": c.id, "nome": c.nome, "tipo": c.tipo} for c in colunas]
        }

    return _executar(db, user_and_tenant, dados.loja_id, PERM_CONFIGURAR, _salvar)
