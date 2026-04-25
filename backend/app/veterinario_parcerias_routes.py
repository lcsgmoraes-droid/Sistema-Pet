"""Rotas de parcerias veterinarias e repasses."""
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .auth.dependencies import get_current_user_and_tenant
from .db import get_session
from .financeiro_models import ContaReceber
from .models import Tenant
from .veterinario_core import _get_tenant
from .veterinario_financeiro import _round_money
from .veterinario_models import VetPartnerLink
from .veterinario_schemas import PartnerLinkCreate, PartnerLinkResponse, PartnerLinkUpdate

router = APIRouter()


@router.get("/parceiros", response_model=List[PartnerLinkResponse], summary="Lista parcerias do tenant atual")
def listar_parceiros(
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    """Retorna todos os vínculos de parceria em que o tenant atual é a empresa (loja)."""
    user, tenant_id = _get_tenant(current)
    links = db.query(VetPartnerLink).filter(
        VetPartnerLink.empresa_tenant_id == str(tenant_id),
    ).all()

    result = []
    for link in links:
        vet_tenant = db.query(Tenant).filter(Tenant.id == str(link.vet_tenant_id)).first()
        result.append(
            PartnerLinkResponse(
                id=link.id,
                empresa_tenant_id=str(link.empresa_tenant_id),
                vet_tenant_id=str(link.vet_tenant_id),
                tipo_relacao=link.tipo_relacao,
                comissao_empresa_pct=float(link.comissao_empresa_pct) if link.comissao_empresa_pct else None,
                ativo=link.ativo,
                criado_em=link.criado_em,
                vet_tenant_nome=vet_tenant.name if vet_tenant else None,
            )
        )
    return result


@router.post("/parceiros", response_model=PartnerLinkResponse, status_code=201, summary="Cria vínculo com veterinário parceiro")
def criar_parceiro(
    payload: PartnerLinkCreate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    """Cria um vínculo de parceria entre o tenant atual (loja) e um tenant veterinário."""
    user, tenant_id = _get_tenant(current)

    # Verifica se o tenant de destino existe
    vet_tenant = db.query(Tenant).filter(Tenant.id == payload.vet_tenant_id).first()
    if not vet_tenant:
        raise HTTPException(status_code=404, detail="Tenant do veterinário não encontrado.")

    # Impede vínculo consigo mesmo
    if str(payload.vet_tenant_id) == str(tenant_id):
        raise HTTPException(status_code=400, detail="O tenant parceiro não pode ser o mesmo tenant atual.")

    # Impede duplicata
    existente = db.query(VetPartnerLink).filter(
        VetPartnerLink.empresa_tenant_id == str(tenant_id),
        VetPartnerLink.vet_tenant_id == payload.vet_tenant_id,
    ).first()
    if existente:
        raise HTTPException(status_code=409, detail="Já existe um vínculo com este veterinário parceiro.")

    link = VetPartnerLink(
        empresa_tenant_id=str(tenant_id),
        vet_tenant_id=payload.vet_tenant_id,
        tipo_relacao=payload.tipo_relacao,
        comissao_empresa_pct=payload.comissao_empresa_pct,
        ativo=True,
    )
    db.add(link)
    db.commit()
    db.refresh(link)

    return PartnerLinkResponse(
        id=link.id,
        empresa_tenant_id=str(link.empresa_tenant_id),
        vet_tenant_id=str(link.vet_tenant_id),
        tipo_relacao=link.tipo_relacao,
        comissao_empresa_pct=float(link.comissao_empresa_pct) if link.comissao_empresa_pct else None,
        ativo=link.ativo,
        criado_em=link.criado_em,
        vet_tenant_nome=vet_tenant.name,
    )


@router.patch("/parceiros/{link_id}", response_model=PartnerLinkResponse, summary="Atualiza vínculo de parceria")
def atualizar_parceiro(
    link_id: int,
    payload: PartnerLinkUpdate,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    link = db.query(VetPartnerLink).filter(
        VetPartnerLink.id == link_id,
        VetPartnerLink.empresa_tenant_id == str(tenant_id),
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="Vínculo de parceria não encontrado.")

    if payload.tipo_relacao is not None:
        link.tipo_relacao = payload.tipo_relacao
    if payload.comissao_empresa_pct is not None:
        link.comissao_empresa_pct = payload.comissao_empresa_pct
    if payload.ativo is not None:
        link.ativo = payload.ativo

    db.commit()
    db.refresh(link)

    vet_tenant = db.query(Tenant).filter(Tenant.id == str(link.vet_tenant_id)).first()
    return PartnerLinkResponse(
        id=link.id,
        empresa_tenant_id=str(link.empresa_tenant_id),
        vet_tenant_id=str(link.vet_tenant_id),
        tipo_relacao=link.tipo_relacao,
        comissao_empresa_pct=float(link.comissao_empresa_pct) if link.comissao_empresa_pct else None,
        ativo=link.ativo,
        criado_em=link.criado_em,
        vet_tenant_nome=vet_tenant.name if vet_tenant else None,
    )


@router.delete("/parceiros/{link_id}", status_code=204, summary="Remove vínculo de parceria")
def remover_parceiro(
    link_id: int,
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    user, tenant_id = _get_tenant(current)
    link = db.query(VetPartnerLink).filter(
        VetPartnerLink.id == link_id,
        VetPartnerLink.empresa_tenant_id == str(tenant_id),
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="Vínculo de parceria não encontrado.")
    db.delete(link)
    db.commit()


@router.get("/tenants-veterinarios", summary="Lista tenants com tipo veterinary_clinic")
def listar_tenants_veterinarios(
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    """Lista tenants que podem ser vinculados como parceiros (veterinary_clinic)."""
    _get_tenant(current)
    tenants = db.query(Tenant).filter(
        Tenant.organization_type == "veterinary_clinic",
        Tenant.status == "active",
    ).all()
    return [{"id": str(t.id), "nome": t.name, "cnpj": t.cnpj} for t in tenants]


@router.get("/relatorios/repasse", summary="Relatório de repasse veterinário por período")
def relatorio_repasse(
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    """
    Lista todas as contas a receber geradas por procedimentos veterinários
    (documento começando com VET-PROC-), filtrando por período e status.
    Útil para fechar o repasse com o veterinário parceiro.
    """
    user, tenant_id = _get_tenant(current)

    query = db.query(ContaReceber).filter(
        ContaReceber.tenant_id == str(tenant_id),
        ContaReceber.documento.like("VET-PROC-%"),
    )

    if data_inicio:
        query = query.filter(ContaReceber.data_emissao >= data_inicio)
    if data_fim:
        query = query.filter(ContaReceber.data_emissao <= data_fim)
    if status:
        query = query.filter(ContaReceber.status == status)

    contas = query.order_by(ContaReceber.data_emissao.desc()).all()

    items = []
    total_valor = 0.0
    total_recebido = 0.0
    total_pendente = 0.0

    for c in contas:
        tipo = "repasse_empresa" if "-REPASSE-EMPRESA" in (c.documento or "") else "liquido_vet"
        valor = float(c.valor_final or 0)
        recebido = float(c.valor_recebido or 0)
        pendente = valor - recebido if c.status != "recebido" else 0.0

        total_valor += valor
        total_recebido += recebido if c.status == "recebido" else 0.0
        total_pendente += pendente

        items.append({
            "id": c.id,
            "documento": c.documento,
            "descricao": c.descricao,
            "tipo": tipo,
            "valor": valor,
            "valor_recebido": recebido,
            "data_emissao": c.data_emissao.isoformat() if c.data_emissao else None,
            "data_vencimento": c.data_vencimento.isoformat() if c.data_vencimento else None,
            "data_recebimento": c.data_recebimento.isoformat() if c.data_recebimento else None,
            "status": c.status,
            "observacoes": c.observacoes,
        })

    return {
        "items": items,
        "total_valor": _round_money(total_valor),
        "total_recebido": _round_money(total_recebido),
        "total_pendente": _round_money(total_pendente),
        "quantidade": len(items),
    }


@router.post("/relatorios/repasse/{conta_id}/baixar", summary="Dá baixa (recebimento) em um lançamento de repasse")
def baixar_repasse(
    conta_id: int,
    data_recebimento: Optional[date] = Query(None),
    db: Session = Depends(get_session),
    current=Depends(get_current_user_and_tenant),
):
    """
    Marca um lançamento de repasse veterinário como recebido.
    Atualiza status='recebido', valor_recebido=valor_final e data_recebimento.
    """
    user, tenant_id = _get_tenant(current)

    conta = db.query(ContaReceber).filter(
        ContaReceber.id == conta_id,
        ContaReceber.tenant_id == str(tenant_id),
        ContaReceber.documento.like("VET-PROC-%"),
    ).first()

    if not conta:
        raise HTTPException(404, "Lançamento de repasse não encontrado.")
    if conta.status == "recebido":
        raise HTTPException(400, "Este lançamento já foi baixado.")

    conta.status = "recebido"
    conta.valor_recebido = conta.valor_final
    conta.data_recebimento = data_recebimento or date.today()
    db.commit()

    return {
        "ok": True,
        "id": conta.id,
        "status": conta.status,
        "data_recebimento": conta.data_recebimento.isoformat(),
        "valor_recebido": float(conta.valor_recebido),
    }
