"""Parsers de PDF e XML para preencher a baixa FULL por NF."""

from collections import defaultdict
from typing import List, Optional
import unicodedata
import xml.etree.ElementTree as ET

from fastapi import HTTPException


NFE_NAMESPACE = "http" + "://www.portalfiscal.inf.br/nfe"
SKU_ROTULOS_EXPLICITOS = ("SKU", "CODIGO")
QTD_ROTULOS_EXPLICITOS = ("QTD", "QUANTIDADE")


def _texto_busca_sem_acento(value: str) -> str:
    return "".join(
        char
        for char in unicodedata.normalize("NFD", value)
        if unicodedata.category(char) != "Mn"
    ).upper()


def _char_sku_valido(char: str) -> bool:
    return char.isascii() and (char.isalnum() or char in "._/-")


def _posicao_valor_apos_rotulo(linha: str, rotulo: str) -> Optional[int]:
    texto_busca = _texto_busca_sem_acento(linha)
    inicio = texto_busca.find(rotulo)

    while inicio >= 0:
        if inicio > 0 and texto_busca[inicio - 1].isalnum():
            inicio = texto_busca.find(rotulo, inicio + 1)
            continue

        posicao = inicio + len(rotulo)
        while posicao < len(linha) and linha[posicao].isspace():
            posicao += 1
        if posicao < len(linha) and linha[posicao] in ":#-":
            posicao += 1
        while posicao < len(linha) and linha[posicao].isspace():
            posicao += 1
        return posicao if posicao < len(linha) else None

    return None


def _extrair_sku_explicito(linha: str) -> Optional[str]:
    for rotulo in SKU_ROTULOS_EXPLICITOS:
        posicao = _posicao_valor_apos_rotulo(linha, rotulo)
        if posicao is None:
            continue

        inicio = posicao
        while posicao < len(linha) and _char_sku_valido(linha[posicao]):
            posicao += 1
        if posicao > inicio:
            return linha[inicio:posicao].strip()

    return None


def _consumir_numero_quantidade(value: str, posicao: int = 0) -> Optional[str]:
    if posicao >= len(value) or not value[posicao].isdigit():
        return None

    inicio = posicao
    while posicao < len(value) and value[posicao].isdigit():
        posicao += 1

    if posicao < len(value) and value[posicao] in ".,":
        separador = posicao
        posicao += 1
        if posicao < len(value) and value[posicao].isdigit():
            while posicao < len(value) and value[posicao].isdigit():
                posicao += 1
        else:
            posicao = separador

    return value[inicio:posicao]


def _extrair_quantidade_explicita(linha: str) -> Optional[str]:
    for rotulo in QTD_ROTULOS_EXPLICITOS:
        posicao = _posicao_valor_apos_rotulo(linha, rotulo)
        if posicao is None:
            continue

        quantidade = _consumir_numero_quantidade(linha, posicao)
        if quantidade:
            return quantidade

    return None


def _extrair_sku_quantidade_linha(linha: str) -> Optional[tuple[str, str]]:
    partes = linha.split()
    if len(partes) != 2:
        return None

    sku, quantidade_texto = partes
    if len(sku) < 3 or not all(_char_sku_valido(char) for char in sku):
        return None

    quantidade = _consumir_numero_quantidade(quantidade_texto)
    if quantidade != quantidade_texto:
        return None

    return sku, quantidade


def _to_float_br(value: str) -> float:
    return (
        float(value.replace(".", "").replace(",", "."))
        if "," in value
        else float(value)
    )


def _extrair_itens_full_pdf(texto: str) -> List[dict]:
    itens_por_sku = defaultdict(float)

    for raw_line in texto.splitlines():
        linha = (raw_line or "").strip()
        if not linha:
            continue

        sku = _extrair_sku_explicito(linha)
        quantidade = _extrair_quantidade_explicita(linha)
        if sku and quantidade:
            qtd = _to_float_br(quantidade)
            if qtd > 0:
                itens_por_sku[sku] += qtd
            continue

        linha_item = _extrair_sku_quantidade_linha(linha)
        if linha_item:
            sku, quantidade = linha_item
            qtd = _to_float_br(quantidade)
            if qtd > 0:
                itens_por_sku[sku] += qtd

    return [
        {"sku": sku, "quantidade": quantidade}
        for sku, quantidade in itens_por_sku.items()
    ]


def _xml_find_text(parent, path_ns: str, path_plain: str, ns: dict) -> Optional[str]:
    elem = parent.find(path_ns, ns)
    if elem is None:
        elem = parent.find(path_plain)
    if elem is None:
        return None
    return (elem.text or "").strip()


def _parse_saida_full_xml(xml_bytes: bytes) -> dict:
    root = ET.fromstring(xml_bytes)
    # Namespace XML oficial da NF-e; nao e usado para conexao de rede.
    ns = {"nfe": NFE_NAMESPACE}

    inf_nfe = root.find(".//nfe:infNFe", ns)
    if inf_nfe is None:
        inf_nfe = root.find(".//infNFe")
    if inf_nfe is None:
        raise HTTPException(
            status_code=400, detail="XML invalido: tag infNFe nao encontrada"
        )

    ide = inf_nfe.find("nfe:ide", ns)
    if ide is None:
        ide = inf_nfe.find("ide")
    if ide is None:
        raise HTTPException(
            status_code=400, detail="XML invalido: tag ide nao encontrada"
        )

    numero_nf = _xml_find_text(ide, "nfe:nNF", "nNF", ns)
    if not numero_nf:
        raise HTTPException(
            status_code=400, detail="Numero da NF nao encontrado no XML"
        )

    itens_por_sku = defaultdict(float)
    det_list = inf_nfe.findall(".//nfe:det", ns)
    if not det_list:
        det_list = inf_nfe.findall(".//det")

    for det in det_list:
        prod = det.find("nfe:prod", ns)
        if prod is None:
            prod = det.find("prod")
        if prod is None:
            continue

        sku = _xml_find_text(prod, "nfe:cProd", "cProd", ns)
        qcom = _xml_find_text(prod, "nfe:qCom", "qCom", ns)
        if not sku or not qcom:
            continue

        try:
            qtd = float(qcom.replace(",", "."))
        except ValueError:
            continue

        if qtd > 0:
            itens_por_sku[sku] += qtd

    itens = [
        {"sku": sku, "quantidade": quantidade}
        for sku, quantidade in itens_por_sku.items()
    ]

    if not itens:
        raise HTTPException(
            status_code=400,
            detail="Nenhum item valido (cProd + qCom) foi encontrado no XML",
        )

    return {
        "numero_nf": numero_nf,
        "total_itens": len(itens),
        "itens": itens,
    }
