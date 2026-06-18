from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from io import BytesIO
import re
from typing import Optional
from xml.etree import ElementTree as ET

import pdfplumber


NFE_NAMESPACE = "http://www.portalfiscal.inf.br/nfe"


@dataclass(frozen=True)
class PDFEntradaFornecedor:
    id: int
    nome: str
    cnpj: str = ""


@dataclass(frozen=True)
class PDFEntradaItem:
    numero_item: int
    codigo: str
    descricao: str
    quantidade: float
    valor_unitario: float
    valor_total: float
    unidade: str = "UN"


@dataclass(frozen=True)
class PDFEntradaDuplicata:
    numero: str
    vencimento: date
    valor: float


@dataclass(frozen=True)
class PDFEntradaPedido:
    numero_pedido: str
    data_emissao: date
    valor_total: float
    valor_produtos: float
    peso_total_kg: Optional[float] = None
    itens: list[PDFEntradaItem] = field(default_factory=list)
    duplicatas: list[PDFEntradaDuplicata] = field(default_factory=list)


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extracts text from a digital PDF file."""
    if not pdf_bytes:
        raise ValueError("PDF vazio")

    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        pages_text = [page.extract_text(x_tolerance=1, y_tolerance=3) or "" for page in pdf.pages]

    text = "\n".join(page_text.strip() for page_text in pages_text if page_text.strip())
    if not text.strip():
        raise ValueError("Nao foi possivel ler texto do PDF. Envie um PDF digital, nao escaneado.")
    return text


def parse_pedido_pdf_text(text: str) -> PDFEntradaPedido:
    normalized = _normalizar_texto(text)
    numero_pedido = _extrair_numero_pedido(normalized)
    data_emissao = _extrair_data_emissao(normalized)
    itens = _extrair_itens(normalized)
    if not itens:
        raise ValueError("Nenhum item foi identificado no PDF")

    valor_total = _extrair_valor_total(normalized) or sum(item.valor_total for item in itens)
    peso_total = _extrair_peso_total(normalized)
    duplicatas = _extrair_duplicatas(normalized)

    return PDFEntradaPedido(
        numero_pedido=numero_pedido,
        data_emissao=data_emissao,
        valor_total=round(float(valor_total), 2),
        valor_produtos=round(float(sum(item.valor_total for item in itens)), 2),
        peso_total_kg=peso_total,
        itens=itens,
        duplicatas=duplicatas,
    )


def build_pdf_synthetic_nfe_xml(
    pedido: PDFEntradaPedido,
    fornecedor: PDFEntradaFornecedor,
    tenant_id: int,
) -> str:
    """Builds a minimal NF-e-shaped XML so the existing entry flow can be reused."""
    ET.register_namespace("", NFE_NAMESPACE)
    ns = f"{{{NFE_NAMESPACE}}}"
    chave = _gerar_chave_pdf(pedido, fornecedor, tenant_id)
    cnpj = _somente_digitos(fornecedor.cnpj) or "00000000000000"

    nfe_proc = ET.Element(f"{ns}nfeProc")
    nfe = ET.SubElement(nfe_proc, f"{ns}NFe")
    inf_nfe = ET.SubElement(nfe, f"{ns}infNFe", {"Id": f"NFe{chave}", "versao": "4.00"})

    ide = ET.SubElement(inf_nfe, f"{ns}ide")
    _sub(ide, ns, "cUF", "35")
    _sub(ide, ns, "natOp", "Entrada por PDF")
    _sub(ide, ns, "mod", "55")
    _sub(ide, ns, "serie", "PDF")
    _sub(ide, ns, "nNF", pedido.numero_pedido[:20])
    _sub(ide, ns, "dhEmi", f"{pedido.data_emissao.isoformat()}T00:00:00-03:00")
    _sub(ide, ns, "tpNF", "0")

    emit = ET.SubElement(inf_nfe, f"{ns}emit")
    _sub(emit, ns, "CNPJ", cnpj[:14].zfill(14))
    _sub(emit, ns, "xNome", fornecedor.nome or "Fornecedor PDF")
    _sub(emit, ns, "xFant", fornecedor.nome or "Fornecedor PDF")

    for item in pedido.itens:
        det = ET.SubElement(inf_nfe, f"{ns}det", {"nItem": str(item.numero_item)})
        prod = ET.SubElement(det, f"{ns}prod")
        _sub(prod, ns, "cProd", item.codigo)
        _sub(prod, ns, "cEAN", "")
        _sub(prod, ns, "xProd", item.descricao)
        _sub(prod, ns, "NCM", "")
        _sub(prod, ns, "CEST", "")
        _sub(prod, ns, "CFOP", "")
        _sub(prod, ns, "orig", "")
        _sub(prod, ns, "uCom", item.unidade or "UN")
        _sub(prod, ns, "qCom", _format_decimal(item.quantidade, places=4))
        _sub(prod, ns, "vUnCom", _format_decimal(item.valor_unitario, places=4))
        _sub(prod, ns, "vProd", _format_decimal(item.valor_total))
        _sub(prod, ns, "cEANTrib", "")
        _sub(prod, ns, "uTrib", item.unidade or "UN")
        _sub(prod, ns, "qTrib", _format_decimal(item.quantidade, places=4))
        _sub(prod, ns, "vUnTrib", _format_decimal(item.valor_unitario, places=4))

    total = ET.SubElement(inf_nfe, f"{ns}total")
    icms_tot = ET.SubElement(total, f"{ns}ICMSTot")
    _sub(icms_tot, ns, "vProd", _format_decimal(pedido.valor_produtos))
    _sub(icms_tot, ns, "vFrete", "0.00")
    _sub(icms_tot, ns, "vSeg", "0.00")
    _sub(icms_tot, ns, "vDesc", "0.00")
    _sub(icms_tot, ns, "vOutro", "0.00")
    _sub(icms_tot, ns, "vNF", _format_decimal(pedido.valor_total))

    if pedido.duplicatas:
        cobr = ET.SubElement(inf_nfe, f"{ns}cobr")
        for dup in pedido.duplicatas:
            dup_node = ET.SubElement(cobr, f"{ns}dup")
            _sub(dup_node, ns, "nDup", dup.numero)
            _sub(dup_node, ns, "dVenc", dup.vencimento.isoformat())
            _sub(dup_node, ns, "vDup", _format_decimal(dup.valor))

    return ET.tostring(nfe_proc, encoding="unicode")


def _normalizar_texto(text: str) -> str:
    lines = []
    for raw_line in (text or "").replace("\r", "\n").split("\n"):
        line = re.sub(r"\s+", " ", raw_line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def _extrair_numero_pedido(text: str) -> str:
    match = re.search(r"CODIGO PRODUTO\s*\n\s*(\d{3,})", text, flags=re.IGNORECASE)
    if match:
        return match.group(1)

    match = re.search(
        r"\bPEDIDO\s*(?:N[ROº°\.]*|NUMERO)?\s*[:#-]?\s*(\d{1,})",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        return match.group(1)

    raise ValueError("Numero do pedido nao identificado no PDF")


def _extrair_data_emissao(text: str) -> date:
    match = re.search(r"\b(\d{2}/\d{2}/\d{4})", text)
    if not match:
        raise ValueError("Data do pedido nao identificada no PDF")
    return _parse_date(match.group(1))


def _extrair_itens(text: str) -> list[PDFEntradaItem]:
    for extractor in (
        _extrair_itens_romaneio,
        _extrair_itens_app_vendas_mobile,
    ):
        itens = extractor(text)
        if itens:
            return itens
    return []


def _extrair_itens_romaneio(text: str) -> list[PDFEntradaItem]:
    itens = []
    codigo_pattern = r"([A-Z0-9][A-Z0-9._/-]{2,})"
    valor_pattern = r"(\d{1,3}(?:\.\d{3})*,\d{2})"
    item_patterns = [
        re.compile(
            rf"^{codigo_pattern}\s+(.+?)\s+(\d+(?:[,.]\d+)?)\s+"
            rf"{valor_pattern}\s+{valor_pattern}([A-Za-z]{{1,6}})$",
            flags=re.IGNORECASE,
        ),
        re.compile(
            rf"^{codigo_pattern}\s+(.+)\s+([A-Za-z]{{1,6}})\s+(\d+(?:[,.]\d+)?)\s+"
            rf"{valor_pattern}\s+{valor_pattern}$",
            flags=re.IGNORECASE,
        ),
    ]

    for line in text.split("\n"):
        match = item_patterns[0].match(line)
        if match:
            codigo, descricao, quantidade, valor_unitario, valor_total, unidade = match.groups()
        else:
            match = item_patterns[1].match(line)
            if not match:
                continue
            codigo, descricao, unidade, quantidade, valor_unitario, valor_total = match.groups()

        itens.append(
            PDFEntradaItem(
                numero_item=len(itens) + 1,
                codigo=codigo,
                descricao=descricao.strip(),
                quantidade=float(_parse_decimal(quantidade)),
                valor_unitario=float(_parse_decimal(valor_unitario)),
                valor_total=float(_parse_decimal(valor_total)),
                unidade=unidade.upper(),
            )
        )

    return itens


def _extrair_itens_app_vendas_mobile(text: str) -> list[PDFEntradaItem]:
    itens = []
    valor_pattern = r"(\d{1,3}(?:\.\d{3})*,\d{2})"
    item_pattern = re.compile(
        rf"^([A-Z0-9][A-Z0-9._/-]*)\s+(.+?)\s+(\d+(?:[,.]\d+)?)\s+"
        rf"{valor_pattern}\s+{valor_pattern}$",
        flags=re.IGNORECASE,
    )

    parsing_items = False
    for line in text.split("\n"):
        upper_line = line.upper()
        if "CÓDIGO DESCRIÇÃO" in upper_line or "CODIGO DESCRICAO" in upper_line:
            parsing_items = True
            continue
        if parsing_items and (
            re.search(r"\b\d+\s+ITENS?\b", upper_line)
            or upper_line.startswith("DESCONTO ")
            or upper_line.startswith("VLR.FRETE")
            or "TOTAL:R$" in upper_line
            or "APP VENDAS" in upper_line
        ):
            break
        if not parsing_items:
            continue

        match = item_pattern.match(line)
        if not match:
            continue
        codigo, descricao, quantidade, valor_unitario, valor_total = match.groups()
        itens.append(
            PDFEntradaItem(
                numero_item=len(itens) + 1,
                codigo=codigo,
                descricao=descricao.strip(),
                quantidade=float(_parse_decimal(quantidade)),
                valor_unitario=float(_parse_decimal(valor_unitario)),
                valor_total=float(_parse_decimal(valor_total)),
                unidade="UN",
            )
        )

    return itens


def _extrair_valor_total(text: str) -> Optional[float]:
    match = re.search(r"VALOR TOTAL:\s*(\d{1,3}(?:\.\d{3})*,\d{2})", text, flags=re.IGNORECASE)
    if not match:
        match = re.search(r"\bTOTAL\s*:\s*R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2})", text, flags=re.IGNORECASE)
    if not match:
        return None
    return float(_parse_decimal(match.group(1)))


def _extrair_peso_total(text: str) -> Optional[float]:
    match = re.search(r"PESO TOTAL:\s*([\d.,]+)\s*Kg", text, flags=re.IGNORECASE)
    if not match:
        return None
    return float(_parse_decimal(match.group(1)))


def _extrair_duplicatas(text: str) -> list[PDFEntradaDuplicata]:
    lines = text.split("\n")
    pares = []
    vistos = set()

    for index, line in enumerate(lines):
        if "BOLETO" not in line.upper():
            continue

        linha_datas = re.sub(
            r"(\d{2}/\d{2}/\d{2})(?=\d{2}/\d{2})",
            r"\1 ",
            line,
        )
        datas = []
        for value in re.findall(r"\d{2}/\d{2}/(?:\d{4}|\d{2})(?!\d)", linha_datas):
            try:
                datas.append(_parse_date(value))
            except ValueError:
                continue

        linhas_valores = []
        for next_line in lines[index + 1 : index + 4]:
            upper_line = next_line.upper()
            if (
                upper_line.startswith("PEDIDO ")
                or upper_line.startswith("CODIGO PRODUTO")
                or upper_line.startswith("CLIENTE ")
                or "REPRESENTANTE" in upper_line
                or "VALOR TOTAL" in upper_line
                or "PESO TOTAL" in upper_line
            ):
                break
            linhas_valores.append(next_line)

        valores = [
            _parse_decimal(value)
            for value in re.findall(
                r"\d{1,3}(?:\.\d{3})*,\d{2}",
                "\n".join(linhas_valores),
            )
        ]

        for vencimento, valor in zip(datas, valores):
            chave = (vencimento, valor)
            if chave in vistos:
                continue
            vistos.add(chave)
            pares.append((vencimento, valor))

    for line in lines:
        match = re.match(
            r"^([A-Z0-9./-]+)\s+(\d{2}/\d{2}/(?:\d{4}|\d{2}))\s+(\d{1,3}(?:\.\d{3})*,\d{2})$",
            line,
            flags=re.IGNORECASE,
        )
        if not match:
            continue
        _, data_vencimento, valor_texto = match.groups()
        try:
            vencimento = _parse_date(data_vencimento)
            valor = _parse_decimal(valor_texto)
        except ValueError:
            continue
        chave = (vencimento, valor)
        if chave in vistos:
            continue
        vistos.add(chave)
        pares.append((vencimento, valor))

    pares = sorted(pares, key=lambda pair: pair[0])

    duplicatas = []
    for idx, (vencimento, valor) in enumerate(pares, start=1):
        duplicatas.append(
            PDFEntradaDuplicata(
                numero=f"PDF-{idx:03d}",
                vencimento=vencimento,
                valor=float(valor),
            )
        )
    return duplicatas


def _parse_decimal(value: str) -> Decimal:
    normalized = str(value).strip().replace(".", "").replace(",", ".")
    try:
        return Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError(f"Valor numerico invalido no PDF: {value}") from exc


def _parse_date(value: str) -> date:
    day, month, year = value.split("/")
    if len(year) == 2:
        year = f"20{year}"
    return date(int(year), int(month), int(day))


def _format_decimal(value: float | Decimal, places: int = 2) -> str:
    quantizer = Decimal("1").scaleb(-places)
    decimal_value = Decimal(str(value)).quantize(quantizer)
    return f"{decimal_value:.{places}f}"


def _gerar_chave_pdf(
    pedido: PDFEntradaPedido,
    fornecedor: PDFEntradaFornecedor,
    tenant_id: int,
) -> str:
    itens_hash = "|".join(
        f"{item.codigo}:{item.quantidade}:{item.valor_unitario}:{item.valor_total}"
        for item in pedido.itens
    )
    raw = (
        f"{tenant_id}|{fornecedor.id}|{pedido.numero_pedido}|"
        f"{pedido.data_emissao.isoformat()}|{pedido.valor_total}|{itens_hash}"
    )
    digest_int = int(sha256(raw.encode("utf-8")).hexdigest(), 16) % (10**44)
    return f"{digest_int:044d}"


def _somente_digitos(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def _sub(parent: ET.Element, ns: str, tag: str, value: str) -> ET.Element:
    child = ET.SubElement(parent, f"{ns}{tag}")
    child.text = value
    return child
