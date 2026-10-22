"""Leads do CRM (etapa 1.6): funil padrao e identificacao do tutor.

Regras (docs/crm/CONTRATOS_CONCEITUAIS.md):
- um card por tutor por loja; o tutor e identificado pelo servico unico de
  telefone (`resolver_tutor_por_telefone`), que nunca chuta;
- numero desconhecido (ou ambiguo) vira lead SEM cadastro, guardando o telefone;
  quando o numero passa a pertencer a um unico cadastro, o card e vinculado;
- numero que nao e telefone (identificador interno do WhatsApp) nao vira lead.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.crm.models import (
    COLUNA_ANDAMENTO,
    COLUNA_CONCLUIDO,
    COLUNA_ENCERRADO,
    COLUNA_ENTRADA,
    CrmColuna,
    CrmFunil,
    CrmInteracao,
    CrmLead,
    CrmMovimentacao,
)
from app.models import Cliente
from app.whatsapp.customer_lookup import (
    SITUACAO_INVALIDO,
    SITUACAO_UNICO,
    resolver_tutor_por_telefone,
    somente_digitos,
)

# Modelo inicial para pet shop. As colunas definitivas ainda estao em decisao
# (ROADMAP 2.1); a loja podera renomear, reordenar e trocar o tipo.
COLUNAS_PADRAO = (
    ("Novo", COLUNA_ENTRADA),
    ("Em contato", COLUNA_ANDAMENTO),
    ("Proposta enviada", COLUNA_ANDAMENTO),
    ("Aguardando tutor", COLUNA_ANDAMENTO),
    ("Resolvido", COLUNA_CONCLUIDO),
    ("Sem interesse", COLUNA_ENCERRADO),
)
SEM_NOME = "Sem nome no WhatsApp"


def _agora() -> datetime:
    return datetime.now(UTC)


def garantir_funil_padrao(db: Session, tenant_id: Any) -> tuple[CrmFunil, CrmColuna]:
    """Funil padrao da loja (criado na primeira necessidade) e sua coluna de entrada."""
    funil = (
        db.query(CrmFunil)
        .filter(CrmFunil.tenant_id == tenant_id, CrmFunil.padrao.is_(True))
        .first()
    )
    if funil is None:
        funil = CrmFunil(tenant_id=tenant_id, nome="Funil principal", padrao=True)
        db.add(funil)
        db.flush()
        for ordem, (nome, tipo) in enumerate(COLUNAS_PADRAO, start=1):
            db.add(
                CrmColuna(
                    tenant_id=tenant_id,
                    funil_id=funil.id,
                    nome=nome,
                    ordem=ordem,
                    tipo=tipo,
                )
            )
        db.flush()
    entrada = (
        db.query(CrmColuna)
        .filter(
            CrmColuna.tenant_id == tenant_id,
            CrmColuna.funil_id == funil.id,
            CrmColuna.tipo == COLUNA_ENTRADA,
            CrmColuna.ativo.is_(True),
        )
        .order_by(CrmColuna.ordem)
        .first()
    )
    return funil, entrada


def _lead_principal(db: Session, tenant_id: Any, **filtros) -> CrmLead | None:
    consulta = db.query(CrmLead).filter(
        CrmLead.tenant_id == tenant_id, CrmLead.separado_de_lead_id.is_(None)
    )
    for campo, valor in filtros.items():
        coluna = getattr(CrmLead, campo)
        consulta = consulta.filter(
            coluna.is_(None) if valor is None else coluna == valor
        )
    return consulta.first()


def _novo_lead(
    db: Session,
    tenant_id: Any,
    *,
    cliente_id: int | None,
    telefone: str | None,
    nome: str | None,
    origem: str,
) -> CrmLead:
    funil, entrada = garantir_funil_padrao(db, tenant_id)
    agora = _agora()
    lead = CrmLead(
        tenant_id=tenant_id,
        funil_id=funil.id,
        coluna_id=entrada.id,
        cliente_id=cliente_id,
        telefone=telefone,
        nome_exibicao=nome,
        origem=origem,
        coluna_desde=agora,
    )
    db.add(lead)
    db.flush()
    db.add(
        CrmMovimentacao(
            tenant_id=tenant_id,
            lead_id=lead.id,
            ciclo=lead.ciclo_atual,
            coluna_destino_id=entrada.id,
            nota="Card criado",
        )
    )
    db.add(
        CrmInteracao(
            tenant_id=tenant_id,
            lead_id=lead.id,
            cliente_id=cliente_id,
            tipo="lead_criado",
            resumo=f"Card criado (origem: {origem})",
            origem="sistema",
        )
    )
    return lead


def identificar_ou_criar_lead(
    db: Session,
    tenant_id: Any,
    telefone: Any,
    *,
    nome: str | None = None,
    origem: str = "whatsapp",
) -> CrmLead | None:
    """O card do tutor com esse telefone (criando se ainda nao existir)."""
    resolucao = resolver_tutor_por_telefone(db, tenant_id, telefone)
    if resolucao.situacao == SITUACAO_INVALIDO:
        return None
    digitos = somente_digitos(telefone)

    if resolucao.situacao == SITUACAO_UNICO:
        cliente_id = resolucao.cliente_id
        lead = _lead_principal(db, tenant_id, cliente_id=cliente_id)
        if lead is not None:
            return lead
        # Ja havia um card sem cadastro com esse numero: vincula ao cadastro.
        adotado = _lead_principal(db, tenant_id, cliente_id=None, telefone=digitos)
        if adotado is not None:
            adotado.cliente_id = cliente_id
            db.flush()
            return adotado
        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        return _novo_lead(
            db,
            tenant_id,
            cliente_id=cliente_id,
            telefone=digitos,
            nome=getattr(cliente, "nome", None),
            origem=origem,
        )

    lead = _lead_principal(db, tenant_id, cliente_id=None, telefone=digitos)
    if lead is not None:
        return lead
    return _novo_lead(
        db,
        tenant_id,
        cliente_id=None,
        telefone=digitos,
        nome=(nome or "").strip() or SEM_NOME,
        origem=origem,
    )
