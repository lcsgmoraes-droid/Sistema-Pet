"""Validacao e geracao de documentos das NF-e de entrada."""

from brazilfiscalreport.danfe import Danfe
from defusedxml import ElementTree as ET


NS = {"n": "http://www.portalfiscal.inf.br/nfe"}
STATUS_AUTORIZADOS = {"100", "150"}


def validar_xml_nfe_entrada(xml_content: str, chave_acesso: str) -> str:
    """Confirma que o XML salvo e uma NF-e modelo 55 autorizada da nota pedida."""
    if not str(xml_content or "").strip():
        raise ValueError("O XML original desta nota nao esta disponivel.")

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as exc:
        raise ValueError("O XML original desta nota esta invalido.") from exc

    info = root.find(".//n:infNFe", NS)
    protocolo = root.find(".//n:protNFe/n:infProt", NS)
    chave = str(chave_acesso or "").strip()
    modelo = (
        info.findtext("n:ide/n:mod", default="", namespaces=NS)
        if info is not None
        else ""
    )
    chave_protocolo = (
        protocolo.findtext("n:chNFe", default="", namespaces=NS)
        if protocolo is not None
        else ""
    )
    status = (
        protocolo.findtext("n:cStat", default="", namespaces=NS)
        if protocolo is not None
        else ""
    )

    if info is None or info.get("Id") != f"NFe{chave}" or modelo != "55":
        raise ValueError("O XML salvo nao corresponde a esta NF-e de entrada.")
    if chave_protocolo != chave or status not in STATUS_AUTORIZADOS:
        raise ValueError("A NF-e ainda nao possui protocolo de autorizacao valido.")

    return xml_content


def gerar_danfe_entrada(xml_content: str, chave_acesso: str) -> bytes:
    """Gera o DANFE A4 diretamente do XML autorizado armazenado no CorePet."""
    xml_validado = validar_xml_nfe_entrada(xml_content, chave_acesso)

    try:
        pdf = bytes(Danfe(xml=xml_validado).output())
    except Exception as exc:
        raise RuntimeError("Nao foi possivel gerar o DANFE desta NF-e.") from exc

    if not pdf.startswith(b"%PDF-"):
        raise RuntimeError("O gerador nao produziu um PDF valido para esta NF-e.")

    return pdf
