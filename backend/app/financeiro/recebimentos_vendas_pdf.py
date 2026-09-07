"""PDF com o mesmo período, fontes e total da tela de recebimentos."""

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _brl(valor):
    return "R$ " + f"{valor:,.2f}".replace(",", "#").replace(".", ",").replace("#", ".")


def _data(valor):
    return "/".join(valor.split("-")[::-1])


def gerar_pdf_recebimentos(relatorio, canal=None):
    arquivo = BytesIO()
    doc = SimpleDocTemplate(
        arquivo,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )
    estilos = getSampleStyleSheet()
    corpo = estilos["BodyText"]
    corpo.fontSize = 8
    corpo.leading = 10

    def texto(valor):
        return Paragraph(escape(str(valor or "")), corpo)

    resumo = relatorio["resumo"]
    itens = [
        Paragraph("Recebimentos de vendas", estilos["Title"]),
        texto(
            f"Pela data do recebimento: {_data(relatorio['data_inicio'])} a {_data(relatorio['data_fim'])}. Canal: {canal or 'Todos os canais'}."
        ),
        texto(
            f"Recebimentos: {_brl(resumo['recebimentos'])} | Devoluções: {_brl(resumo['devolucoes'])} | Total: {_brl(resumo['total'])}"
        ),
        Spacer(1, 5 * mm),
    ]
    linhas = [
        [
            texto(t)
            for t in [
                "Recebimento",
                "Venda",
                "Data da venda",
                "Cliente",
                "Forma",
                "Movimento",
                "Valor",
            ]
        ]
    ]
    for mov in relatorio["movimentos"]:
        linhas.append(
            [
                texto(t)
                for t in [
                    _data(mov["data_recebimento"]),
                    mov["numero_venda"],
                    _data(mov["data_venda"]),
                    mov["cliente_nome"],
                    mov["forma_pagamento"],
                    "Devolução" if mov["tipo"] == "devolucao" else "Recebimento",
                    _brl(mov["valor"]),
                ]
            ]
        )
    if not relatorio["movimentos"]:
        itens.append(texto("Nenhum recebimento de venda neste período."))
    tabela = Table(
        linhas,
        colWidths=[25 * mm, 31 * mm, 25 * mm, 72 * mm, 46 * mm, 32 * mm, 42 * mm],
        repeatRows=1,
    )
    tabela.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6f4f1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#dddddd")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    itens.append(tabela)
    doc.build(itens)
    arquivo.seek(0)
    return arquivo
