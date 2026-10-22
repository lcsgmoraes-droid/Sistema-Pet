"""Regras do funil (etapa 2): colunas, movimentacao, ciclos e oportunidades.

Regras em docs/crm/CONTRATOS_CONCEITUAIS.md ("Card por tutor e oportunidades",
"Ciclo e colunas finais"). O servico nao faz commit: quem chama (rota) decide.
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
    OPORTUNIDADE_ABERTA,
    OPORTUNIDADE_DESCARTADA,
    OPORTUNIDADE_RESOLVIDA,
    TIPOS_DE_COLUNA,
    CrmColuna,
    CrmInteracao,
    CrmLead,
    CrmMovimentacao,
    CrmOportunidade,
)

MAXIMO_DE_COLUNAS = 8
TIPOS_FINAIS = (COLUNA_CONCLUIDO, COLUNA_ENCERRADO)


class RegraDoCrm(Exception):
    """Violacao de regra de negocio do CRM (a rota responde 422 com a mensagem)."""


def _agora() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Colunas configuraveis
# ---------------------------------------------------------------------------


def validar_colunas(colunas: list[dict[str, Any]]) -> None:
    """Minimo 1 entrada e 1 concluido, maximo 8, nomes unicos e tipos validos."""
    if not colunas:
        raise RegraDoCrm("O funil precisa de pelo menos uma coluna.")
    if len(colunas) > MAXIMO_DE_COLUNAS:
        raise RegraDoCrm(f"O funil pode ter no máximo {MAXIMO_DE_COLUNAS} colunas.")
    nomes = set()
    for coluna in colunas:
        nome = str(coluna.get("nome") or "").strip()
        if not nome:
            raise RegraDoCrm("Toda coluna precisa de um nome.")
        if len(nome) > 60:
            raise RegraDoCrm("O nome da coluna pode ter no máximo 60 letras.")
        if nome.casefold() in nomes:
            raise RegraDoCrm(f"Já existe uma coluna chamada “{nome}”.")
        nomes.add(nome.casefold())
        if coluna.get("tipo") not in TIPOS_DE_COLUNA:
            raise RegraDoCrm(f"Tipo de coluna inválido em “{nome}”.")
        janela = coluna.get("janela_dias")
        if janela is not None and int(janela) < 1:
            raise RegraDoCrm("A janela de dias da coluna precisa ser 1 ou mais.")
    tipos = [coluna["tipo"] for coluna in colunas]
    if COLUNA_ENTRADA not in tipos:
        raise RegraDoCrm("O funil precisa de uma coluna de entrada.")
    if COLUNA_CONCLUIDO not in tipos:
        raise RegraDoCrm("O funil precisa de uma coluna de concluído.")


def salvar_colunas(
    db: Session, tenant_id: Any, funil_id: int, colunas: list[dict[str, Any]]
) -> list[CrmColuna]:
    """Substitui a configuracao do funil. A ordem e a da lista recebida.

    Itens com `id` atualizam a coluna existente; sem `id` criam. Coluna que
    sai da lista so pode ser removida se nao tiver cards.
    """
    validar_colunas(colunas)
    atuais = {
        c.id: c
        for c in db.query(CrmColuna).filter(
            CrmColuna.tenant_id == tenant_id, CrmColuna.funil_id == funil_id
        )
    }
    mantidos = {c["id"] for c in colunas if c.get("id") is not None}
    if mantidos - set(atuais):
        raise RegraDoCrm("Coluna desconhecida neste funil.")
    for coluna_id, coluna in atuais.items():
        if coluna_id in mantidos:
            continue
        com_cards = (
            db.query(CrmLead.id)
            .filter(CrmLead.tenant_id == tenant_id, CrmLead.coluna_id == coluna_id)
            .first()
        )
        if com_cards:
            raise RegraDoCrm(
                f"A coluna “{coluna.nome}” ainda tem cards. Mova-os antes de removê-la."
            )
        db.delete(coluna)

    resultado = []
    for ordem, spec in enumerate(colunas, start=1):
        coluna = atuais.get(spec.get("id"))
        if coluna is None:
            coluna = CrmColuna(tenant_id=tenant_id, funil_id=funil_id)
            db.add(coluna)
        coluna.nome = spec["nome"].strip()
        coluna.tipo = spec["tipo"]
        coluna.ordem = ordem
        coluna.janela_dias = spec.get("janela_dias")
        resultado.append(coluna)
    db.flush()
    return resultado


# ---------------------------------------------------------------------------
# Oportunidades
# ---------------------------------------------------------------------------


def oportunidades_abertas(db: Session, lead: CrmLead) -> list[CrmOportunidade]:
    """Abertas do ciclo atual: a mais especifica primeiro (generica por ultimo)."""
    itens = (
        db.query(CrmOportunidade)
        .filter(
            CrmOportunidade.tenant_id == lead.tenant_id,
            CrmOportunidade.lead_id == lead.id,
            CrmOportunidade.ciclo == lead.ciclo_atual,
            CrmOportunidade.estado == OPORTUNIDADE_ABERTA,
        )
        .order_by(CrmOportunidade.id)
        .all()
    )
    return sorted(itens, key=lambda o: o.generica)


def _coluna_de_entrada(db: Session, lead: CrmLead) -> CrmColuna:
    entrada = (
        db.query(CrmColuna)
        .filter(
            CrmColuna.tenant_id == lead.tenant_id,
            CrmColuna.funil_id == lead.funil_id,
            CrmColuna.tipo == COLUNA_ENTRADA,
            CrmColuna.ativo.is_(True),
        )
        .order_by(CrmColuna.ordem)
        .first()
    )
    if entrada is None:
        raise RegraDoCrm("O funil não tem coluna de entrada.")
    return entrada


def registrar_sinal(
    db: Session,
    lead: CrmLead,
    *,
    tipo: str,
    detalhe: str | None = None,
    generica: bool = False,
    user_id: int | None = None,
) -> CrmOportunidade:
    """Soma um motivo de contato ao card.

    - card aberto: soma ao ciclo atual (sem duplicar o mesmo tipo e detalhe);
    - card concluido ou encerrado: abre um NOVO ciclo e volta para a entrada.
    """
    coluna = db.get(CrmColuna, lead.coluna_id)
    if coluna is not None and coluna.tipo in TIPOS_FINAIS:
        lead.ciclo_atual += 1
        entrada = _coluna_de_entrada(db, lead)
        _gravar_movimentacao(
            db, lead, coluna.id, entrada.id, user_id, f"Novo ciclo: {tipo}"
        )
        lead.coluna_id = entrada.id
        lead.coluna_desde = _agora()
        lead.motivo_perda = None
    else:
        repetida = next(
            (
                o
                for o in oportunidades_abertas(db, lead)
                if o.tipo == tipo and (o.detalhe or None) == (detalhe or None)
            ),
            None,
        )
        if repetida is not None:
            return repetida
    oportunidade = CrmOportunidade(
        tenant_id=lead.tenant_id,
        lead_id=lead.id,
        ciclo=lead.ciclo_atual,
        tipo=tipo,
        detalhe=detalhe,
        generica=generica,
    )
    db.add(oportunidade)
    db.add(
        CrmInteracao(
            tenant_id=lead.tenant_id,
            lead_id=lead.id,
            cliente_id=lead.cliente_id,
            tipo="oportunidade",
            resumo=f"Oportunidade: {tipo}" + (f" — {detalhe}" if detalhe else ""),
            origem="sistema",
        )
    )
    db.flush()
    return oportunidade


# ---------------------------------------------------------------------------
# Movimentacao e ciclos
# ---------------------------------------------------------------------------


def _gravar_movimentacao(
    db: Session,
    lead: CrmLead,
    origem_id: int | None,
    destino_id: int,
    user_id: int | None,
    nota: str | None,
) -> None:
    db.add(
        CrmMovimentacao(
            tenant_id=lead.tenant_id,
            lead_id=lead.id,
            ciclo=lead.ciclo_atual,
            coluna_origem_id=origem_id,
            coluna_destino_id=destino_id,
            user_id=user_id,
            nota=nota,
        )
    )


def _fechar_ciclo(
    abertas: list[CrmOportunidade], resultados: dict[int, dict[str, Any]] | None
) -> None:
    """Cada oportunidade aberta precisa de um resultado (resolvida ou descartada)."""
    resultados = resultados or {}
    faltando = [o for o in abertas if o.id not in resultados]
    if faltando:
        raise RegraDoCrm(
            "Informe o resultado de cada oportunidade aberta antes de concluir o card."
        )
    agora = _agora()
    for oportunidade in abertas:
        resultado = resultados[oportunidade.id]
        estado = resultado.get("estado")
        if estado not in (OPORTUNIDADE_RESOLVIDA, OPORTUNIDADE_DESCARTADA):
            raise RegraDoCrm("O resultado deve ser resolvida ou descartada.")
        motivo = (resultado.get("motivo") or "").strip() or None
        if estado == OPORTUNIDADE_DESCARTADA and not motivo:
            raise RegraDoCrm("Informe o motivo de descartar a oportunidade.")
        oportunidade.estado = estado
        oportunidade.motivo = motivo
        oportunidade.resolvida_em = agora


def _reabrir_ciclo(db: Session, lead: CrmLead) -> None:
    for oportunidade in db.query(CrmOportunidade).filter(
        CrmOportunidade.tenant_id == lead.tenant_id,
        CrmOportunidade.lead_id == lead.id,
        CrmOportunidade.ciclo == lead.ciclo_atual,
        CrmOportunidade.estado != OPORTUNIDADE_ABERTA,
    ):
        oportunidade.estado = OPORTUNIDADE_ABERTA
        oportunidade.motivo = None
        oportunidade.resolvida_em = None
    lead.motivo_perda = None


def mover_lead(
    db: Session,
    lead: CrmLead,
    coluna_destino_id: int,
    *,
    user_id: int | None = None,
    nota: str | None = None,
    resultados: dict[int, dict[str, Any]] | None = None,
    motivo_perda: str | None = None,
) -> CrmLead:
    """Move o card de coluna gravando a movimentacao.

    - para coluna final: exige o resultado de cada oportunidade aberta (fecha o ciclo);
      coluna "encerrado" exige tambem o motivo da perda;
    - de coluna final para uma nao final: reabre as oportunidades do ciclo.
    """
    if coluna_destino_id == lead.coluna_id:
        return lead
    destino = (
        db.query(CrmColuna)
        .filter(
            CrmColuna.id == coluna_destino_id,
            CrmColuna.tenant_id == lead.tenant_id,
            CrmColuna.funil_id == lead.funil_id,
            CrmColuna.ativo.is_(True),
        )
        .first()
    )
    if destino is None:
        raise RegraDoCrm("Coluna de destino não encontrada neste funil.")
    origem = db.get(CrmColuna, lead.coluna_id)
    origem_final = origem is not None and origem.tipo in TIPOS_FINAIS

    if destino.tipo in TIPOS_FINAIS:
        if destino.tipo == COLUNA_ENCERRADO and not (motivo_perda or "").strip():
            raise RegraDoCrm("Informe o motivo para encerrar o card sem resultado.")
        if not origem_final:
            _fechar_ciclo(oportunidades_abertas(db, lead), resultados)
        lead.motivo_perda = (
            (motivo_perda or "").strip() or None
            if destino.tipo == COLUNA_ENCERRADO
            else None
        )
    elif origem_final:
        _reabrir_ciclo(db, lead)

    _gravar_movimentacao(db, lead, lead.coluna_id, destino.id, user_id, nota)
    db.add(
        CrmInteracao(
            tenant_id=lead.tenant_id,
            lead_id=lead.id,
            cliente_id=lead.cliente_id,
            tipo="etapa",
            resumo=f"Movido para “{destino.nome}”",
            origem="usuario" if user_id else "sistema",
        )
    )
    lead.coluna_id = destino.id
    lead.coluna_desde = _agora()
    db.flush()
    return lead


__all__ = [
    "COLUNA_ANDAMENTO",
    "MAXIMO_DE_COLUNAS",
    "RegraDoCrm",
    "mover_lead",
    "oportunidades_abertas",
    "registrar_sinal",
    "salvar_colunas",
    "validar_colunas",
]
