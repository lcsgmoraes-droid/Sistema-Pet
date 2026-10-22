"""Leitura do quadro (Kanban) de UMA loja: colunas, cards, contagens e valores.

Roda sempre no contexto de uma loja; o quadro de varias lojas e montado por
`app.crm.lojas.consultar_por_loja`. O card nao mostra o numero de telefone.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.crm.funil_service import TIPOS_FINAIS, oportunidades_abertas
from app.crm.leads_service import garantir_funil_padrao
from app.crm.models import CrmColuna, CrmLead, CrmProximoPasso
from app.models import Pet, User

LIMITE_POR_COLUNA = 50
MAXIMO_DE_PETS_NO_CARD = 3


def _iso(valor: datetime | None) -> str | None:
    return valor.isoformat() if valor else None


def _dias_desde(valor: datetime | None, agora: datetime) -> int | None:
    if valor is None:
        return None
    if valor.tzinfo is None:
        valor = valor.replace(tzinfo=UTC)
    return max(0, (agora - valor).days)


def _nomes_de_pets(
    db: Session, tenant_id: Any, cliente_ids: set[int]
) -> dict[int, list[str]]:
    if not cliente_ids:
        return {}
    por_cliente: dict[int, list[str]] = {}
    linhas = (
        db.query(Pet.cliente_id, Pet.nome)
        .filter(
            Pet.tenant_id == tenant_id,
            Pet.ativo.is_(True),
            Pet.cliente_id.in_(cliente_ids),
        )
        .order_by(Pet.id)
        .all()
    )
    for cliente_id, nome in linhas:
        nomes = por_cliente.setdefault(cliente_id, [])
        if len(nomes) < MAXIMO_DE_PETS_NO_CARD:
            nomes.append(nome)
    return por_cliente


def serializar_card(
    db: Session,
    lead: CrmLead,
    *,
    agora: datetime,
    pets: list[str],
    proximo_passo: CrmProximoPasso | None,
    responsavel: str | None,
) -> dict[str, Any]:
    return {
        "id": lead.id,
        "coluna_id": lead.coluna_id,
        "nome": lead.nome_exibicao or "Sem nome",
        "sem_cadastro": lead.cliente_id is None,
        "cliente_id": lead.cliente_id,
        "pets": pets,
        "origem": lead.origem,
        "responsavel_id": lead.responsavel_user_id,
        "responsavel_nome": responsavel,
        "valor_estimado": float(lead.valor_estimado)
        if lead.valor_estimado is not None
        else None,
        "ciclo": lead.ciclo_atual,
        "dias_na_coluna": _dias_desde(lead.coluna_desde, agora),
        "ultimo_contato_em": _iso(lead.ultimo_contato_em),
        "separado": lead.separado_de_lead_id is not None,
        "oportunidades": [
            {"id": o.id, "tipo": o.tipo, "detalhe": o.detalhe, "generica": o.generica}
            for o in oportunidades_abertas(db, lead)
        ],
        "proximo_passo": (
            {
                "tipo": proximo_passo.tipo,
                "descricao": proximo_passo.descricao,
                "agendado_para": _iso(proximo_passo.agendado_para),
            }
            if proximo_passo
            else None
        ),
    }


def montar_quadro(
    db: Session,
    tenant_id: Any,
    *,
    busca: str | None = None,
    responsavel_id: int | None = None,
    origem: str | None = None,
    agora: datetime | None = None,
) -> dict[str, Any]:
    """Colunas da loja com cards (ate 50 por coluna), total e valor por coluna."""
    agora = agora or datetime.now(UTC)
    funil, _ = garantir_funil_padrao(db, tenant_id)
    colunas = (
        db.query(CrmColuna)
        .filter(
            CrmColuna.tenant_id == tenant_id,
            CrmColuna.funil_id == funil.id,
            CrmColuna.ativo.is_(True),
        )
        .order_by(CrmColuna.ordem)
        .all()
    )

    filtros = [CrmLead.tenant_id == tenant_id, CrmLead.funil_id == funil.id]
    if busca and busca.strip():
        termo = f"%{busca.strip()}%"
        filtros.append(
            or_(CrmLead.nome_exibicao.ilike(termo), CrmLead.telefone.ilike(termo))
        )
    if responsavel_id is not None:
        filtros.append(CrmLead.responsavel_user_id == responsavel_id)
    if origem:
        filtros.append(CrmLead.origem == origem)

    totais = {
        coluna_id: (quantidade, valor)
        for coluna_id, quantidade, valor in db.query(
            CrmLead.coluna_id,
            func.count(CrmLead.id),
            func.coalesce(func.sum(CrmLead.valor_estimado), 0),
        )
        .filter(*filtros)
        .group_by(CrmLead.coluna_id)
    }

    saida = []
    for coluna in colunas:
        consulta = db.query(CrmLead).filter(*filtros, CrmLead.coluna_id == coluna.id)
        if coluna.tipo in TIPOS_FINAIS and coluna.janela_dias:
            limite = agora - timedelta(days=coluna.janela_dias)
            consulta = consulta.filter(CrmLead.coluna_desde >= limite)
        leads = (
            consulta.order_by(CrmLead.coluna_desde.desc(), CrmLead.id.desc())
            .limit(LIMITE_POR_COLUNA)
            .all()
        )
        saida.append((coluna, leads))

    todos = [lead for _, leads in saida for lead in leads]
    lead_ids = [lead.id for lead in todos]
    pets = _nomes_de_pets(
        db, tenant_id, {lead.cliente_id for lead in todos if lead.cliente_id}
    )
    passos: dict[int, CrmProximoPasso] = {}
    if lead_ids:
        for passo in (
            db.query(CrmProximoPasso)
            .filter(
                CrmProximoPasso.tenant_id == tenant_id,
                CrmProximoPasso.lead_id.in_(lead_ids),
                CrmProximoPasso.concluido_em.is_(None),
            )
            .order_by(CrmProximoPasso.agendado_para.desc())
        ):
            passos[passo.lead_id] = passo  # o mais proximo ganha (ordem decrescente)
    responsaveis_ids = {
        lead.responsavel_user_id for lead in todos if lead.responsavel_user_id
    }
    nomes = (
        {
            u.id: u.nome
            for u in db.query(User.id, User.nome).filter(User.id.in_(responsaveis_ids))
        }
        if responsaveis_ids
        else {}
    )

    return {
        "funil_id": funil.id,
        "colunas": [
            {
                "id": coluna.id,
                "nome": coluna.nome,
                "tipo": coluna.tipo,
                "ordem": coluna.ordem,
                "janela_dias": coluna.janela_dias,
                "total": int(totais.get(coluna.id, (0, 0))[0]),
                "valor_total": float(totais.get(coluna.id, (0, 0))[1] or 0),
                "cards": [
                    serializar_card(
                        db,
                        lead,
                        agora=agora,
                        pets=pets.get(lead.cliente_id, []),
                        proximo_passo=passos.get(lead.id),
                        responsavel=nomes.get(lead.responsavel_user_id),
                    )
                    for lead in leads
                ],
            }
            for coluna, leads in saida
        ],
    }
