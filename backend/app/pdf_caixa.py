"""
Módulo para geração de PDF de fechamento de caixa
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from datetime import datetime
from io import BytesIO


def gerar_pdf_fechamento_caixa(caixa_data: dict, movimentacoes: list) -> BytesIO:
    """
    Gera PDF do fechamento de caixa com todas as movimentações

    Args:
        caixa_data: Dados do caixa (id, numero_caixa, data_abertura, data_fechamento, saldos, etc)
        movimentacoes: Lista de movimentações do caixa

    Returns:
        BytesIO com o PDF gerado
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    # Estilos
    styles = getSampleStyleSheet()

    style_title = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=18,
        textColor=colors.HexColor("#1e3a8a"),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
    )

    style_heading = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=colors.HexColor("#1e40af"),
        spaceAfter=12,
        spaceBefore=12,
        fontName="Helvetica-Bold",
    )

    style_normal = ParagraphStyle(
        "CustomNormal", parent=styles["Normal"], fontSize=10, spaceAfter=6
    )

    # Elementos do documento
    elements = []

    # ===== CABEÇALHO =====
    elements.append(Paragraph("RELATÓRIO DE FECHAMENTO DE CAIXA", style_title))
    elements.append(Spacer(1, 0.5 * cm))

    # Informações do Caixa
    info_data = [
        ["Número do Caixa:", caixa_data.get("numero_caixa", "N/A")],
        ["Data de Abertura:", formatar_datetime(caixa_data.get("data_abertura"))],
        ["Data de Fechamento:", formatar_datetime(caixa_data.get("data_fechamento"))],
        ["Responsável:", caixa_data.get("responsavel", "N/A")],
        ["Status:", caixa_data.get("status", "N/A").upper()],
    ]

    info_table = Table(info_data, colWidths=[5 * cm, 12 * cm])
    info_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#1e40af")),
                ("ALIGN", (0, 0), (0, -1), "RIGHT"),
                ("ALIGN", (1, 0), (1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    elements.append(info_table)
    elements.append(Spacer(1, 1 * cm))

    # ===== RESUMO FINANCEIRO =====
    elements.append(Paragraph("RESUMO FINANCEIRO", style_heading))

    saldo_inicial = float(caixa_data.get("saldo_inicial", 0))
    totais = caixa_data.get("totais", {})
    saldo_final = float(totais.get("saldo_atual", 0))
    saldo_declarado = (
        float(caixa_data.get("saldo_fechamento", 0))
        if caixa_data.get("saldo_fechamento") is not None
        else None
    )
    diferenca = (
        float(caixa_data.get("diferenca", 0))
        if caixa_data.get("diferenca") is not None
        else None
    )

    resumo_data = [
        ["DESCRIÇÃO", "VALOR"],
        ["Abertura do caixa", formatar_moeda(saldo_inicial)],
        ["Total vendido no caixa", formatar_moeda(caixa_data.get("total_vendido"))],
        ["Total recebido no caixa", formatar_moeda(caixa_data.get("total_recebido"))],
        ["Vendas recebidas em dinheiro", formatar_moeda(totais.get("vendas"))],
        ["Suprimentos (entradas avulsas)", formatar_moeda(totais.get("suprimentos"))],
        [
            "Total de entradas em dinheiro",
            formatar_moeda(
                float(totais.get("vendas", 0)) + float(totais.get("suprimentos", 0))
            ),
        ],
        ["Sangrias", formatar_moeda(totais.get("sangrias"))],
        ["Despesas", formatar_moeda(totais.get("despesas"))],
        ["Devoluções", formatar_moeda(totais.get("devolucoes"))],
        ["Transferências", formatar_moeda(totais.get("transferencias"))],
        ["Saldo esperado em dinheiro", formatar_moeda(saldo_final)],
    ]
    saldo_row = len(resumo_data) - 1

    if saldo_declarado is not None:
        resumo_data.append(
            ["Saldo Declarado (Contado)", formatar_moeda(saldo_declarado)]
        )

    if diferenca is not None:
        resumo_data.append(["Diferença", formatar_moeda(diferenca)])

    resumo_table = Table(resumo_data, colWidths=[12 * cm, 5 * cm])

    table_style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e40af")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 11),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 10),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ("ALIGN", (0, 1), (0, -1), "LEFT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        (
            "ROWBACKGROUNDS",
            (0, 1),
            (-1, -1),
            [colors.white, colors.HexColor("#f3f4f6")],
        ),
    ]

    # Destacar saldo esperado
    table_style.append(
        ("BACKGROUND", (0, saldo_row), (-1, saldo_row), colors.HexColor("#dbeafe"))
    )
    table_style.append(("FONTNAME", (0, saldo_row), (-1, saldo_row), "Helvetica-Bold"))

    # Destacar diferença se houver
    if diferenca is not None:
        cor_fundo = (
            colors.HexColor("#dcfce7") if diferenca >= 0 else colors.HexColor("#fee2e2")
        )
        cor_texto = (
            colors.HexColor("#166534") if diferenca >= 0 else colors.HexColor("#991b1b")
        )
        table_style.append(
            (
                "BACKGROUND",
                (0, len(resumo_data) - 1),
                (-1, len(resumo_data) - 1),
                cor_fundo,
            )
        )
        table_style.append(
            (
                "TEXTCOLOR",
                (1, len(resumo_data) - 1),
                (1, len(resumo_data) - 1),
                cor_texto,
            )
        )
        table_style.append(
            (
                "FONTNAME",
                (0, len(resumo_data) - 1),
                (-1, len(resumo_data) - 1),
                "Helvetica-Bold",
            )
        )

    resumo_table.setStyle(TableStyle(table_style))
    elements.append(resumo_table)
    elements.append(Spacer(1, 1 * cm))

    elements.append(Paragraph("PAGAMENTOS POR FORMA", style_heading))
    formas_data = [["FORMA", "VALOR"]]
    for forma, dados in sorted(
        caixa_data.get("vendas_por_forma_pagamento", {}).items()
    ):
        prazo = forma.strip().casefold() in {"crediario", "crediário", "boleto"}
        formas_data.append(
            [
                f"{forma} (a prazo)" if prazo else forma,
                formatar_moeda(dados.get("total")),
            ]
        )
    if len(formas_data) == 1:
        formas_data.append(["Nenhum recebimento", formatar_moeda(0)])
    formas_table = Table(formas_data, colWidths=[12 * cm, 5 * cm])
    formas_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e40af")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    elements.append(formas_table)
    elements.append(Spacer(1, 0.5 * cm))
    elements.append(
        Paragraph(
            "Vendido e recebido são indicadores separados. Formas a prazo não entram no recebido. Suprimentos e abertura não são vendas.",
            style_normal,
        )
    )

    # ===== MOVIMENTAÇÕES DETALHADAS =====
    if movimentacoes and len(movimentacoes) > 0:
        elements.append(Paragraph("MOVIMENTAÇÕES DETALHADAS", style_heading))

        # Cabeçalho da tabela
        mov_data = [["DATA/HORA", "TIPO", "DESCRIÇÃO", "FORMA PGTO", "VALOR"]]

        # Adicionar movimentações
        for mov in movimentacoes:
            data_hora = formatar_datetime(mov.get("created_at"))
            tipo = {
                "venda": "VENDA",
                "suprimento": "SUPRIMENTO",
                "sangria": "SANGRIA",
                "despesa": "DESPESA",
                "transferencia": "TRANSFERÊNCIA",
                "devolucao": "DEVOLUÇÃO",
            }.get(mov.get("tipo"), str(mov.get("tipo") or "OUTRO").upper())
            descricao = str(mov.get("descricao") or "")[:40]
            forma_pgto = mov.get("forma_pagamento_nome") or "-"
            valor = mov.get("valor", 0)

            # Cores por tipo
            mov_data.append(
                [data_hora, tipo, descricao, forma_pgto, formatar_moeda(valor)]
            )

        # Criar tabela de movimentações
        mov_table = Table(
            mov_data, colWidths=[3.5 * cm, 2 * cm, 6 * cm, 3 * cm, 2.5 * cm]
        )

        # Estilo da tabela de movimentações
        mov_style = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e40af")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("ALIGN", (4, 1), (4, -1), "RIGHT"),
            ("ALIGN", (2, 1), (2, -1), "LEFT"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [colors.white, colors.HexColor("#f3f4f6")],
            ),
        ]

        # Colorir tipos de movimentação
        for i, mov in enumerate(movimentacoes, start=1):
            if mov.get("tipo") in {"venda", "suprimento", "entrada"}:
                mov_style.append(
                    ("TEXTCOLOR", (1, i), (1, i), colors.HexColor("#166534"))
                )
                mov_style.append(
                    ("TEXTCOLOR", (4, i), (4, i), colors.HexColor("#166534"))
                )
            else:
                mov_style.append(
                    ("TEXTCOLOR", (1, i), (1, i), colors.HexColor("#991b1b"))
                )
                mov_style.append(
                    ("TEXTCOLOR", (4, i), (4, i), colors.HexColor("#991b1b"))
                )

        mov_table.setStyle(TableStyle(mov_style))
        elements.append(mov_table)
    else:
        elements.append(
            Paragraph("Nenhuma movimentação registrada neste caixa.", style_normal)
        )

    elements.append(Spacer(1, 2 * cm))

    # ===== ASSINATURAS =====
    elements.append(Spacer(1, 1 * cm))

    assinatura_data = [
        ["_______________________________", "_______________________________"],
        ["Responsável pelo Caixa", "Gerente/Supervisor"],
    ]

    assinatura_table = Table(assinatura_data, colWidths=[8.5 * cm, 8.5 * cm])
    assinatura_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 1), (-1, 1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, 1), 9),
                ("TOPPADDING", (0, 1), (-1, 1), 8),
            ]
        )
    )

    elements.append(assinatura_table)

    # ===== RODAPÉ =====
    elements.append(Spacer(1, 1 * cm))
    rodape_text = f"Documento gerado automaticamente em {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}"
    elements.append(
        Paragraph(
            rodape_text,
            ParagraphStyle(
                "Rodape",
                parent=styles["Normal"],
                fontSize=8,
                textColor=colors.grey,
                alignment=TA_CENTER,
            ),
        )
    )

    # Construir PDF
    doc.build(elements)

    buffer.seek(0)
    return buffer


def formatar_datetime(dt) -> str:
    """Formata datetime para string"""
    if not dt:
        return "N/A"
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except ValueError:
            return dt
    return dt.strftime("%d/%m/%Y %H:%M")


def formatar_moeda(valor) -> str:
    """Formata valor para moeda brasileira"""
    if valor is None:
        return "R$ 0,00"
    try:
        valor_float = float(valor)
        return (
            f"R$ {valor_float:,.2f}".replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )
    except (TypeError, ValueError):
        return "R$ 0,00"
