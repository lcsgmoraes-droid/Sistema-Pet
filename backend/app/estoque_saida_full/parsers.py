"""Parsers de PDF e XML para preencher a baixa de estoque FULL."""

from collections import defaultdict
from typing import List, Optional
import unicodedata
import xml.etree.ElementTree as ET

from fastapi import HTTPException


NFE_NAMESPACE = "http" + "://www.portalfiscal.inf.br/nfe"
SKU_ROTULOS_EXPLICITOS = ("MSKU", "SKU", "CODIGO")
QTD_ROTULOS_EXPLICITOS = ("QTD", "QUANTIDADE", "UNIDADES")
UNIDADES_DANFE = {"UN", "UND", "UNID", "PC", "PCA", "PCT", "CX", "KG"}


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


def _extrair_sku_por_rotulo(
    linha: str, rotulos=SKU_ROTULOS_EXPLICITOS
) -> Optional[str]:
    for rotulo in rotulos:
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


def _adicionar_item(
    itens_por_sku, sku: Optional[str], quantidade: Optional[str]
) -> None:
    if not sku or not quantidade:
        return

    try:
        qtd = _to_float_br(quantidade)
    except (TypeError, ValueError):
        return

    if qtd > 0:
        itens_por_sku[sku] += qtd


def _itens_dict(itens_por_sku) -> List[dict]:
    return [
        {"sku": sku, "quantidade": quantidade}
        for sku, quantidade in itens_por_sku.items()
    ]


def _quantidade_antes_de_rotulo(linha: str, rotulo: str) -> Optional[str]:
    partes = linha.split()
    for indice, parte in enumerate(partes):
        if _texto_busca_sem_acento(parte).strip(".:|") != rotulo:
            continue
        if indice == 0:
            return None

        candidato = partes[indice - 1].strip(".:;|()[]")
        quantidade = _consumir_numero_quantidade(candidato)
        if quantidade == candidato:
            return quantidade
    return None


def _extrair_sku_explicito(linha: str) -> Optional[str]:
    return _extrair_sku_por_rotulo(linha)


def _extrair_itens_mercado_livre_pdf(texto: str) -> List[dict]:
    linhas = [(linha or "").strip() for linha in texto.splitlines()]
    blocos = []
    bloco_atual = []

    for linha in linhas:
        if "DIGO ML" in _texto_busca_sem_acento(linha):
            if bloco_atual:
                blocos.append(bloco_atual)
            bloco_atual = [linha]
        elif bloco_atual:
            bloco_atual.append(linha)
    if bloco_atual:
        blocos.append(bloco_atual)

    itens_por_sku = defaultdict(float)
    for bloco in blocos:
        sku = None
        for linha in bloco:
            sku = _extrair_sku_por_rotulo(linha, ("SKU",))
            if sku:
                break
        quantidade = next(
            (
                _quantidade_antes_de_rotulo(linha, "ETIQUETAGEM")
                for linha in bloco
                if _quantidade_antes_de_rotulo(linha, "ETIQUETAGEM")
            ),
            None,
        )
        _adicionar_item(itens_por_sku, sku, quantidade)

    return _itens_dict(itens_por_sku)


def _extrair_itens_danfe_pdf(texto: str) -> List[dict]:
    dentro_dos_itens = False
    itens_por_sku = defaultdict(float)

    for raw_line in texto.splitlines():
        linha = (raw_line or "").strip()
        linha_busca = _texto_busca_sem_acento(linha)
        if "DADOS DO PRODUTO / SERVI" in linha_busca:
            dentro_dos_itens = True
            continue
        if dentro_dos_itens and (
            "LCULO DO ISSQN" in linha_busca or "DADOS ADICIONAIS" in linha_busca
        ):
            break
        if not dentro_dos_itens or not linha:
            continue

        partes = linha.split()
        sku = partes[0].strip("|:;") if partes else ""
        if (
            len(sku) < 3
            or not any(char.isdigit() for char in sku)
            or not all(_char_sku_valido(char) for char in sku)
        ):
            continue

        for indice in range(len(partes) - 2, 0, -1):
            parte = partes[indice]
            unidade = _texto_busca_sem_acento(parte).strip(".:;|()[]")
            if unidade not in UNIDADES_DANFE:
                continue
            candidato = partes[indice + 1].strip(".:;|()[]")
            quantidade = _consumir_numero_quantidade(candidato)
            if quantidade == candidato:
                _adicionar_item(itens_por_sku, sku, quantidade)
                break

    return _itens_dict(itens_por_sku)


def _extrair_itens_amazon_pdf(texto: str) -> List[dict]:
    itens_por_sku = defaultdict(float)
    sku_pendente = None

    for raw_line in texto.splitlines():
        linha = (raw_line or "").strip()
        if not linha:
            continue

        sku = _extrair_sku_explicito(linha)
        quantidade = _extrair_quantidade_explicita(linha)
        if sku:
            sku_pendente = sku
        if sku_pendente and quantidade:
            _adicionar_item(itens_por_sku, sku_pendente, quantidade)
            sku_pendente = None

    return _itens_dict(itens_por_sku)


def _extrair_itens_full_pdf(texto: str) -> List[dict]:
    texto_busca = _texto_busca_sem_acento(texto)
    if "DIGO ML" in texto_busca and "PRODUTOS DO ENVIO" in texto_busca:
        itens = _extrair_itens_mercado_livre_pdf(texto)
        if itens:
            return itens

    if "DANFE" in texto_busca and "DADOS DO PRODUTO / SERVI" in texto_busca:
        itens = _extrair_itens_danfe_pdf(texto)
        if itens:
            return itens

    if "MSKU" in texto_busca and ("AMAZON" in texto_busca or "FBA" in texto_busca):
        itens = _extrair_itens_amazon_pdf(texto)
        if itens:
            return itens

    itens_por_sku = defaultdict(float)

    for raw_line in texto.splitlines():
        linha = (raw_line or "").strip()
        if not linha:
            continue

        sku = _extrair_sku_explicito(linha)
        quantidade = _extrair_quantidade_explicita(linha)
        if sku and quantidade:
            _adicionar_item(itens_por_sku, sku, quantidade)
            continue

        linha_item = _extrair_sku_quantidade_linha(linha)
        if linha_item:
            sku, quantidade = linha_item
            _adicionar_item(itens_por_sku, sku, quantidade)

    return _itens_dict(itens_por_sku)


def _extrair_numero_frete_mercado_livre(texto: str) -> Optional[str]:
    for linha in texto.splitlines():
        posicao = _posicao_valor_apos_rotulo(linha, "FRETE")
        if posicao is None:
            continue
        numero = _consumir_numero_quantidade(linha, posicao)
        if numero:
            return numero.split(".", 1)[0].split(",", 1)[0]
    return None


def _extrair_numero_danfe(texto: str) -> Optional[str]:
    for linha in texto.splitlines()[:30]:
        for parte in linha.split():
            candidato = parte.strip("Nnº°�:;|()[]")
            if candidato.count(".") < 2:
                continue
            digitos = "".join(char for char in candidato if char.isdigit())
            if len(digitos) >= 5:
                return digitos.lstrip("0") or "0"
    return None


def _extrair_id_remessa_amazon(texto: str) -> Optional[str]:
    for linha in texto.splitlines():
        for parte in linha.split():
            candidato = parte.strip("#:;|()[]").upper()
            if (
                candidato.startswith("FBA")
                and len(candidato) >= 8
                and candidato.isalnum()
            ):
                return candidato
    return None


def _parse_saida_full_pdf(texto: str) -> dict:
    texto_busca = _texto_busca_sem_acento(texto)
    itens = _extrair_itens_full_pdf(texto)
    tipo_documento = "pdf"
    numero_documento = None
    plataforma_sugerida = None

    if "DIGO ML" in texto_busca and "PRODUTOS DO ENVIO" in texto_busca:
        numero_frete = _extrair_numero_frete_mercado_livre(texto)
        numero_documento = f"ML-FRETE-{numero_frete}" if numero_frete else None
        tipo_documento = "mercado_livre_inbound"
        plataforma_sugerida = "mercado_livre"
    elif "DANFE" in texto_busca and "DADOS DO PRODUTO / SERVI" in texto_busca:
        numero_documento = _extrair_numero_danfe(texto)
        tipo_documento = "danfe"
        if "EBAZAR.COM.BR" in texto_busca or "MERCADO LIVRE" in texto_busca:
            plataforma_sugerida = "mercado_livre"
        elif "SHOPEE" in texto_busca:
            plataforma_sugerida = "shopee"
        elif "AMAZON" in texto_busca:
            plataforma_sugerida = "amazon"
    elif "MSKU" in texto_busca and ("AMAZON" in texto_busca or "FBA" in texto_busca):
        numero_documento = _extrair_id_remessa_amazon(texto)
        tipo_documento = "amazon_inbound"
        plataforma_sugerida = "amazon"
    elif "SHOPEE" in texto_busca:
        tipo_documento = "shopee_inbound"
        plataforma_sugerida = "shopee"

    return {
        "numero_documento": numero_documento,
        # Alias temporario para manter consumidores antigos compativeis.
        "numero_nf": numero_documento,
        "tipo_documento": tipo_documento,
        "plataforma_sugerida": plataforma_sugerida,
        "total_itens": len(itens),
        "total_unidades": sum(float(item["quantidade"]) for item in itens),
        "itens": itens,
    }


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
