import xml.etree.ElementTree as ET

import requests

from app.nfe.listagem_base import (
    _FINALIDADE_MAP,
    _INDICADOR_PRESENCA_MAP,
    _REGIME_TRIBUTARIO_MAP,
    _XML_NS,
    _primeiro_preenchido,
    _separar_data_hora,
    _texto,
)
from app.utils.logger import logger


def _extrair_campos_fiscais_do_xml(xml_texto: str | None) -> dict:
    if not _texto(xml_texto):
        return {}

    root = ET.fromstring(xml_texto)
    ide = root.find(".//nfe:ide", _XML_NS)
    emit = root.find(".//nfe:emit", _XML_NS)

    if ide is None:
        return {}

    data_emissao, hora_emissao = _separar_data_hora(
        ide.findtext("nfe:dhEmi", default="", namespaces=_XML_NS)
    )
    data_saida, hora_saida = _separar_data_hora(
        ide.findtext("nfe:dhSaiEnt", default="", namespaces=_XML_NS)
    )

    return {
        "data_emissao": data_emissao,
        "hora_emissao": hora_emissao,
        "data_saida": data_saida,
        "hora_saida": hora_saida,
        "natureza_operacao": _texto(
            ide.findtext("nfe:natOp", default="", namespaces=_XML_NS)
        ),
        "codigo_regime_tributario": _REGIME_TRIBUTARIO_MAP.get(
            _texto(emit.findtext("nfe:CRT", default="", namespaces=_XML_NS)) or "",
        ),
        "finalidade": _FINALIDADE_MAP.get(
            _texto(ide.findtext("nfe:finNFe", default="", namespaces=_XML_NS)) or "",
        ),
        "indicador_presenca": _INDICADOR_PRESENCA_MAP.get(
            _texto(ide.findtext("nfe:indPres", default="", namespaces=_XML_NS)) or "",
        ),
    }


def _consultar_campos_fiscais_no_xml(xml_url: str | None) -> dict:
    if not _texto(xml_url):
        return {}
    response = requests.get(xml_url, timeout=20)
    response.raise_for_status()
    return _extrair_campos_fiscais_do_xml(response.text)


def _enriquecer_detalhe_com_xml_link(item: dict, detalhe: dict) -> None:
    xml_url = _texto(
        _primeiro_preenchido(item.get("xml"), item.get("urlXml"), item.get("xmlUrl"))
    )
    if not xml_url:
        return

    try:
        campos_xml = _consultar_campos_fiscais_no_xml(xml_url)
    except Exception as exc:
        logger.warning("consultar_nfe", f"Falha ao enriquecer NF via XML: {exc}")
        return

    for campo in ("data_emissao", "hora_emissao", "data_saida", "hora_saida"):
        if campos_xml.get(campo):
            detalhe[campo] = campos_xml[campo]

    if campos_xml.get("natureza_operacao") and (
        not detalhe.get("natureza_operacao")
        or str(detalhe.get("natureza_operacao", "")).startswith("ID ")
    ):
        detalhe["natureza_operacao"] = campos_xml["natureza_operacao"]

    for campo in ("codigo_regime_tributario", "finalidade", "indicador_presenca"):
        if campos_xml.get(campo) and not detalhe.get(campo):
            detalhe[campo] = campos_xml[campo]
