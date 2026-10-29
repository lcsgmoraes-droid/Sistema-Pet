"""Acoes sobre o lead: criar card, registrar acao, agendar passo e detalhe.

Nao faz commit. Registrar uma acao atualiza o "ultimo contato" e pode concluir
o passo agendado (docs/crm/CONTRATOS_CONCEITUAIS.md).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.crm.funil_service import RegraDoCrm, oportunidades_abertas
from app.crm.leads_service import _lead_principal, _novo_lead
from app.crm.mensagens_service import consumo_do_lead
from app.crm.models import (
    TIPOS_DE_ACAO,
    TIPOS_DE_PASSO,
    CrmAcao,
    CrmColuna,
    CrmInteracao,
    CrmLead,
    CrmMovimentacao,
    CrmOportunidade,
    CrmProximoPasso,
    CrmVinculoIgnorado,
)
from app.models import Cliente
from app.whatsapp.customer_lookup import (
    SITUACAO_AMBIGUO,
    SITUACAO_UNICO,
    resolver_tutor_por_telefone,
    somente_digitos,
)


def _agora() -> datetime:
    return datetime.now(UTC)


def obter_lead(db: Session, tenant_id: Any, lead_id: int) -> CrmLead:
    lead = (
        db.query(CrmLead)
        .filter(CrmLead.id == lead_id, CrmLead.tenant_id == tenant_id)
        .first()
    )
    if lead is None:
        raise RegraDoCrm("Card não encontrado nesta loja.")
    return lead


def criar_lead_manual(
    db: Session,
    tenant_id: Any,
    *,
    nome: str | None = None,
    telefone: str | None = None,
    cliente_id: int | None = None,
    valor_estimado: float | None = None,
    responsavel_user_id: int | None = None,
) -> CrmLead:
    """Cria o card de um tutor cadastrado ou de um contato sem cadastro."""
    if cliente_id is not None:
        cliente = (
            db.query(Cliente)
            .filter(Cliente.id == cliente_id, Cliente.tenant_id == tenant_id)
            .first()
        )
        if cliente is None:
            raise RegraDoCrm("Pessoa não encontrada nesta loja.")
        if _lead_principal(db, tenant_id, cliente_id=cliente_id) is not None:
            raise RegraDoCrm("Esta pessoa já tem um card no funil.")
        digitos = somente_digitos(cliente.celular or cliente.telefone) or None
        nome_card = cliente.nome
    else:
        digitos = somente_digitos(telefone) or None
        nome_card = (nome or "").strip()
        if not nome_card:
            raise RegraDoCrm("Informe o nome do contato.")
        if digitos is None:
            raise RegraDoCrm("Informe o telefone do contato.")
        if _lead_principal(db, tenant_id, cliente_id=None, telefone=digitos):
            raise RegraDoCrm("Já existe um card com este telefone.")
    lead = _novo_lead(
        db,
        tenant_id,
        cliente_id=cliente_id,
        telefone=digitos,
        nome=nome_card,
        origem="manual",
    )
    lead.valor_estimado = valor_estimado
    lead.responsavel_user_id = responsavel_user_id
    db.flush()
    return lead


def registrar_acao(
    db: Session,
    lead: CrmLead,
    *,
    tipo: str,
    observacao: str | None,
    user_id: int | None,
    concluir_passo: bool = True,
) -> CrmAcao:
    if tipo not in TIPOS_DE_ACAO:
        raise RegraDoCrm("Tipo de ação inválido.")
    agora = _agora()
    acao = CrmAcao(
        tenant_id=lead.tenant_id,
        lead_id=lead.id,
        tipo=tipo,
        observacao=(observacao or "").strip() or None,
        user_id=user_id,
        ocorrida_em=agora,
    )
    db.add(acao)
    db.add(
        CrmInteracao(
            tenant_id=lead.tenant_id,
            lead_id=lead.id,
            cliente_id=lead.cliente_id,
            tipo=f"acao_{tipo}",
            resumo=acao.observacao or f"Ação registrada: {tipo}",
            origem="usuario",
            ocorrida_em=agora,
        )
    )
    if tipo != "observacao":  # anotar nao conta como contato com o tutor
        lead.ultimo_contato_em = agora
    if concluir_passo and tipo != "observacao":
        for passo in _passos_pendentes(db, lead):
            passo.concluido_em = agora
    db.flush()
    return acao


def _passos_pendentes(db: Session, lead: CrmLead) -> list[CrmProximoPasso]:
    return (
        db.query(CrmProximoPasso)
        .filter(
            CrmProximoPasso.tenant_id == lead.tenant_id,
            CrmProximoPasso.lead_id == lead.id,
            CrmProximoPasso.concluido_em.is_(None),
        )
        .all()
    )


def agendar_passo(
    db: Session,
    lead: CrmLead,
    *,
    tipo: str,
    agendado_para: datetime,
    descricao: str | None = None,
    responsavel_user_id: int | None = None,
) -> CrmProximoPasso:
    """Agenda o proximo passo; ele substitui o passo pendente anterior."""
    if tipo not in TIPOS_DE_PASSO:
        raise RegraDoCrm("Tipo de passo inválido.")
    agora = _agora()
    for anterior in _passos_pendentes(db, lead):
        anterior.concluido_em = agora
    passo = CrmProximoPasso(
        tenant_id=lead.tenant_id,
        lead_id=lead.id,
        tipo=tipo,
        descricao=(descricao or "").strip() or None,
        agendado_para=agendado_para,
        responsavel_user_id=responsavel_user_id or lead.responsavel_user_id,
    )
    db.add(passo)
    db.flush()
    return passo


def detalhe_do_lead(db: Session, lead: CrmLead, limite: int = 100) -> dict[str, Any]:
    """Ficha do card: oportunidades, caminhada de colunas e linha do tempo."""
    colunas = {
        c.id: c.nome
        for c in db.query(CrmColuna).filter(CrmColuna.tenant_id == lead.tenant_id)
    }
    movimentacoes = (
        db.query(CrmMovimentacao)
        .filter(
            CrmMovimentacao.tenant_id == lead.tenant_id,
            CrmMovimentacao.lead_id == lead.id,
        )
        .order_by(CrmMovimentacao.id)
        .all()
    )
    interacoes = (
        db.query(CrmInteracao)
        .filter(
            CrmInteracao.tenant_id == lead.tenant_id, CrmInteracao.lead_id == lead.id
        )
        .order_by(CrmInteracao.ocorrida_em.desc(), CrmInteracao.id.desc())
        .limit(limite)
        .all()
    )
    todas = (
        db.query(CrmOportunidade)
        .filter(
            CrmOportunidade.tenant_id == lead.tenant_id,
            CrmOportunidade.lead_id == lead.id,
        )
        .order_by(CrmOportunidade.ciclo.desc(), CrmOportunidade.id)
        .all()
    )
    return {
        "id": lead.id,
        "nome": lead.nome_exibicao or "Sem nome",
        "telefone": lead.telefone,
        "cliente_id": lead.cliente_id,
        "sem_cadastro": lead.cliente_id is None,
        "origem": lead.origem,
        "ciclo": lead.ciclo_atual,
        "coluna_id": lead.coluna_id,
        "motivo_perda": lead.motivo_perda,
        "ultimo_contato_em": lead.ultimo_contato_em.isoformat()
        if lead.ultimo_contato_em
        else None,
        "mensagens": consumo_do_lead(db, lead.tenant_id, lead.id),
        "oportunidades_abertas": [o.id for o in oportunidades_abertas(db, lead)],
        "oportunidades": [
            {
                "id": o.id,
                "ciclo": o.ciclo,
                "tipo": o.tipo,
                "detalhe": o.detalhe,
                "estado": o.estado,
                "motivo": o.motivo,
                "generica": o.generica,
            }
            for o in todas
        ],
        "caminhada": [
            {
                "ciclo": m.ciclo,
                "de": colunas.get(m.coluna_origem_id),
                "para": colunas.get(m.coluna_destino_id),
                "quando": m.created_at.isoformat() if m.created_at else None,
                "nota": m.nota,
            }
            for m in movimentacoes
        ],
        "linha_do_tempo": [
            {
                "tipo": i.tipo,
                "resumo": i.resumo,
                "origem": i.origem,
                "quando": i.ocorrida_em.isoformat() if i.ocorrida_em else None,
            }
            for i in interacoes
        ],
    }


def buscar_tutores(
    db: Session, tenant_id: Any, busca: str, limite: int = 10
) -> list[dict[str, Any]]:
    """Pessoas cadastradas (clientes) por nome ou telefone, para criar/vincular cards."""
    termo = (busca or "").strip()
    if len(termo) < 2:
        return []
    filtros = [Cliente.nome.ilike(f"%{termo}%")]
    digitos = somente_digitos(termo)
    if len(digitos) >= 4:
        filtros += [
            Cliente.celular.ilike(f"%{digitos}%"),
            Cliente.telefone.ilike(f"%{digitos}%"),
        ]
    consulta = db.query(Cliente).filter(
        Cliente.tenant_id == tenant_id,
        Cliente.is_cliente.is_(True),
        Cliente.ativo.is_(True),
        or_(*filtros),
    )
    fundido_em = getattr(Cliente, "merged_into_id", None)
    if fundido_em is not None:
        consulta = consulta.filter(fundido_em.is_(None))
    clientes = consulta.order_by(Cliente.nome).limit(limite).all()
    com_card = {
        linha[0]
        for linha in db.query(CrmLead.cliente_id).filter(
            CrmLead.tenant_id == tenant_id,
            CrmLead.separado_de_lead_id.is_(None),
            CrmLead.cliente_id.in_([c.id for c in clientes] or [0]),
        )
    }
    return [
        {
            "id": c.id,
            "nome": c.nome,
            "telefone": c.celular or c.telefone,
            "tem_card": c.id in com_card,
        }
        for c in clientes
    ]


def vincular_a_cadastro(
    db: Session, lead: CrmLead, cliente_id: int, user_id: int | None = None
) -> CrmLead:
    """Liga um card sem cadastro a uma pessoa ja cadastrada (os dados passam a vir dela)."""
    if lead.cliente_id is not None:
        raise RegraDoCrm("Este card já está ligado a um cadastro.")
    cliente = (
        db.query(Cliente)
        .filter(Cliente.id == cliente_id, Cliente.tenant_id == lead.tenant_id)
        .first()
    )
    if cliente is None:
        raise RegraDoCrm("Pessoa não encontrada nesta loja.")
    if _lead_principal(db, lead.tenant_id, cliente_id=cliente_id) is not None:
        raise RegraDoCrm(
            "Esta pessoa já tem outro card no funil. Use o card dela em vez de criar outro."
        )
    lead.cliente_id = cliente.id
    lead.nome_exibicao = cliente.nome
    db.add(
        CrmInteracao(
            tenant_id=lead.tenant_id,
            lead_id=lead.id,
            cliente_id=cliente.id,
            tipo="vinculo",
            resumo=f"Card ligado ao cadastro de {cliente.nome}",
            origem="usuario" if user_id else "sistema",
        )
    )
    db.flush()
    return lead


def sugerir_vinculo(db: Session, lead: CrmLead) -> dict[str, Any] | None:
    """Pessoa que passou a ter o mesmo telefone de um card sem cadastro, ou None.

    So sugere quem ainda pode ser ligado: a pessoa precisa estar ativa, nao ter outro
    card no funil e nao ter sido recusada para este card ("nao perguntar novamente").
    """
    if lead.cliente_id is not None or not lead.telefone:
        return None
    resolucao = resolver_tutor_por_telefone(db, lead.tenant_id, lead.telefone)
    if resolucao.situacao not in (SITUACAO_UNICO, SITUACAO_AMBIGUO):
        return None
    ignorados = {
        linha[0]
        for linha in db.query(CrmVinculoIgnorado.cliente_id).filter(
            CrmVinculoIgnorado.tenant_id == lead.tenant_id,
            CrmVinculoIgnorado.lead_id == lead.id,
        )
    }
    for cliente_id in resolucao.candidatos:
        if cliente_id in ignorados:
            continue
        cliente = (
            db.query(Cliente)
            .filter(Cliente.id == cliente_id, Cliente.tenant_id == lead.tenant_id)
            .first()
        )
        if cliente is None or cliente.ativo is False:
            continue
        if _lead_principal(db, lead.tenant_id, cliente_id=cliente.id) is not None:
            continue
        return {
            "cliente_id": cliente.id,
            "nome": cliente.nome,
            "telefone": cliente.celular or cliente.telefone,
        }
    return None


def ignorar_sugestao_de_vinculo(
    db: Session, lead: CrmLead, cliente_id: int, user_id: int | None = None
) -> None:
    """Registra que esta pessoa nao deve mais ser sugerida como vinculo deste card."""
    if lead.cliente_id is not None:
        raise RegraDoCrm("Este card já está ligado a um cadastro.")
    existe = (
        db.query(CrmVinculoIgnorado.id)
        .filter(
            CrmVinculoIgnorado.tenant_id == lead.tenant_id,
            CrmVinculoIgnorado.lead_id == lead.id,
            CrmVinculoIgnorado.cliente_id == cliente_id,
        )
        .first()
    )
    if existe is not None:
        return
    cliente = (
        db.query(Cliente.id)
        .filter(Cliente.id == cliente_id, Cliente.tenant_id == lead.tenant_id)
        .first()
    )
    if cliente is None:
        raise RegraDoCrm("Pessoa não encontrada nesta loja.")
    db.add(
        CrmVinculoIgnorado(
            tenant_id=lead.tenant_id,
            lead_id=lead.id,
            cliente_id=cliente_id,
            user_id=user_id,
        )
    )
    db.flush()
