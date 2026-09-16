from urllib.parse import urlsplit

from defusedxml import ElementTree as ET


NFE_XML_NAMESPACE = {"nfe": "http://www.portalfiscal.inf.br/nfe"}


def extrair_link_publico_nfce(xml: str | bytes) -> str:
    """Extrai do XML autorizado o link oficial de consulta publica da NFC-e."""
    if not xml:
        raise ValueError("O XML autorizado da NFC-e não está disponível.")

    try:
        raiz = ET.fromstring(xml)
    except (ET.ParseError, TypeError, ValueError) as exc:
        raise ValueError("O XML autorizado da NFC-e é inválido.") from exc

    elemento = raiz.find(".//nfe:infNFeSupl/nfe:qrCode", NFE_XML_NAMESPACE)
    link = (elemento.text if elemento is not None else "") or ""
    link = link.strip()
    if not link:
        raise ValueError("O XML autorizado não contém o link de consulta da NFC-e.")

    url = urlsplit(link)
    host = (url.hostname or "").lower().rstrip(".")
    if (
        url.scheme != "https"
        or not host
        or not (host == "gov.br" or host.endswith(".gov.br"))
    ):
        raise ValueError("O link de consulta da NFC-e não pertence à SEFAZ.")

    return link
