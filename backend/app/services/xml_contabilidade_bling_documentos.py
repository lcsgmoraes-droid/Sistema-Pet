"""Documentos NF-e oficiais do Bling, com bytes e eventos completos preservados."""

import base64
from binascii import Error as Base64Error
from gzip import BadGzipFile, GzipFile
from io import BytesIO
import re
from zlib import error as ZlibError

from defusedxml import ElementTree as ET

from app.bling_integration import BlingAPI
from app.services.xml_contabilidade_common import (
    MAX_TOTAL_BYTES,
    MAX_XML_BYTES,
    NS,
    XmlContabilidadeError,
)

# Comporta a nota, as sequências de CC-e e diversos outros tipos de evento.
# Acima deste limite explícito, é necessária confirmação do provedor/suporte.
MAX_ARQUIVOS_POR_NOTA = 1000


def _erro_documentos():
    return XmlContabilidadeError(
        "O Bling não confirmou todos os documentos fiscais originais da nota. "
        "Nenhum arquivo parcial foi preparado.",
        409,
    )


def _validar_referencia(chave, cnpj):
    if (
        not isinstance(chave, str)
        or not re.fullmatch(r"[0-9]{44}", chave)
        or chave[20:22] != "55"
        or not isinstance(cnpj, str)
        or not re.fullmatch(r"[0-9]{14}", cnpj)
        or chave[6:20] != cnpj
    ):
        raise _erro_documentos()


def _decodificar_xml(conteudo, limite):
    # Limitar antes de alocar o conteúdo decodificado e antes de expandir GZIP.
    max_base64 = 4 * ((MAX_XML_BYTES + 2) // 3)
    if not isinstance(conteudo, str) or not conteudo or len(conteudo) > max_base64:
        raise _erro_documentos()
    try:
        comprimido = base64.b64decode(conteudo, validate=True)
        if len(comprimido) > MAX_XML_BYTES:
            raise _erro_documentos()
        with GzipFile(fileobj=BytesIO(comprimido)) as arquivo:
            xml = arquivo.read(limite + 1)
    except (Base64Error, BadGzipFile, EOFError, OSError, ValueError, ZlibError):
        raise _erro_documentos() from None
    if not xml.strip() or len(xml) > limite:
        raise _erro_documentos()
    return xml, len(comprimido)


def decodificar_documentos_nfe(payload, chave, cnpj):
    """Classifica a lista oficial pelo XML, sem confiar no nome do arquivo.

    Contrato: GET /nfe/documento/{chaveAcesso}?formato=xml retorna data[] com
    conteúdo GZIP/base64. Nota e cada evento conservam os bytes recebidos.
    """
    from app.services.xml_contabilidade_documentos import validar_xml_saida
    from app.services.xml_contabilidade_eventos import (
        _validar_evento,
        coletar_eventos,
    )

    _validar_referencia(chave, cnpj)
    documentos = payload.get("data") if isinstance(payload, dict) else None
    if (
        not isinstance(documentos, list)
        or not documentos
        or len(documentos) > MAX_ARQUIVOS_POR_NOTA
    ):
        raise _erro_documentos()
    nota, root_nota = None, None
    eventos = {}
    total, total_comprimido = 0, 0
    for documento in documentos:
        if not isinstance(documento, dict):
            raise _erro_documentos()
        limite = min(MAX_XML_BYTES, MAX_TOTAL_BYTES - total)
        xml, tamanho_comprimido = _decodificar_xml(documento.get("conteudo"), limite)
        total += len(xml)
        total_comprimido += tamanho_comprimido
        if total_comprimido > MAX_TOTAL_BYTES:
            raise _erro_documentos()
        try:
            root = ET.fromstring(xml)
        except Exception:
            raise _erro_documentos() from None
        if root.tag == f"{{{NS['n']}}}nfeProc":
            validacao = validar_xml_saida(xml, chave, 55)
            if (
                validacao is None
                or root.findtext(".//n:infNFe/n:emit/n:CNPJ", namespaces=NS) != cnpj
            ):
                raise _erro_documentos()
            if nota is not None and nota != xml:
                raise _erro_documentos()
            nota, root_nota = xml, root
        elif root.tag == f"{{{NS['n']}}}procEventoNFe":
            evento = _validar_evento(root, xml, chave, cnpj)
            anterior = eventos.get(evento.identidade)
            if anterior is not None and anterior != xml:
                raise _erro_documentos()
            eventos[evento.identidade] = xml
        else:
            raise _erro_documentos()
    if nota is None:
        raise _erro_documentos()
    # A mesma validação usada pelo lote exige sequências completas de CC-e e
    # também confere comprovantes eventualmente embutidos no arquivo da nota.
    xmls_eventos = list(eventos.values())
    coletar_eventos(
        root_nota,
        {"xmlEvento": xmls_eventos},
        chave,
        cnpj,
        xml_original=nota,
    )
    return nota, xmls_eventos


def obter_documentos_nfe(tenant_id, chave, cnpj):
    """Consulta sempre o recurso canônico: o link isolado pode omitir eventos."""
    _validar_referencia(chave, cnpj)
    try:
        payload = BlingAPI(tenant_id=tenant_id)._request(
            "GET", f"/nfe/documento/{chave}", data={"formato": "xml"}
        )
    except Exception:
        raise XmlContabilidadeError(
            "Não foi possível confirmar todos os documentos fiscais no Bling. "
            "Nenhum arquivo parcial foi preparado.",
            503,
        ) from None
    return decodificar_documentos_nfe(payload, chave, cnpj)
