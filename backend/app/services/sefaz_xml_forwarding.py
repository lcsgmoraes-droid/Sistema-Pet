"""Encaminhamento duravel dos XMLs completos de entrada ao escritorio contabil.

O chamador serializa esta rotina com um lock dedicado ao envio de e-mails. O
registro de cada NF-e e confirmado antes do SMTP para permitir nova tentativa
sem repetir envios nas execucoes normais do scheduler.
"""

from datetime import datetime, timedelta, timezone
from html import escape
import json
import logging
from pathlib import Path
from uuid import UUID

from defusedxml import ElementTree as ET
from email_validator import EmailNotValidError, validate_email
from sqlalchemy import and_, or_

from app.produtos_compras_models import (
    SefazDocumentoDistribuido,
    SefazXmlEncaminhamento,
)
from app.services.email_service import is_email_configured, send_email
from app.services.tenant_email_settings import resolve_tenant_reply_to
from app.tenancy.context import tenant_context


logger = logging.getLogger(__name__)
STATUS_ENVIAVEIS = (
    "pendente_importacao",
    "erro_processamento",
    "importada",
    "duplicada",
)
STATUS_PENDENTES = ("pendente", "erro")


def _horario_configurado(valor: object) -> datetime | None:
    if not isinstance(valor, str) or not valor.strip():
        return None
    try:
        data = datetime.fromisoformat(valor.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if data.tzinfo is None:
        return None
    return data.astimezone(timezone.utc)


def _ativado_em(config: dict) -> datetime | None:
    return _horario_configurado(config.get("encaminhamento_ativado_em"))


def _inicio_em(config: dict) -> datetime | None:
    valor = config.get("encaminhamento_inicio_em")
    if valor is not None and str(valor).strip():
        return _horario_configurado(valor)
    return _ativado_em(config)


def _destino(config: dict) -> str | None:
    raw = str(config.get("encaminhamento_email_destino") or "").strip()
    try:
        return validate_email(raw, check_deliverability=False).normalized
    except EmailNotValidError:
        return None


def _nome_tag(elemento) -> str:
    return str(elemento.tag).rsplit("}", 1)[-1]


def _filho(elemento, nome: str):
    return next((filho for filho in elemento if _nome_tag(filho) == nome), None)


def _xml_valido_para_envio(
    documento: SefazDocumentoDistribuido, chave: str, cnpj: str
) -> bool:
    """Confirma que o XML completo pertence ao CNPJ antes de anexá-lo."""
    if (
        documento.tipo != "procNFe"
        or documento.status not in STATUS_ENVIAVEIS
        or not documento.raw_xml
        or len(chave) != 44
        or not chave.isdigit()
        or len(cnpj) != 14
        or not cnpj.isdigit()
    ):
        return False
    try:
        raiz = ET.fromstring(documento.raw_xml)
        if _nome_tag(raiz) != "nfeProc":
            return False
        nfe = _filho(raiz, "NFe")
        inf_nfe = _filho(nfe, "infNFe")
        if inf_nfe is None or inf_nfe.get("Id") != f"NFe{chave}":
            return False
        if _filho(raiz, "protNFe") is None:
            return False
        dest = _filho(inf_nfe, "dest")
        cnpj_xml = _filho(dest, "CNPJ")
        return (
            cnpj_xml is not None
            and "".join(ch for ch in str(cnpj_xml.text or "") if ch.isdigit())
            == cnpj
        )
    except Exception:  # XML malformed or entity expansion is never sent onward.
        return False


def _proxima_tentativa(tentativas: int, agora: datetime) -> datetime:
    minutos = min(15 * (2 ** min(max(tentativas - 1, 0), 7)), 24 * 60)
    return agora + timedelta(minutes=minutos)


def _config_ainda_atual(
    config_path: Path | None, destino: str, cnpj: str, inicio_em: datetime
) -> bool:
    if config_path is None:
        return True
    try:
        atual = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if not isinstance(atual, dict):
        return False
    return (
        bool(atual.get("encaminhamento_email_ativo"))
        and _destino(atual) == destino
        and "".join(ch for ch in str(atual.get("cnpj") or "") if ch.isdigit())
        == cnpj
        and _inicio_em(atual) == inicio_em
    )


def _registrar_novas_pendencias(
    db,
    tenant_uuid: UUID,
    cnpj: str,
    destino: str,
    ativado_em: datetime,
    inicio_em: datetime,
    limite: int,
) -> int:
    """Insere XMLs capturados após o início configurado, sem duplicar a chave."""
    documentos = (
        db.query(SefazDocumentoDistribuido)
        .outerjoin(
            SefazXmlEncaminhamento,
            and_(
                SefazXmlEncaminhamento.tenant_id == tenant_uuid,
                SefazXmlEncaminhamento.chave_acesso
                == SefazDocumentoDistribuido.chave_acesso,
            ),
        )
        .filter(
            SefazDocumentoDistribuido.tenant_id == tenant_uuid,
            SefazDocumentoDistribuido.tipo == "procNFe",
            SefazDocumentoDistribuido.status.in_(STATUS_ENVIAVEIS),
            SefazDocumentoDistribuido.created_at >= inicio_em,
            SefazDocumentoDistribuido.chave_acesso.isnot(None),
            SefazXmlEncaminhamento.id.is_(None),
        )
        .order_by(
            SefazDocumentoDistribuido.created_at.asc(),
            SefazDocumentoDistribuido.id.asc(),
        )
        .limit(limite * 5)
        .all()
    )
    vistos: set[str] = set()
    novos = 0
    for documento in documentos:
        chave = str(documento.chave_acesso or "")
        if chave in vistos or not _xml_valido_para_envio(documento, chave, cnpj):
            continue
        vistos.add(chave)
        db.add(
            SefazXmlEncaminhamento(
                tenant_id=tenant_uuid,
                documento_id=documento.id,
                chave_acesso=chave,
                email_destino=destino,
                ativado_em=ativado_em,
                status="pendente",
                tentativas=0,
            )
        )
        novos += 1
        if novos >= limite:
            break
    if novos:
        db.commit()
    return novos


def _atualizar_destino_pendente(
    db, tenant_uuid: UUID, destino: str, ativado_em: datetime
) -> int:
    """Pendente segue o destino atual; comprovante já enviado nunca é alterado."""
    pendencias = (
        db.query(SefazXmlEncaminhamento)
        .filter(
            SefazXmlEncaminhamento.tenant_id == tenant_uuid,
            SefazXmlEncaminhamento.status.in_(STATUS_PENDENTES),
            SefazXmlEncaminhamento.email_destino != destino,
        )
        .all()
    )
    for registro in pendencias:
        registro.email_destino = destino
        registro.ativado_em = ativado_em
        registro.status = "pendente"
        registro.proxima_tentativa_em = None
        registro.ultimo_erro = None
    if pendencias:
        db.commit()
    return len(pendencias)


def processar_encaminhamentos_sefaz(
    db,
    tenant_id_str: str,
    cfg: dict,
    limite: int = 20,
    config_path: Path | None = None,
) -> dict:
    """Enfileira e envia NF-e completas uma vez por chave para o destino atual.

    Erros SMTP ficam na outbox com backoff. Desativar interrompe os envios;
    reativar retoma pendências já criadas. Se o endereço mudar, só pendências
    ainda não enviadas são redirecionadas ao destinatário vigente.
    """
    if not cfg.get("encaminhamento_email_ativo"):
        return {"status": "desativado", "novos": 0, "enviados": 0, "falhas": 0}
    destino = _destino(cfg)
    ativado_em = _ativado_em(cfg)
    inicio_em = _inicio_em(cfg)
    cnpj = "".join(ch for ch in str(cfg.get("cnpj") or "") if ch.isdigit())
    if not destino or not ativado_em or not inicio_em or len(cnpj) != 14:
        return {
            "status": "configuracao_invalida",
            "novos": 0,
            "enviados": 0,
            "falhas": 0,
        }
    tenant_uuid = UUID(tenant_id_str)
    limite = max(1, min(int(limite), 100))
    agora = datetime.now(timezone.utc)

    with tenant_context(tenant_uuid):
        if not _config_ainda_atual(config_path, destino, cnpj, inicio_em):
            return {
                "status": "configuracao_alterada",
                "novos": 0,
                "enviados": 0,
                "falhas": 0,
            }
        retargeted = _atualizar_destino_pendente(db, tenant_uuid, destino, ativado_em)
        novos = _registrar_novas_pendencias(
            db, tenant_uuid, cnpj, destino, ativado_em, inicio_em, limite
        )
        pendencias = (
            db.query(SefazXmlEncaminhamento, SefazDocumentoDistribuido)
            .join(
                SefazDocumentoDistribuido,
                and_(
                    SefazDocumentoDistribuido.id
                    == SefazXmlEncaminhamento.documento_id,
                    SefazDocumentoDistribuido.tenant_id == tenant_uuid,
                ),
            )
            .filter(
                SefazXmlEncaminhamento.tenant_id == tenant_uuid,
                SefazXmlEncaminhamento.email_destino == destino,
                SefazXmlEncaminhamento.status.in_(STATUS_PENDENTES),
                or_(
                    SefazXmlEncaminhamento.proxima_tentativa_em.is_(None),
                    SefazXmlEncaminhamento.proxima_tentativa_em <= agora,
                ),
            )
            .order_by(SefazXmlEncaminhamento.id.asc())
            .limit(limite)
            .all()
        )

        enviados = 0
        falhas = 0
        configuracao_alterada = False
        reply_to = resolve_tenant_reply_to(db, tenant_uuid)
        for registro, documento in pendencias:
            if not _config_ainda_atual(config_path, destino, cnpj, inicio_em):
                configuracao_alterada = True
                break
            # A checagem é repetida imediatamente antes de ler o anexo.
            if not _xml_valido_para_envio(documento, registro.chave_acesso, cnpj):
                registro.status = "invalido"
                registro.ultimo_erro = "XML completo ou destinatário inválido."
                db.commit()
                falhas += 1
                continue

            chave = registro.chave_acesso
            corpo = (
                "Segue o XML completo da NF-e de entrada capturada pelo CorePet. "
                f"Chave de acesso: {chave}."
            )
            try:
                enviado = bool(is_email_configured()) and send_email(
                    to=destino,
                    subject=f"CorePet - XML de NF-e de entrada {chave}",
                    html_body=f"<p>{escape(corpo)}</p>",
                    text_body=corpo,
                    attachments=[
                        {
                            "filename": f"NFe_{chave}.xml",
                            "content": documento.raw_xml,
                            "mime_subtype": "xml",
                        }
                    ],
                    simulate_if_unconfigured=False,
                    reply_to=reply_to,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "[SEFAZ] Falha no envio do XML para tenant %s (%s)",
                    tenant_uuid,
                    type(exc).__name__,
                )
                enviado = False

            instante = datetime.now(timezone.utc)
            registro.tentativas += 1
            if enviado:
                registro.status = "enviado"
                registro.enviado_em = instante
                registro.proxima_tentativa_em = None
                registro.ultimo_erro = None
                enviados += 1
            else:
                registro.status = "erro"
                registro.proxima_tentativa_em = _proxima_tentativa(
                    registro.tentativas, instante
                )
                registro.ultimo_erro = "Falha no envio SMTP; nova tentativa agendada."
                falhas += 1
            db.commit()

        return {
            "status": (
                "configuracao_alterada"
                if configuracao_alterada
                else "ok" if falhas == 0 else "erro_envio"
            ),
            "novos": novos,
            "redirecionados": retargeted,
            "enviados": enviados,
            "falhas": falhas,
        }
