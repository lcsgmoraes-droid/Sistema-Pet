"""Tipos, limites e convenções compartilhadas do envio de XML contábil."""

from datetime import timezone
from uuid import UUID
from zoneinfo import ZoneInfo

BRASILIA = ZoneInfo("America/Sao_Paulo")


UTC = timezone.utc


NS = {"n": "http://www.portalfiscal.inf.br/nfe"}


MAX_DOCUMENTOS = 1000


MAX_XML_BYTES = 10 * 1024 * 1024


MAX_TOTAL_BYTES = 30 * 1024 * 1024


MAX_ZIP_BYTES = 15 * 1024 * 1024


MAX_TENTATIVAS = 3


STATUS_VALIDOS = ("autorizada", "cancelada", "cancelado")


class XmlContabilidadeError(ValueError):
    def __init__(self, message, status_code=422):
        super().__init__(message)
        self.status_code = status_code


def _utc(value):
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _tenant(value):
    return UUID(str(value))


def _status(value):
    value = str(value or "").strip().lower()
    return "cancelada" if value == "cancelado" else value


def _validar_periodo(data_inicio, data_fim):
    if data_fim < data_inicio or (data_fim - data_inicio).days > 365:
        raise XmlContabilidadeError("Escolha um período válido, de no máximo 366 dias.")
