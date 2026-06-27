"""Geracao de PDF e HTML para pendencias de compras."""

from io import BytesIO
from typing import Any
from xml.sax.saxutils import escape

from fastapi import HTTPException

from .compras_pendencias_models import CompraPendenciaFornecedor
from .compras_pendencias_utils import _formatar_moeda, _formatar_qtd


def _pdf_pendencia_bytes(pendencia: CompraPendenciaFornecedor) -> bytes:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError:
        raise HTTPException(
            status_code=500, detail="Biblioteca reportlab nao instalada."
        )

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, topMargin=14 * mm, bottomMargin=14 * mm
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title", parent=styles["Heading1"], fontSize=15, spaceAfter=8
    )
    small_style = ParagraphStyle(
        "Small", parent=styles["Normal"], fontSize=8, leading=10
    )

    def cell(valor: Any) -> Paragraph:
        return Paragraph(escape(str(valor if valor is not None else "-")), small_style)

    elements = [
        Paragraph("PENDENCIA DE FORNECEDOR", title_style),
        Paragraph(escape(pendencia.titulo or ""), styles["Normal"]),
        Spacer(1, 6),
    ]

    info = [
        ["Codigo", pendencia.codigo or "-", "Status", pendencia.status],
        [
            "Fornecedor",
            pendencia.fornecedor_nome,
            "CNPJ",
            pendencia.fornecedor_cnpj or "-",
        ],
        ["NF", pendencia.numero_nota or "-", "Pedido", pendencia.numero_pedido or "-"],
        [
            "Criada em",
            pendencia.created_at.strftime("%d/%m/%Y %H:%M")
            if pendencia.created_at
            else "-",
            "Prazo",
            pendencia.prazo_previsto.strftime("%d/%m/%Y")
            if pendencia.prazo_previsto
            else "-",
        ],
    ]
    info_table = Table(
        [[cell(col) for col in row] for row in info],
        colWidths=[28 * mm, 62 * mm, 28 * mm, 62 * mm],
    )
    info_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F1F5F9")),
                ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#F1F5F9")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    elements.append(info_table)
    elements.append(Spacer(1, 10))

    item_rows = [
        ["Produto", "Qtd NF", "Recebida", "Faltante", "Avariada", "Valor div."]
    ]
    for item in pendencia.itens or []:
        item_rows.append(
            [
                item.descricao,
                _formatar_qtd(item.quantidade_nf),
                _formatar_qtd(item.quantidade_recebida),
                _formatar_qtd(item.quantidade_faltante),
                _formatar_qtd(item.quantidade_avariada),
                _formatar_moeda(item.valor_total_divergente),
            ]
        )
    item_table = Table(
        [[cell(col) for col in row] for row in item_rows],
        colWidths=[70 * mm, 22 * mm, 22 * mm, 22 * mm, 22 * mm, 28 * mm],
        repeatRows=1,
    )
    item_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elements.append(item_table)

    if pendencia.email_mensagem:
        elements.append(Spacer(1, 10))
        for linha in pendencia.email_mensagem.splitlines():
            elements.append(Paragraph(escape(linha or " "), small_style))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def _html_email_pendencia(pendencia: CompraPendenciaFornecedor, mensagem: str) -> str:
    linhas = "<br>".join(escape(linha) for linha in (mensagem or "").splitlines())
    return f"""
    <html>
      <body style="font-family:Arial,sans-serif;color:#0f172a;line-height:1.5;">
        <div style="max-width:680px;margin:0 auto;border:1px solid #e2e8f0;border-radius:10px;overflow:hidden;">
          <div style="background:#f8fafc;padding:18px 22px;border-bottom:1px solid #e2e8f0;">
            <div style="font-size:12px;color:#2563eb;font-weight:700;text-transform:uppercase;">Pendencia de fornecedor</div>
            <h1 style="font-size:20px;margin:6px 0 0;">{escape(pendencia.titulo or pendencia.codigo or "Pendencia")}</h1>
          </div>
          <div style="padding:22px;">
            <p><strong>NF:</strong> {escape(str(pendencia.numero_nota or "-"))}</p>
            <p><strong>Pedido:</strong> {escape(str(pendencia.numero_pedido or "-"))}</p>
            <p><strong>Fornecedor:</strong> {escape(str(pendencia.fornecedor_nome or "-"))}</p>
            <div style="margin-top:18px;padding-top:18px;border-top:1px solid #e2e8f0;">{linhas}</div>
            <p style="margin-top:22px;color:#64748b;font-size:12px;">
              O relatorio em PDF segue anexo para conferencia dos itens divergentes.
            </p>
          </div>
        </div>
      </body>
    </html>
    """
