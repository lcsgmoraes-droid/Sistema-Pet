"""Rotas do piloto de orcamentos emitidos por empresas do grupo."""

from io import BytesIO
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.audit_log import log_action
from app.auth.dependencies import get_current_user_and_tenant
from app.constants.feature_flags import ORCAMENTOS_GRUPO
from app.db import get_session
from app.models import Cliente
from app.orcamentos_grupo_models import (
    OrcamentoGrupo,
    OrcamentoGrupoEmpresa,
)
from app.orcamentos_grupo_pdf import gerar_pdf_orcamentos
from app.orcamentos_grupo_schemas import (
    OrcamentoGrupoConfiguracaoUpdate,
    OrcamentoGrupoCreate,
    OrcamentoGrupoEmpresaCreate,
    OrcamentoGrupoEmpresaUpdate,
)
from app.orcamentos_grupo_service import (
    criar_orcamento,
    obter_orcamento,
    obter_ou_criar_configuracao,
    serializar_configuracao,
    serializar_empresa,
    serializar_orcamento,
)
from app.security.permissions_decorator import require_permission
from app.services.feature_flag_service import is_feature_enabled


router = APIRouter(prefix="/orcamentos-grupo", tags=["Orcamentos do Grupo"])


def _feature_ativa(db: Session, tenant_id) -> bool:
    return is_feature_enabled(db, UUID(str(tenant_id)), ORCAMENTOS_GRUPO)


def _garantir_feature(db: Session, tenant_id) -> None:
    if not _feature_ativa(db, tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Orcamentos do grupo nao estao habilitados para esta empresa",
        )


@router.get("/status")
def status_orcamentos_grupo(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _current_user, tenant_id = user_and_tenant
    return {"enabled": _feature_ativa(db, tenant_id)}


@router.get("/configuracao")
@require_permission("vendas.criar")
def buscar_configuracao(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _current_user, tenant_id = user_and_tenant
    _garantir_feature(db, tenant_id)
    configuracao = obter_ou_criar_configuracao(db, tenant_id)
    db.commit()
    return serializar_configuracao(configuracao)


@router.put("/configuracao")
@require_permission("configuracoes.editar")
def atualizar_configuracao(
    payload: OrcamentoGrupoConfiguracaoUpdate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = user_and_tenant
    _garantir_feature(db, tenant_id)
    configuracao = obter_ou_criar_configuracao(db, tenant_id)
    anterior = serializar_configuracao(configuracao)
    for campo, valor in payload.model_dump().items():
        setattr(configuracao, campo, valor)
    db.commit()
    db.refresh(configuracao)
    atual = serializar_configuracao(configuracao)
    log_action(
        db,
        current_user.id,
        action="update_orcamento_grupo_configuracao",
        entity_type="orcamento_grupo_configuracao",
        entity_id=configuracao.id,
        old_value=anterior,
        new_value=atual,
        tenant_id=tenant_id,
    )
    return atual


@router.get("/pessoas")
@require_permission("clientes.visualizar")
def buscar_pessoas(
    search: str = Query(..., min_length=2, max_length=120),
    limit: int = Query(15, ge=1, le=30),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _current_user, tenant_id = user_and_tenant
    _garantir_feature(db, tenant_id)
    termo = f"%{search.strip()}%"
    pessoas = (
        db.query(Cliente)
        .filter(
            Cliente.tenant_id == tenant_id,
            Cliente.ativo.is_not(False),
            or_(
                Cliente.nome.ilike(termo),
                Cliente.nome_fantasia.ilike(termo),
                Cliente.razao_social.ilike(termo),
                Cliente.cnpj.ilike(termo),
            ),
        )
        .order_by(Cliente.nome.asc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": pessoa.id,
            "nome": pessoa.nome_fantasia or pessoa.nome,
            "razao_social": pessoa.razao_social,
            "cnpj": pessoa.cnpj,
            "tipo_pessoa": pessoa.tipo_pessoa,
            "telefone": pessoa.telefone or pessoa.celular,
            "email": pessoa.email,
        }
        for pessoa in pessoas
    ]


@router.get("/empresas")
@require_permission("vendas.criar")
def listar_empresas(
    incluir_inativas: bool = False,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _current_user, tenant_id = user_and_tenant
    _garantir_feature(db, tenant_id)
    query = (
        db.query(OrcamentoGrupoEmpresa)
        .options(joinedload(OrcamentoGrupoEmpresa.cliente))
        .filter(OrcamentoGrupoEmpresa.tenant_id == tenant_id)
    )
    if not incluir_inativas:
        query = query.filter(OrcamentoGrupoEmpresa.ativo.is_(True))
    empresas = query.order_by(
        OrcamentoGrupoEmpresa.fixada_padrao.desc(), OrcamentoGrupoEmpresa.id.asc()
    ).all()
    return [serializar_empresa(empresa) for empresa in empresas]


@router.post("/empresas", status_code=status.HTTP_201_CREATED)
@require_permission("configuracoes.editar")
def adicionar_empresa(
    payload: OrcamentoGrupoEmpresaCreate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = user_and_tenant
    _garantir_feature(db, tenant_id)
    cliente = (
        db.query(Cliente)
        .filter(Cliente.id == payload.cliente_id, Cliente.tenant_id == tenant_id)
        .first()
    )
    if not cliente:
        raise HTTPException(status_code=404, detail="Pessoa nao encontrada")

    empresa = (
        db.query(OrcamentoGrupoEmpresa)
        .filter(
            OrcamentoGrupoEmpresa.tenant_id == tenant_id,
            OrcamentoGrupoEmpresa.cliente_id == cliente.id,
        )
        .first()
    )
    if empresa:
        empresa.ativo = True
        empresa.fixada_padrao = payload.fixada_padrao
        empresa.observacoes = payload.observacoes
    else:
        empresa = OrcamentoGrupoEmpresa(
            tenant_id=tenant_id,
            cliente_id=cliente.id,
            ativo=True,
            fixada_padrao=payload.fixada_padrao,
            observacoes=payload.observacoes,
        )
        db.add(empresa)
    db.commit()
    empresa = (
        db.query(OrcamentoGrupoEmpresa)
        .options(joinedload(OrcamentoGrupoEmpresa.cliente))
        .filter(OrcamentoGrupoEmpresa.id == empresa.id)
        .first()
    )
    log_action(
        db,
        current_user.id,
        action="save_orcamento_grupo_empresa",
        entity_type="orcamento_grupo_empresa",
        entity_id=empresa.id,
        new_value={"cliente_id": cliente.id, "nome": cliente.nome},
        tenant_id=tenant_id,
    )
    return serializar_empresa(empresa)


@router.patch("/empresas/{empresa_id}")
@require_permission("configuracoes.editar")
def atualizar_empresa(
    empresa_id: int,
    payload: OrcamentoGrupoEmpresaUpdate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _current_user, tenant_id = user_and_tenant
    _garantir_feature(db, tenant_id)
    empresa = (
        db.query(OrcamentoGrupoEmpresa)
        .options(joinedload(OrcamentoGrupoEmpresa.cliente))
        .filter(
            OrcamentoGrupoEmpresa.id == empresa_id,
            OrcamentoGrupoEmpresa.tenant_id == tenant_id,
        )
        .first()
    )
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa do grupo nao encontrada")
    for campo, valor in payload.model_dump(exclude_unset=True).items():
        setattr(empresa, campo, valor)
    db.commit()
    db.refresh(empresa)
    return serializar_empresa(empresa)


@router.delete("/empresas/{empresa_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_permission("configuracoes.editar")
def remover_empresa(
    empresa_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _current_user, tenant_id = user_and_tenant
    _garantir_feature(db, tenant_id)
    empresa = (
        db.query(OrcamentoGrupoEmpresa)
        .filter(
            OrcamentoGrupoEmpresa.id == empresa_id,
            OrcamentoGrupoEmpresa.tenant_id == tenant_id,
        )
        .first()
    )
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa do grupo nao encontrada")
    db.delete(empresa)
    db.commit()


@router.get("")
@require_permission("vendas.criar")
def listar_orcamentos(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _current_user, tenant_id = user_and_tenant
    _garantir_feature(db, tenant_id)
    orcamentos = (
        db.query(OrcamentoGrupo)
        .options(joinedload(OrcamentoGrupo.cotacoes))
        .filter(OrcamentoGrupo.tenant_id == tenant_id)
        .order_by(OrcamentoGrupo.id.desc())
        .limit(limit)
        .all()
    )
    return [serializar_orcamento(item, resumido=True) for item in orcamentos]


@router.post("", status_code=status.HTTP_201_CREATED)
@require_permission("vendas.criar")
def emitir_orcamentos(
    payload: OrcamentoGrupoCreate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = user_and_tenant
    _garantir_feature(db, tenant_id)
    orcamento = criar_orcamento(
        db,
        tenant_id=tenant_id,
        user_id=current_user.id,
        payload=payload,
    )
    log_action(
        db,
        current_user.id,
        action="create_orcamentos_grupo",
        entity_type="orcamento_grupo",
        entity_id=orcamento.id,
        new_value={
            "numero": orcamento.numero,
            "total_base": str(orcamento.total_base),
            "quantidade_cotacoes": len(orcamento.cotacoes or []),
        },
        tenant_id=tenant_id,
    )
    return serializar_orcamento(orcamento)


@router.get("/{orcamento_id}")
@require_permission("vendas.criar")
def detalhar_orcamento(
    orcamento_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _current_user, tenant_id = user_and_tenant
    _garantir_feature(db, tenant_id)
    return serializar_orcamento(obter_orcamento(db, tenant_id, orcamento_id))


@router.get("/{orcamento_id}/pdf")
@require_permission("vendas.criar")
def baixar_pdf_orcamento(
    orcamento_id: int,
    cotacao_id: int | None = Query(None),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    _current_user, tenant_id = user_and_tenant
    _garantir_feature(db, tenant_id)
    orcamento = obter_orcamento(db, tenant_id, orcamento_id)
    cotacoes = list(orcamento.cotacoes or [])
    if cotacao_id is not None:
        cotacoes = [item for item in cotacoes if item.id == cotacao_id]
        if not cotacoes:
            raise HTTPException(status_code=404, detail="Cotacao nao encontrada")
    conteudo = gerar_pdf_orcamentos(orcamento, cotacoes)
    sufixo = f"-cotacao-{cotacao_id}" if cotacao_id else "-todos"
    nome = f"{orcamento.numero or orcamento.id}{sufixo}.pdf"
    return StreamingResponse(
        BytesIO(conteudo),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )
