"""Geracao dos PDFs oficiais de orcamentos das empresas do grupo."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from html import escape
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _fontes() -> tuple[str, str]:
    diretorio = Path(__file__).resolve().parent / "fonts"
    regular = diretorio / "Vera.ttf"
    negrito = diretorio / "VeraBd.ttf"
    if regular.exists() and negrito.exists():
        if "OrcamentoSans" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont("OrcamentoSans", str(regular)))
            pdfmetrics.registerFont(TTFont("OrcamentoSans-Bold", str(negrito)))
        return "OrcamentoSans", "OrcamentoSans-Bold"
    return "Helvetica", "Helvetica-Bold"


FONT, FONT_BOLD = _fontes()


def _brl(value) -> str:
    numero = Decimal(str(value or 0)).quantize(Decimal("0.01"))
    formatado = f"{numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatado}"


def _quantidade(value) -> str:
    numero = Decimal(str(value or 0))
    texto = f"{numero:,.3f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return texto.rstrip("0").rstrip(",")


def _linha_endereco(empresa: dict) -> str:
    endereco = " ".join(
        parte for parte in [empresa.get("endereco"), empresa.get("numero")] if parte
    )
    localidade = " - ".join(
        parte for parte in [empresa.get("cidade"), empresa.get("uf")] if parte
    )
    partes = [
        parte
        for parte in [
            endereco,
            empresa.get("complemento"),
            empresa.get("bairro"),
            localidade,
            empresa.get("cep"),
        ]
        if parte
    ]
    return " · ".join(partes)


def _adicionar_cotacao(story: list, orcamento, cotacao, estilos) -> None:
    empresa = cotacao.empresa_snapshot or {}
    nome = empresa.get("nome") or empresa.get("razao_social") or "Empresa"
    razao = empresa.get("razao_social")
    story.append(Paragraph(escape(nome), estilos["empresa"]))
    if razao and razao != nome:
        story.append(Paragraph(escape(razao), estilos["empresa_detalhe"]))

    identificacao = []
    if empresa.get("cnpj"):
        identificacao.append(f"CNPJ: {empresa['cnpj']}")
    if empresa.get("inscricao_estadual"):
        identificacao.append(f"IE: {empresa['inscricao_estadual']}")
    if identificacao:
        story.append(
            Paragraph(escape(" · ".join(identificacao)), estilos["empresa_detalhe"])
        )
    endereco = _linha_endereco(empresa)
    if endereco:
        story.append(Paragraph(escape(endereco), estilos["empresa_detalhe"]))
    contatos = " · ".join(
        parte for parte in [empresa.get("telefone"), empresa.get("email")] if parte
    )
    if contatos:
        story.append(Paragraph(escape(contatos), estilos["empresa_detalhe"]))

    story.append(Spacer(1, 7 * mm))
    story.append(Paragraph("ORÇAMENTO", estilos["titulo"]))
    validade_ate = orcamento.data_emissao + timedelta(days=orcamento.validade_dias)
    meta = [
        ["Número", orcamento.numero or str(orcamento.id)],
        ["Emissão", orcamento.data_emissao.strftime("%d/%m/%Y")],
        ["Válido até", validade_ate.strftime("%d/%m/%Y")],
    ]
    meta_table = Table(meta, colWidths=[30 * mm, 55 * mm], hAlign="RIGHT")
    meta_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), FONT),
                ("FONTNAME", (0, 0), (0, -1), FONT_BOLD),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#475569")),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 4 * mm))

    if orcamento.destinatario:
        story.append(
            Paragraph(
                f"<b>Destinatário:</b> {escape(orcamento.destinatario)}",
                estilos["texto"],
            )
        )
        story.append(Spacer(1, 3 * mm))

    dados = [["Item", "Qtd.", "Un.", "Valor unitário", "Total"]]
    for item in cotacao.itens_snapshot or []:
        dados.append(
            [
                Paragraph(escape(str(item.get("descricao") or "")), estilos["celula"]),
                _quantidade(item.get("quantidade")),
                item.get("unidade") or "-",
                _brl(item.get("preco_unitario")),
                _brl(item.get("preco_total")),
            ]
        )
    tabela = Table(
        dados,
        colWidths=[79 * mm, 18 * mm, 15 * mm, 31 * mm, 31 * mm],
        repeatRows=1,
    )
    tabela.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f766e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
                ("FONTNAME", (0, 1), (-1, -1), FONT),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#f8fafc")],
                ),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(tabela)
    story.append(Spacer(1, 4 * mm))
    total_table = Table(
        [["TOTAL DO ORÇAMENTO", _brl(cotacao.total)]],
        colWidths=[115 * mm, 59 * mm],
        hAlign="RIGHT",
    )
    total_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ecfdf5")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#065f46")),
                ("FONTNAME", (0, 0), (-1, -1), FONT_BOLD),
                ("FONTSIZE", (0, 0), (-1, -1), 11),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#6ee7b7")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(total_table)

    if orcamento.observacoes:
        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph("Observações", estilos["subtitulo"]))
        story.append(
            Paragraph(
                escape(orcamento.observacoes).replace("\n", "<br/>"),
                estilos["texto"],
            )
        )

    story.append(Spacer(1, 18 * mm))
    assinatura = Table(
        [["", ""], ["Responsável pela empresa", "Assinatura / data"]],
        colWidths=[75 * mm, 75 * mm],
        hAlign="CENTER",
    )
    assinatura.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (0, 1), (-1, 1), 0.6, colors.HexColor("#64748b")),
                ("FONTNAME", (0, 1), (-1, 1), FONT),
                ("FONTSIZE", (0, 1), (-1, 1), 8),
                ("TEXTCOLOR", (0, 1), (-1, 1), colors.HexColor("#64748b")),
                ("ALIGN", (0, 1), (-1, 1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8 * mm),
            ]
        )
    )
    story.append(assinatura)


def _desenhar_rodape(canvas, doc) -> None:
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#cbd5e1"))
    canvas.setLineWidth(0.4)
    canvas.line(doc.leftMargin, 10 * mm, A4[0] - doc.rightMargin, 10 * mm)
    canvas.setFont(FONT, 7.5)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawString(doc.leftMargin, 6.5 * mm, "Documento gerado pelo CorePet")
    canvas.drawRightString(
        A4[0] - doc.rightMargin,
        6.5 * mm,
        f"Página {canvas.getPageNumber()}",
    )
    canvas.restoreState()


def gerar_pdf_orcamentos(orcamento, cotacoes: list) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"Orcamentos {orcamento.numero or orcamento.id}",
        author="CorePet",
    )
    styles = getSampleStyleSheet()
    estilos = {
        "empresa": ParagraphStyle(
            "Empresa",
            parent=styles["Heading1"],
            fontName=FONT_BOLD,
            fontSize=15,
            leading=18,
            textColor=colors.HexColor("#0f172a"),
            alignment=TA_LEFT,
            spaceAfter=2,
        ),
        "empresa_detalhe": ParagraphStyle(
            "EmpresaDetalhe",
            parent=styles["Normal"],
            fontName=FONT,
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#475569"),
        ),
        "titulo": ParagraphStyle(
            "Titulo",
            parent=styles["Heading1"],
            fontName=FONT_BOLD,
            fontSize=20,
            leading=24,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#0f766e"),
            spaceAfter=4,
        ),
        "subtitulo": ParagraphStyle(
            "Subtitulo",
            parent=styles["Heading2"],
            fontName=FONT_BOLD,
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#334155"),
        ),
        "texto": ParagraphStyle(
            "Texto",
            parent=styles["Normal"],
            fontName=FONT,
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#334155"),
        ),
        "celula": ParagraphStyle(
            "Celula",
            parent=styles["Normal"],
            fontName=FONT,
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#1e293b"),
        ),
    }
    story = []
    for indice, cotacao in enumerate(cotacoes):
        if indice:
            story.append(PageBreak())
        _adicionar_cotacao(story, orcamento, cotacao, estilos)
    doc.build(story, onFirstPage=_desenhar_rodape, onLaterPages=_desenhar_rodape)
    return buffer.getvalue()
