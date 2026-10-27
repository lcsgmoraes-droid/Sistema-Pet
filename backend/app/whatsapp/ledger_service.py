"""Registro e leitura do livro-razao de mensagens de WhatsApp.

Regra de ouro: registrar no livro-razao NUNCA pode atrapalhar o atendimento.
Todas as funcoes `anotar_*` engolem erro (so logam) e usam um savepoint proprio.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.whatsapp.ledger_models import (
    DIRECAO_ENVIADA,
    DIRECAO_RECEBIDA,
    ESTADO_ENTREGUE,
    ESTADO_ENVIADA,
    ESTADO_FALHOU,
    ESTADO_LIDA,
    ESTADO_RECEBIDA,
    ORIGEM_ATENDENTE,
    ORIGEM_DESCONHECIDA,
    ORIGEM_IA,
    ORIGEM_SISTEMA,
    ORIGEM_TUTOR,
    WhatsAppLedger,
)

logger = logging.getLogger(__name__)

JANELA_DE_ATENDIMENTO = timedelta(hours=24)
# Estados que so avancam: enviada -> entregue -> lida.
_ORDEM = {ESTADO_ENVIADA: 1, ESTADO_ENTREGUE: 2, ESTADO_LIDA: 3}
_ESTADO_DA_META = {
    "sent": ESTADO_ENVIADA,
    "delivered": ESTADO_ENTREGUE,
    "read": ESTADO_LIDA,
}


def origem_do_envio(message_type: str, sent_by_user_id: Any) -> str:
    if sent_by_user_id:
        return ORIGEM_ATENDENTE
    if message_type == "notificacao_sistema":
        return ORIGEM_SISTEMA
    return ORIGEM_IA


def provedor_do_cliente(cliente: Any) -> str:
    nome = type(cliente).__name__
    if nome == "MetaCloudClient":
        return "meta_cloud"
    if nome == "Dialog360Client":
        return "360dialog"
    return "waha"


def _agora() -> datetime:
    return datetime.now(UTC)


def _naive_utc(valor: Any) -> datetime | None:
    if valor is None:
        return None
    if valor.tzinfo is not None:
        return valor.astimezone(UTC).replace(tzinfo=None)
    return valor


def janela_aberta(
    db: Session, tenant_id: Any, session_id: Any, agora: datetime | None = None
) -> bool:
    """True se o tutor escreveu nas ultimas 24h (texto livre e de graca dentro dela)."""
    from app.whatsapp.models import WhatsAppMessage

    limite = _naive_utc(agora or _agora()) - JANELA_DE_ATENDIMENTO
    ultima = (
        db.query(func.max(WhatsAppMessage.created_at))
        .filter(
            WhatsAppMessage.tenant_id == tenant_id,
            WhatsAppMessage.session_id == session_id,
            WhatsAppMessage.tipo == "recebida",
        )
        .scalar()
    )
    return bool(ultima and _naive_utc(ultima) >= limite)


def _gravar(db: Session, linha: WhatsAppLedger) -> bool:
    try:
        with db.begin_nested():
            db.add(linha)
        db.commit()
        return True
    except Exception as erro:
        logger.warning(
            "Livro-razao: nao foi possivel registrar (%s)", type(erro).__name__
        )
        try:
            db.rollback()
        except Exception:
            pass
        return False


def anotar_envio(
    db: Session,
    *,
    tenant_id: Any,
    provedor: str,
    session: Any,
    message_row: Any,
    wa_message_id: str | None,
    origem: str,
    tipo_conteudo: str = "texto",
    template_nome: str | None = None,
    template_categoria: str | None = None,
) -> bool:
    try:
        janela = janela_aberta(db, tenant_id, session.id)
        agora = _agora()
        return _gravar(
            db,
            WhatsAppLedger(
                tenant_id=tenant_id,
                direcao=DIRECAO_ENVIADA,
                origem=origem,
                provedor=provedor,
                session_id=str(session.id),
                message_id=str(message_row.id) if message_row is not None else None,
                wa_message_id=wa_message_id,
                telefone=getattr(session, "phone_number", None),
                tipo_conteudo=tipo_conteudo,
                template_nome=template_nome,
                template_categoria=template_categoria,
                janela_24h=janela,
                estado=ESTADO_ENVIADA,
                ocorrido_em=agora,
                enviado_em=agora,
            ),
        )
    except Exception as erro:
        logger.warning("Livro-razao: falha ao montar o envio (%s)", type(erro).__name__)
        return False


def anotar_falha_de_envio(
    db: Session,
    *,
    tenant_id: Any,
    provedor: str,
    session: Any,
    session_id: Any,
    origem: str,
    erro_codigo: Any = None,
    erro_mensagem: str | None = None,
    tipo_conteudo: str = "texto",
) -> bool:
    try:
        agora = _agora()
        return _gravar(
            db,
            WhatsAppLedger(
                tenant_id=tenant_id,
                direcao=DIRECAO_ENVIADA,
                origem=origem,
                provedor=provedor,
                session_id=str(session_id) if session_id else None,
                telefone=getattr(session, "phone_number", None),
                tipo_conteudo=tipo_conteudo,
                estado=ESTADO_FALHOU,
                ocorrido_em=agora,
                falhou_em=agora,
                erro_codigo=str(erro_codigo)[:20] if erro_codigo is not None else None,
                erro_mensagem=(erro_mensagem or "")[:300] or None,
            ),
        )
    except Exception as erro:
        logger.warning("Livro-razao: falha ao montar a falha (%s)", type(erro).__name__)
        return False


def anotar_recebimento(
    db: Session,
    *,
    tenant_id: Any,
    provedor: str,
    session: Any,
    message_row: Any,
    wa_message_id: str | None,
) -> bool:
    try:
        agora = _agora()
        return _gravar(
            db,
            WhatsAppLedger(
                tenant_id=tenant_id,
                direcao=DIRECAO_RECEBIDA,
                origem=ORIGEM_TUTOR,
                provedor=provedor,
                session_id=str(session.id),
                message_id=str(message_row.id),
                wa_message_id=wa_message_id,
                telefone=getattr(session, "phone_number", None),
                estado=ESTADO_RECEBIDA,
                ocorrido_em=agora,
            ),
        )
    except Exception as erro:
        logger.warning(
            "Livro-razao: falha ao montar o recebimento (%s)", type(erro).__name__
        )
        return False


def tarifa_vigente(db: Session, categoria: str | None, dia: Any) -> Decimal | None:
    """Preco (em reais) por mensagem da categoria no dia, ou None se nao houver tarifa."""
    if not categoria:
        return None
    from app.whatsapp.consumo_models import WhatsAppTarifa

    dia = dia.date() if isinstance(dia, datetime) else dia
    tarifa = (
        db.query(WhatsAppTarifa)
        .filter(
            WhatsAppTarifa.categoria == categoria, WhatsAppTarifa.vigente_desde <= dia
        )
        .order_by(WhatsAppTarifa.vigente_desde.desc())
        .first()
    )
    return Decimal(tarifa.valor) if tarifa else None


def estimar_custo(db: Session, linha: WhatsAppLedger) -> bool:
    """Preenche o custo estimado de uma mensagem cobravel com a tarifa do dia."""
    if linha.cobravel is not True or not linha.categoria_cobranca:
        return False
    valor = tarifa_vigente(db, linha.categoria_cobranca, linha.ocorrido_em or _agora())
    if valor is None:
        return False
    linha.custo_estimado = valor
    linha.moeda = "BRL"
    return True


def recalcular_custos(
    db: Session, tenant_id: Any, inicio: datetime, fim: datetime
) -> int:
    """Refaz o custo estimado do periodo (ex.: depois de cadastrar uma tarifa nova)."""
    atualizadas = 0
    consulta = db.query(WhatsAppLedger).filter(
        WhatsAppLedger.tenant_id == tenant_id,
        WhatsAppLedger.ocorrido_em >= inicio,
        WhatsAppLedger.ocorrido_em < fim,
        WhatsAppLedger.cobravel.is_(True),
    )
    for linha in consulta:
        antes = linha.custo_estimado
        if estimar_custo(db, linha) and linha.custo_estimado != antes:
            atualizadas += 1
    return atualizadas


def _de_unix(valor: Any) -> datetime:
    try:
        return datetime.fromtimestamp(int(valor), UTC)
    except (TypeError, ValueError, OverflowError):
        return _agora()


def aplicar_estado_da_meta(
    db: Session, tenant_id: Any, aviso: dict[str, Any], provedor: str = "meta_cloud"
) -> str:
    """Aplica um aviso de estado do webhook (enviada, entregue, lida, falhou + cobranca).

    Devolve "atualizada", "criada" ou "ignorada". Nao faz commit.
    """
    wa_id = str(aviso.get("id") or "").strip()
    codigo = str(aviso.get("status") or "").lower()
    if not wa_id or codigo not in (*_ESTADO_DA_META, "failed"):
        return "ignorada"
    quando = _de_unix(aviso.get("timestamp"))

    linha = (
        db.query(WhatsAppLedger)
        .filter(
            WhatsAppLedger.tenant_id == tenant_id,
            WhatsAppLedger.wa_message_id == wa_id,
        )
        .first()
    )
    criada = False
    if linha is None:
        # Aviso de mensagem que nao saiu por aqui (ex.: enviada pelo app WhatsApp Business).
        linha = WhatsAppLedger(
            tenant_id=tenant_id,
            direcao=DIRECAO_ENVIADA,
            origem=ORIGEM_DESCONHECIDA,
            provedor=provedor,
            wa_message_id=wa_id,
            telefone=aviso.get("recipient_id"),
            estado=ESTADO_ENVIADA,
            ocorrido_em=quando,
        )
        db.add(linha)
        criada = True

    if codigo == "failed":
        if linha.estado not in (ESTADO_ENTREGUE, ESTADO_LIDA):
            linha.estado = ESTADO_FALHOU
            linha.falhou_em = quando
        erros = aviso.get("errors") or []
        if erros:
            linha.erro_codigo = str(erros[0].get("code") or "")[:20] or None
            texto = erros[0].get("title") or erros[0].get("message") or ""
            linha.erro_mensagem = str(texto)[:300] or None
    else:
        novo = _ESTADO_DA_META[codigo]
        if linha.estado == ESTADO_FALHOU or _ORDEM.get(novo, 0) > _ORDEM.get(
            linha.estado, 0
        ):
            linha.estado = novo
        if novo == ESTADO_ENVIADA:
            linha.enviado_em = linha.enviado_em or quando
        elif novo == ESTADO_ENTREGUE:
            linha.entregue_em = linha.entregue_em or quando
        else:
            linha.lido_em = linha.lido_em or quando
            linha.entregue_em = linha.entregue_em or quando

    preco = aviso.get("pricing")
    if isinstance(preco, dict):
        if "billable" in preco:
            linha.cobravel = bool(preco.get("billable"))
        if preco.get("category"):
            linha.categoria_cobranca = str(preco["category"]).lower()[:30]
        if preco.get("pricing_model"):
            linha.modelo_de_preco = str(preco["pricing_model"])[:30]
        estimar_custo(db, linha)
    return "criada" if criada else "atualizada"


def aplicar_avisos_de_estado(
    db: Session,
    tenant_id: Any,
    avisos: list[dict[str, Any]],
    provedor: str = "meta_cloud",
) -> int:
    """Aplica uma lista de avisos e confirma. Erro nunca sobe para o webhook."""
    aplicados = 0
    try:
        for aviso in avisos:
            if aplicar_estado_da_meta(db, tenant_id, aviso, provedor) != "ignorada":
                aplicados += 1
        db.commit()
    except Exception as erro:
        logger.warning(
            "Livro-razao: falha ao aplicar estados (%s)", type(erro).__name__
        )
        try:
            db.rollback()
        except Exception:
            pass
        return 0
    return aplicados


def periodo_do_mes(mes: str | None) -> tuple[datetime, datetime]:
    """(inicio, fim) do mes 'AAAA-MM' em UTC; sem argumento, o mes atual."""
    hoje = _agora()
    if mes:
        try:
            ano, numero = (int(parte) for parte in mes.split("-", 1))
            inicio = datetime(ano, numero, 1, tzinfo=UTC)
        except (ValueError, TypeError) as erro:
            raise ValueError("Mês inválido. Use o formato AAAA-MM.") from erro
    else:
        inicio = datetime(hoje.year, hoje.month, 1, tzinfo=UTC)
    fim = (
        datetime(inicio.year + 1, 1, 1, tzinfo=UTC)
        if inicio.month == 12
        else datetime(inicio.year, inicio.month + 1, 1, tzinfo=UTC)
    )
    return inicio, fim


def resumo_do_periodo(
    db: Session, tenant_id: Any, inicio: datetime, fim: datetime
) -> dict[str, Any]:
    """Totais para conferencia e repasse: por direcao, origem, categoria cobrada e estado."""
    linhas = (
        db.query(
            WhatsAppLedger.direcao,
            WhatsAppLedger.origem,
            WhatsAppLedger.estado,
            WhatsAppLedger.categoria_cobranca,
            WhatsAppLedger.cobravel,
            WhatsAppLedger.janela_24h,
            func.count(WhatsAppLedger.id),
            func.coalesce(func.sum(WhatsAppLedger.custo_estimado), 0),
        )
        .filter(
            WhatsAppLedger.tenant_id == tenant_id,
            WhatsAppLedger.ocorrido_em >= inicio,
            WhatsAppLedger.ocorrido_em < fim,
        )
        .group_by(
            WhatsAppLedger.direcao,
            WhatsAppLedger.origem,
            WhatsAppLedger.estado,
            WhatsAppLedger.categoria_cobranca,
            WhatsAppLedger.cobravel,
            WhatsAppLedger.janela_24h,
        )
        .all()
    )
    total = {
        "enviadas": 0,
        "recebidas": 0,
        "falhas": 0,
        "cobraveis": 0,
        "cobraveis_sem_tarifa": 0,
        "sem_informacao_de_cobranca": 0,
    }
    por_categoria: dict[str, int] = {}
    por_origem: dict[str, int] = {}
    por_estado: dict[str, int] = {}
    custo_estimado = Decimal(0)
    for (
        direcao,
        origem,
        estado,
        categoria,
        cobravel,
        _janela,
        quantidade,
        custo,
    ) in linhas:
        quantidade = int(quantidade)
        custo_estimado += Decimal(custo or 0)
        por_estado[estado] = por_estado.get(estado, 0) + quantidade
        if direcao == DIRECAO_RECEBIDA:
            total["recebidas"] += quantidade
            continue
        total["enviadas"] += quantidade
        por_origem[origem] = por_origem.get(origem, 0) + quantidade
        if estado == ESTADO_FALHOU:
            total["falhas"] += quantidade
        if cobravel is True:
            total["cobraveis"] += quantidade
            chave = categoria or "sem_categoria"
            por_categoria[chave] = por_categoria.get(chave, 0) + quantidade
        elif cobravel is None and estado != ESTADO_FALHOU:
            # A Meta ainda nao informou a cobranca (ou o provedor nao informa).
            total["sem_informacao_de_cobranca"] += quantidade
    # Cobraveis sem tarifa cadastrada: o custo estimado fica subestimado ate cadastrar.
    total["cobraveis_sem_tarifa"] = int(
        db.query(func.count(WhatsAppLedger.id))
        .filter(
            WhatsAppLedger.tenant_id == tenant_id,
            WhatsAppLedger.ocorrido_em >= inicio,
            WhatsAppLedger.ocorrido_em < fim,
            WhatsAppLedger.cobravel.is_(True),
            WhatsAppLedger.custo_estimado.is_(None),
        )
        .scalar()
        or 0
    )
    return {
        "periodo": {"inicio": inicio.isoformat(), "fim": fim.isoformat()},
        "totais": total,
        "cobraveis_por_categoria": por_categoria,
        "enviadas_por_origem": por_origem,
        "por_estado": por_estado,
        "custo_estimado": float(round(custo_estimado, 2)),
    }


def listar_mensagens(
    db: Session, tenant_id: Any, inicio: datetime, fim: datetime, limite: int = 100
) -> list[dict[str, Any]]:
    linhas = (
        db.query(WhatsAppLedger)
        .filter(
            WhatsAppLedger.tenant_id == tenant_id,
            WhatsAppLedger.ocorrido_em >= inicio,
            WhatsAppLedger.ocorrido_em < fim,
        )
        .order_by(WhatsAppLedger.ocorrido_em.desc(), WhatsAppLedger.id.desc())
        .limit(max(1, min(limite, 500)))
        .all()
    )
    return [
        {
            "id": linha.id,
            "quando": linha.ocorrido_em.isoformat() if linha.ocorrido_em else None,
            "direcao": linha.direcao,
            "origem": linha.origem,
            "tipo": linha.tipo_conteudo,
            "modelo": linha.template_nome,
            "estado": linha.estado,
            "dentro_da_janela": linha.janela_24h,
            "cobravel": linha.cobravel,
            "categoria_cobranca": linha.categoria_cobranca,
            "erro": linha.erro_mensagem,
        }
        for linha in linhas
    ]
