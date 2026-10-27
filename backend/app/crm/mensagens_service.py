"""Liga as conversas de WhatsApp ao card da pessoa no CRM.

- cada mensagem enviada ou recebida entra na linha do tempo do card e atualiza o
  "ultimo contato";
- o livro-razao (custos) guarda o card de cada mensagem, para ver o gasto por pessoa;
- quando uma pessoa e cadastrada (ou muda o telefone), o card sem cadastro com o
  mesmo numero passa a ser dela, sem chute: so se o numero tiver um unico dono;
- quando o CRM e ativado numa loja, as conversas que ja existiam ganham card.

Nada aqui pode atrapalhar o atendimento: as funcoes `anotar_*` e `*_no_crm` so logam erro.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.crm.models import CrmInteracao, CrmLead
from app.whatsapp.customer_lookup import (
    SITUACAO_UNICO,
    resolver_tutor_por_telefone,
    somente_digitos,
    telefones_compativeis,
)

logger = logging.getLogger(__name__)

TAMANHO_DO_RESUMO = 120
LIMITE_DE_CONVERSAS_POR_RODADA = 2000


def _agora() -> datetime:
    return datetime.now(UTC)


def lead_da_sessao(db: Session, tenant_id: Any, session: Any) -> CrmLead | None:
    """Card da pessoa dona da conversa (pelo cadastro e, se faltar, pelo telefone)."""
    principal = db.query(CrmLead).filter(
        CrmLead.tenant_id == tenant_id, CrmLead.separado_de_lead_id.is_(None)
    )
    cliente_id = getattr(session, "cliente_id", None)
    if cliente_id:
        lead = principal.filter(CrmLead.cliente_id == cliente_id).first()
        if lead is not None:
            return lead
    digitos = somente_digitos(getattr(session, "phone_number", None))
    if not digitos:
        return None
    return principal.filter(CrmLead.telefone == digitos).first()


def lead_id_da_sessao(db: Session, tenant_id: Any, session: Any) -> int | None:
    try:
        lead = lead_da_sessao(db, tenant_id, session)
        return lead.id if lead is not None else None
    except Exception as erro:
        logger.warning("CRM: card da conversa nao encontrado (%s)", type(erro).__name__)
        return None


def _resumo(texto: str | None) -> str:
    limpo = " ".join(str(texto or "").split())
    return limpo[:TAMANHO_DO_RESUMO] + ("…" if len(limpo) > TAMANHO_DO_RESUMO else "")


def anotar_mensagem_no_crm(
    db: Session,
    *,
    tenant_id: Any,
    session: Any,
    direcao: str,
    texto: str | None,
    origem: str,
) -> bool:
    """Registra a mensagem na linha do tempo do card e atualiza o ultimo contato."""
    try:
        lead = lead_da_sessao(db, tenant_id, session)
        if lead is None:
            return False
        recebida = direcao == "recebida"
        with db.begin_nested():
            db.add(
                CrmInteracao(
                    tenant_id=tenant_id,
                    lead_id=lead.id,
                    cliente_id=lead.cliente_id,
                    tipo="mensagem_recebida" if recebida else "mensagem_enviada",
                    resumo=_resumo(texto) or "(sem texto)",
                    origem="tutor" if recebida else origem,
                    ocorrida_em=_agora(),
                )
            )
            lead.ultimo_contato_em = _agora()
        db.commit()
        return True
    except Exception as erro:
        logger.warning("CRM: mensagem nao registrada no card (%s)", type(erro).__name__)
        try:
            db.rollback()
        except Exception:
            logger.debug("CRM: rollback falhou", exc_info=True)
        return False


def consumo_do_lead(db: Session, tenant_id: Any, lead_id: int) -> dict[str, Any]:
    """Quanto as mensagens desta pessoa custaram (estimado, com as tarifas da Meta)."""
    from app.whatsapp.ledger_models import WhatsAppLedger

    enviadas, recebidas, cobraveis, custo = (
        db.query(
            func.count(WhatsAppLedger.id).filter(WhatsAppLedger.direcao == "enviada"),
            func.count(WhatsAppLedger.id).filter(WhatsAppLedger.direcao == "recebida"),
            func.count(WhatsAppLedger.id).filter(WhatsAppLedger.cobravel.is_(True)),
            func.coalesce(func.sum(WhatsAppLedger.custo_estimado), 0),
        )
        .filter(
            WhatsAppLedger.tenant_id == tenant_id, WhatsAppLedger.lead_id == lead_id
        )
        .one()
    )
    return {
        "enviadas": int(enviadas or 0),
        "recebidas": int(recebidas or 0),
        "cobraveis": int(cobraveis or 0),
        "custo_estimado": float(custo or 0),
    }


def vincular_leads_ao_cliente(db: Session, tenant_id: Any, cliente: Any) -> int:
    """Liga ao cadastro os cards sem cadastro cujo numero agora tem esta pessoa como unica dona."""
    telefones = [t for t in (cliente.celular, cliente.telefone) if t]
    if not telefones:
        return 0
    ja_tem_card = (
        db.query(CrmLead.id)
        .filter(
            CrmLead.tenant_id == tenant_id,
            CrmLead.cliente_id == cliente.id,
            CrmLead.separado_de_lead_id.is_(None),
        )
        .first()
    )
    if ja_tem_card is not None:
        return 0
    candidatos = (
        db.query(CrmLead)
        .filter(
            CrmLead.tenant_id == tenant_id,
            CrmLead.cliente_id.is_(None),
            CrmLead.separado_de_lead_id.is_(None),
            CrmLead.telefone.isnot(None),
        )
        .all()
    )
    for lead in candidatos:
        if not any(telefones_compativeis(lead.telefone, t) for t in telefones):
            continue
        # Mesma regra do atendimento: so liga se o numero tiver UM unico dono.
        resolucao = resolver_tutor_por_telefone(db, tenant_id, lead.telefone)
        if resolucao.situacao != SITUACAO_UNICO or resolucao.cliente_id != cliente.id:
            continue
        lead.cliente_id = cliente.id
        lead.nome_exibicao = cliente.nome
        db.add(
            CrmInteracao(
                tenant_id=tenant_id,
                lead_id=lead.id,
                cliente_id=cliente.id,
                tipo="vinculo",
                resumo=f"Card ligado ao cadastro de {cliente.nome} (mesmo telefone)",
                origem="sistema",
            )
        )
        db.flush()
        return 1  # um card por pessoa
    return 0


def vincular_leads_ao_cliente_com_seguranca(
    db: Session, tenant_id: Any, cliente: Any
) -> int:
    """Versao para rotas de cadastro: salva o vinculo e nunca devolve erro ao usuario."""
    try:
        with db.begin_nested():
            ligados = vincular_leads_ao_cliente(db, tenant_id, cliente)
        if ligados:
            db.commit()
        return ligados
    except Exception as erro:
        logger.warning("CRM: vinculo automatico falhou (%s)", type(erro).__name__)
        try:
            db.rollback()
        except Exception:
            logger.debug("CRM: rollback falhou", exc_info=True)
        return 0


def criar_cards_das_conversas(
    db: Session, tenant_id: Any, limite: int = LIMITE_DE_CONVERSAS_POR_RODADA
) -> dict[str, int]:
    """Cria o card das conversas que ja existiam antes de o CRM ser ativado.

    Seguro para repetir: quem ja tem card e pulado. `ha_mais` pede nova rodada.
    """
    from app.crm.leads_service import identificar_ou_criar_lead
    from app.whatsapp.models import WhatsAppSession

    sessoes = (
        db.query(WhatsAppSession)
        .filter(WhatsAppSession.tenant_id == tenant_id)
        .order_by(WhatsAppSession.last_message_at.desc())
        .all()
    )
    criados = existentes = invalidos = 0
    ha_mais = False
    vistos: set[str] = set()
    processados = 0
    for sessao in sessoes:
        digitos = somente_digitos(sessao.phone_number)
        if not digitos or digitos in vistos:
            continue
        vistos.add(digitos)
        if lead_da_sessao(db, tenant_id, sessao) is not None:
            existentes += 1
            continue
        if processados >= limite:
            ha_mais = True
            break
        processados += 1
        lead = identificar_ou_criar_lead(
            db, tenant_id, sessao.phone_number, origem="whatsapp"
        )
        if lead is None:
            invalidos += 1
            continue
        lead.ultimo_contato_em = sessao.last_message_at or lead.ultimo_contato_em
        criados += 1
    db.flush()
    return {
        "criados": criados,
        "ja_existiam": existentes,
        "invalidos": invalidos,
        "ha_mais": ha_mais,
    }
