"""DANFE NFC-e em PDF a partir do XML autorizado, sem recalcular a nota."""

from decimal import Decimal
from datetime import datetime
from html import escape
from io import BytesIO
import re

from defusedxml import ElementTree as ET
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

NS = {
    "n": "http://www.portalfiscal.inf.br/nfe"  # NOSONAR: namespace XML, sem acesso HTTP.
}
XML_NOME = "n:xNome"
PAGAMENTOS = {
    "01": "Dinheiro",
    "02": "Cheque",
    "03": "Cartão de crédito",
    "04": "Cartão de débito",
    "05": "Crédito loja",
    "10": "Vale alimentação",
    "11": "Vale refeição",
    "15": "Boleto bancário",
    "17": "PIX",
    "18": "Transferência bancária",
    "19": "Programa de fidelidade",
    "90": "Sem pagamento",
    "99": "Outros",
}


def texto(node, path, default=""):
    return (
        node.findtext(path, default=default, namespaces=NS)
        if node is not None
        else default
    )


def numero_br(value, casas=2):
    return (
        f"{Decimal(value or '0'):,.{casas}f}".replace(",", "_")
        .replace(".", ",")
        .replace("_", ".")
    )


def data_br(value):
    try:
        return datetime.fromisoformat(value).strftime("%d/%m/%Y %H:%M:%S")
    except ValueError:
        return value


def validar_xml_nota(xml, chave, modelo):
    root = ET.fromstring(xml)
    info = root.find(".//n:infNFe", NS)
    if (
        info is None
        or info.get("Id") != f"NFe{chave}"
        or texto(info, "n:ide/n:mod") != str(modelo)
    ):
        raise ValueError("O XML recebido não corresponde à nota solicitada.")
    return root


def _adicionar_totais_pagamentos(info, total, quantidade_itens, adicionar):
    adicionar(f"Quantidade total de itens: {quantidade_itens}")
    adicionar(f"Valor total R$: {numero_br(texto(total, 'n:vProd'))}")
    for tag, label in [
        ("vDesc", "Descontos"),
        ("vFrete", "Frete"),
        ("vSeg", "Seguro"),
        ("vOutro", "Outras despesas"),
    ]:
        if Decimal(texto(total, f"n:{tag}", "0")):
            adicionar(f"{label} R$: {numero_br(texto(total, f'n:{tag}'))}")
    adicionar(f"VALOR A PAGAR R$: {numero_br(texto(total, 'n:vNF'))}", negrito=True)
    pagamentos = info.findall("n:pag/n:detPag", NS)
    for pagamento in pagamentos:
        forma = texto(pagamento, "n:xPag") or PAGAMENTOS.get(
            texto(pagamento, "n:tPag"), f"Pagamento {texto(pagamento, 'n:tPag')}"
        )
        adicionar(f"{forma}: R$ {numero_br(texto(pagamento, 'n:vPag'))}")
    troco = texto(info, "n:pag/n:vTroco", "0")
    if Decimal(troco):
        adicionar(f"Troco R$: {numero_br(troco)}")


def _adicionar_consumidor(info, adicionar):
    dest = info.find("n:dest", NS)
    documento = (
        texto(dest, "n:CPF") or texto(dest, "n:CNPJ") or texto(dest, "n:idEstrangeiro")
    )
    adicionar("CONSUMIDOR", True, True)
    adicionar(
        f"CPF/CNPJ: {documento}" if documento else "Consumidor não identificado", True
    )
    if texto(dest, XML_NOME):
        adicionar(texto(dest, XML_NOME), True)
    if dest is not None:
        end_dest = dest.find("n:enderDest", NS)
        if end_dest is not None:
            adicionar(
                ", ".join(
                    filter(
                        None,
                        [
                            texto(end_dest, f"n:{tag}")
                            for tag in ["xLgr", "nro", "xBairro", "xMun", "UF"]
                        ],
                    )
                ),
                True,
            )


def gerar_danfe_nfce(xml: bytes, chave: str) -> bytes:
    root = validar_xml_nota(xml, chave, 65)
    info = root.find(".//n:infNFe", NS)
    protocolo = root.find(".//n:protNFe/n:infProt", NS)
    if (
        texto(protocolo, "n:cStat") not in {"100", "150"}
        or texto(protocolo, "n:chNFe") != chave
    ):
        raise ValueError("A NFC-e ainda não possui protocolo de autorização válido.")
    qr = texto(root, ".//n:infNFeSupl/n:qrCode")
    if not qr:
        raise ValueError("O XML da NFC-e não contém o QR Code de consulta.")

    largura, margem = 80 * mm, 4 * mm
    util = largura - 2 * margem
    normal = ParagraphStyle(
        "normal", fontName="Helvetica", fontSize=8, leading=10, spaceAfter=3
    )
    centro = ParagraphStyle("centro", parent=normal, alignment=1)
    linhas = []

    def adicionar(value, central=False, negrito=False):
        conteudo = escape(str(value or "")).replace("\n", "<br/>")
        if negrito:
            conteudo = f"<b>{conteudo}</b>"
        paragrafo = Paragraph(conteudo, centro if central else normal)
        _, altura = paragrafo.wrap(util, 10000)
        linhas.append((paragrafo, altura + 4))

    emit = info.find("n:emit", NS)
    endereco = emit.find("n:enderEmit", NS)
    adicionar(texto(emit, XML_NOME), True, True)
    adicionar(
        f"CNPJ/CPF: {texto(emit, 'n:CNPJ') or texto(emit, 'n:CPF')}  IE: {texto(emit, 'n:IE')}",
        True,
    )
    adicionar(
        ", ".join(
            filter(
                None,
                [
                    texto(endereco, "n:xLgr"),
                    texto(endereco, "n:nro"),
                    texto(endereco, "n:xBairro"),
                    texto(endereco, "n:xMun"),
                    texto(endereco, "n:UF"),
                ],
            )
        ),
        True,
    )
    adicionar("DOCUMENTO AUXILIAR DA NOTA FISCAL DE CONSUMIDOR ELETRÔNICA", True, True)
    if texto(info, "n:ide/n:tpAmb") != "1":
        adicionar("EMITIDA EM AMBIENTE DE HOMOLOGAÇÃO - SEM VALOR FISCAL", True, True)
    adicionar(
        "Código / Descrição / Quantidade / UN / V. unit. / V. total", negrito=True
    )
    itens = info.findall("n:det/n:prod", NS)
    for item in itens:
        adicionar(f"{texto(item, 'n:cProd')} - {texto(item, 'n:xProd')}")
        quantidade = numero_br(texto(item, "n:qCom"), 4).rstrip("0").rstrip(",")
        unitario = Decimal(texto(item, "n:vUnCom", "0"))
        casas = max(2, -unitario.normalize().as_tuple().exponent)
        adicionar(
            f"{quantidade} {texto(item, 'n:uCom')} x {numero_br(unitario, casas)} = R$ {numero_br(texto(item, 'n:vProd'))}"
        )
    total = info.find("n:total/n:ICMSTot", NS)
    _adicionar_totais_pagamentos(info, total, len(itens), adicionar)
    consulta = texto(root, ".//n:infNFeSupl/n:urlChave")
    adicionar("Consulte pela chave de acesso em:", True)
    adicionar(consulta, True)
    adicionar(" ".join(chave[i : i + 4] for i in range(0, 44, 4)), True)
    _adicionar_consumidor(info, adicionar)
    adicionar(
        f"NFC-e nº {texto(info, 'n:ide/n:nNF')}  Série {texto(info, 'n:ide/n:serie')}",
        True,
        True,
    )
    adicionar(f"Emissão: {data_br(texto(info, 'n:ide/n:dhEmi'))}", True)
    adicionar(f"Protocolo de autorização: {texto(protocolo, 'n:nProt')}", True)
    adicionar(f"Data de autorização: {data_br(texto(protocolo, 'n:dhRecbto'))}", True)
    adicional = texto(info, "n:infAdic/n:infCpl")
    if adicional:
        adicionar(re.sub(r"<br\s*/?>", "\n", adicional, flags=re.IGNORECASE))
    tributos = texto(total, "n:vTotTrib", "0")
    if Decimal(tributos):
        adicionar(
            f"Tributos totais incidentes (Lei Federal 12.741/2012): R$ {numero_br(tributos)}"
        )

    tamanho_qr = 40 * mm
    altura_total = sum(h for _, h in linhas) + tamanho_qr + 4 * margem
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(largura, altura_total))
    pdf.setTitle(f"DANFE NFC-e {texto(info, 'n:ide/n:nNF')}")
    y = altura_total - margem
    for paragrafo, altura in linhas:
        y -= altura
        paragrafo.drawOn(pdf, margem, y)
    widget = QrCodeWidget(qr, barBorder=4)
    x1, y1, x2, y2 = widget.getBounds()
    desenho = Drawing(
        tamanho_qr,
        tamanho_qr,
        transform=[tamanho_qr / (x2 - x1), 0, 0, tamanho_qr / (y2 - y1), 0, 0],
    )
    desenho.add(widget)
    renderPDF.draw(desenho, pdf, (largura - tamanho_qr) / 2, margem)
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()
