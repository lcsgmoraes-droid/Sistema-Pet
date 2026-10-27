"""Carteira de creditos de WhatsApp: franquia mensal + pacotes avulsos, com bloqueio.

Regras:
- o controle e ligado POR LOJA (padrao desligado, para nao bloquear ninguem sem aviso);
- cada envio consome creditos conforme o que e (modelo por categoria, resposta da IA,
  atendente...); avisos automaticos do sistema (ex.: "aguarde um atendente") custam 0;
- primeiro gasta a franquia do mes (que nao acumula), depois os pacotes avulsos;
- sem saldo, o envio e bloqueado (a IA para e a conversa vai para a fila humana);
- registrar consumo nunca derruba o envio que ja saiu.

Os custos padrao abaixo sao VALORES DE EXEMPLO (tema T.1 do roadmap); o OPS pode
sobrescrever cada um na tabela `whatsapp_custos_creditos`.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.whatsapp.creditos_models import (
    COMPRA_PAGA,
    FONTE_AVULSO,
    FONTE_FRANQUIA,
    MOVIMENTO_AJUSTE,
    MOVIMENTO_COMPRA,
    MOVIMENTO_CONSUMO,
    WhatsAppCompraPacote,
    WhatsAppCreditoMovimento,
    WhatsAppCustoCredito,
)
from app.whatsapp.models import TenantWhatsAppConfig

logger = logging.getLogger(__name__)

CUSTOS_PADRAO: dict[str, int] = {
    "modelo_marketing": 10,
    "modelo_utility": 3,
    "modelo_authentication": 3,
    "ia": 2,
    "atendente": 1,
    "sistema": 0,
}
ROTULO_DO_CUSTO = {
    "modelo_marketing": "Modelo de marketing",
    "modelo_utility": "Modelo de utilidade",
    "modelo_authentication": "Modelo de autenticação",
    "ia": "Resposta da IA",
    "atendente": "Mensagem do atendente",
    "sistema": "Aviso automático do sistema",
}
# Abaixo disto (ou de 20% da franquia) a loja recebe o aviso de saldo baixo.
SALDO_BAIXO_MINIMO = 50
SALDO_BAIXO_PERCENTUAL = 0.2


class SemCreditos(Exception):
    """Envio barrado por falta de creditos."""


def _agora() -> datetime:
    return datetime.now(UTC)


def mes_de(quando: datetime | None = None) -> str:
    quando = quando or _agora()
    return f"{quando.year:04d}-{quando.month:02d}"


def tabela_de_custos(db: Session) -> dict[str, int]:
    """Custo em creditos de cada tipo de envio (padrao + ajustes do OPS)."""
    tabela = dict(CUSTOS_PADRAO)
    try:
        for linha in db.query(WhatsAppCustoCredito).all():
            if linha.chave in tabela:
                tabela[linha.chave] = int(linha.creditos)
    except Exception:
        logger.warning(
            "Creditos: tabela de custos do OPS indisponivel; usando o padrao"
        )
    return tabela


def chave_do_custo(origem: str, tipo_conteudo: str, categoria: str | None) -> str:
    if tipo_conteudo == "modelo":
        return (
            f"modelo_{categoria}"
            if categoria in ("marketing", "authentication")
            else "modelo_utility"
        )
    if origem == "sistema":
        return "sistema"
    if origem == "ia":
        return "ia"
    return "atendente"


def custo_em_creditos(
    db: Session, origem: str, tipo_conteudo: str = "texto", categoria: str | None = None
) -> int:
    return tabela_de_custos(db).get(chave_do_custo(origem, tipo_conteudo, categoria), 0)


def _config(
    db: Session, tenant_id: Any, travar: bool = False
) -> TenantWhatsAppConfig | None:
    consulta = db.query(TenantWhatsAppConfig).filter(
        TenantWhatsAppConfig.tenant_id == tenant_id
    )
    if travar:
        consulta = consulta.with_for_update()
    return consulta.first()


def saldo(
    db: Session, tenant_id: Any, config: Any = None, mes: str | None = None
) -> dict[str, Any]:
    """Situacao dos creditos da loja no mes."""
    mes = mes or mes_de()
    config = config if config is not None else _config(db, tenant_id)
    ativo = bool(getattr(config, "creditos_controle_ativo", False))
    franquia = int(getattr(config, "creditos_franquia_mensal", 0) or 0)

    def _soma(*filtros):
        return int(
            db.query(func.coalesce(func.sum(WhatsAppCreditoMovimento.quantidade), 0))
            .filter(WhatsAppCreditoMovimento.tenant_id == tenant_id, *filtros)
            .scalar()
            or 0
        )

    usada = -_soma(
        WhatsAppCreditoMovimento.fonte == FONTE_FRANQUIA,
        WhatsAppCreditoMovimento.tipo == MOVIMENTO_CONSUMO,
        WhatsAppCreditoMovimento.mes == mes,
    )
    avulso = _soma(WhatsAppCreditoMovimento.fonte == FONTE_AVULSO)
    restante = max(franquia - usada, 0)
    disponivel = restante + max(avulso, 0)
    if not ativo:
        nivel = "desligado"
    elif disponivel <= 0:
        nivel = "esgotado"
    elif disponivel <= max(int(franquia * SALDO_BAIXO_PERCENTUAL), SALDO_BAIXO_MINIMO):
        nivel = "baixo"
    else:
        nivel = "ok"
    return {
        "controle_ativo": ativo,
        "mes": mes,
        "franquia_mensal": franquia,
        "franquia_usada": usada,
        "franquia_restante": restante,
        "avulso": avulso,
        "disponivel": disponivel,
        "nivel": nivel,
    }


def pode_gastar(db: Session, tenant_id: Any, creditos: int) -> bool:
    """False so quando o controle esta ligado e nao ha saldo para este envio."""
    if creditos <= 0:
        return True
    try:
        situacao = saldo(db, tenant_id)
    except Exception:
        logger.warning("Creditos: saldo indisponivel; liberando o envio", exc_info=True)
        return True
    return (not situacao["controle_ativo"]) or situacao["disponivel"] >= creditos


def exigir_creditos(db: Session, tenant_id: Any, creditos: int) -> None:
    if not pode_gastar(db, tenant_id, creditos):
        raise SemCreditos(
            "O saldo de créditos de WhatsApp acabou. Compre um pacote para voltar a enviar."
        )


def debitar(
    db: Session,
    tenant_id: Any,
    creditos: int,
    *,
    referencia: str | None = None,
    descricao: str | None = None,
) -> bool:
    """Registra o consumo (franquia primeiro, depois avulso). Nunca derruba o envio."""
    if creditos <= 0:
        return False
    try:
        config = _config(db, tenant_id, travar=True)
        if config is None or not config.creditos_controle_ativo:
            return False
        situacao = saldo(db, tenant_id, config)
        da_franquia = min(creditos, situacao["franquia_restante"])
        do_avulso = creditos - da_franquia
        mes = situacao["mes"]
        with db.begin_nested():
            if da_franquia:
                db.add(
                    WhatsAppCreditoMovimento(
                        tenant_id=tenant_id,
                        tipo=MOVIMENTO_CONSUMO,
                        fonte=FONTE_FRANQUIA,
                        quantidade=-da_franquia,
                        mes=mes,
                        referencia=referencia,
                        descricao=descricao,
                    )
                )
            if do_avulso:
                db.add(
                    WhatsAppCreditoMovimento(
                        tenant_id=tenant_id,
                        tipo=MOVIMENTO_CONSUMO,
                        fonte=FONTE_AVULSO,
                        quantidade=-do_avulso,
                        mes=mes,
                        referencia=referencia,
                        descricao=descricao,
                    )
                )
        db.commit()
        return True
    except Exception as erro:
        logger.warning("Creditos: consumo nao registrado (%s)", type(erro).__name__)
        try:
            db.rollback()
        except Exception:
            logger.debug("Creditos: rollback falhou", exc_info=True)
        return False


def creditar_compra(
    db: Session, compra: WhatsAppCompraPacote, admin_email: str
) -> None:
    """Libera os creditos de uma compra paga. Nao faz commit."""
    db.add(
        WhatsAppCreditoMovimento(
            tenant_id=compra.tenant_id,
            tipo=MOVIMENTO_COMPRA,
            fonte=FONTE_AVULSO,
            quantidade=compra.creditos,
            mes=mes_de(),
            compra_id=compra.id,
            descricao=f"Pacote {compra.pacote_nome}",
            criado_por=admin_email,
        )
    )
    compra.status = COMPRA_PAGA


def ajustar(
    db: Session, tenant_id: Any, quantidade: int, descricao: str, admin_email: str
) -> None:
    """Ajuste manual do OPS (positivo ou negativo) nos creditos avulsos. Nao faz commit."""
    db.add(
        WhatsAppCreditoMovimento(
            tenant_id=tenant_id,
            tipo=MOVIMENTO_AJUSTE,
            fonte=FONTE_AVULSO,
            quantidade=int(quantidade),
            mes=mes_de(),
            descricao=(descricao or "")[:200] or "Ajuste manual",
            criado_por=admin_email,
        )
    )


def extrato(db: Session, tenant_id: Any, limite: int = 50) -> list[dict[str, Any]]:
    linhas = (
        db.query(WhatsAppCreditoMovimento)
        .filter(WhatsAppCreditoMovimento.tenant_id == tenant_id)
        .order_by(WhatsAppCreditoMovimento.id.desc())
        .limit(max(1, min(limite, 200)))
        .all()
    )
    return [
        {
            "id": linha.id,
            "quando": linha.created_at.isoformat() if linha.created_at else None,
            "tipo": linha.tipo,
            "fonte": linha.fonte,
            "quantidade": linha.quantidade,
            "descricao": linha.descricao,
        }
        for linha in linhas
    ]
