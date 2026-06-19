"""Documentos da transferencia de estoque para parceiro."""

from datetime import date
from typing import Any
import io

from fastapi import HTTPException

from ..financeiro_models import ContaReceber
from ..models import Cliente

_OPCOES_DOCUMENTO_TRANSFERENCIA_PADRAO = {
    "mostrar_codigo": True,
    "mostrar_descricao": True,
    "mostrar_quantidade": True,
    "mostrar_custo_unitario": True,
    "mostrar_total_item": True,
    "mostrar_totais": True,
}


def _bool_opcao_documento_transferencia(valor, padrao: bool = True) -> bool:
    if valor is None:
        return padrao
    if isinstance(valor, str):
        return valor.strip().lower() in {"1", "true", "t", "sim", "s", "yes", "y", "on"}
    return bool(valor)


def _normalizar_opcoes_documento_transferencia(opcoes: dict | None = None) -> dict:
    normalizadas = dict(_OPCOES_DOCUMENTO_TRANSFERENCIA_PADRAO)
    for chave, padrao in _OPCOES_DOCUMENTO_TRANSFERENCIA_PADRAO.items():
        if opcoes and chave in opcoes:
            normalizadas[chave] = _bool_opcao_documento_transferencia(
                opcoes.get(chave), padrao
            )

    if not any(
        normalizadas[chave]
        for chave in (
            "mostrar_codigo",
            "mostrar_descricao",
            "mostrar_quantidade",
            "mostrar_custo_unitario",
            "mostrar_total_item",
        )
    ):
        normalizadas["mostrar_descricao"] = True

    return normalizadas


def _saldo_conta_receber(conta: ContaReceber) -> float:
    valor_original = float(conta.valor_original or 0)
    valor_recebido = float(conta.valor_recebido or 0)
    saldo = valor_original - valor_recebido
    return round(max(saldo, 0.0), 2)


def _status_transferencia_parceiro(conta: ContaReceber) -> tuple[str, str]:
    status_atual = str(getattr(conta, "status", "") or "").strip().lower()
    saldo_aberto = _saldo_conta_receber(conta)
    hoje = date.today()

    if status_atual in {"recebido", "pago"} or saldo_aberto <= 0:
        return "recebido", "Recebida"
    if status_atual in {"cancelado", "cancelada"}:
        return "cancelado", "Cancelada"
    if status_atual in {"parcial", "baixa_parcial"}:
        if conta.data_vencimento and conta.data_vencimento < hoje:
            return "vencido", "Vencida"
        return "parcial", "Parcial"
    if conta.data_vencimento and conta.data_vencimento < hoje:
        return "vencido", "Vencida"
    return "pendente", "Pendente"


def _gerar_pdf_transferencia_parceiro_bytes(
    conta: ContaReceber,
    parceiro: Cliente | None,
    itens: list[Any],
    opcoes_documento: dict | None = None,
) -> bytes:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="Biblioteca reportlab nao instalada. Execute: pip install reportlab",
        )

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
    )

    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle(
        "TransferenciaTitulo",
        parent=styles["Heading1"],
        fontSize=18,
        textColor=colors.HexColor("#0f172a"),
        alignment=TA_CENTER,
        spaceAfter=8,
    )
    subtitulo_style = ParagraphStyle(
        "TransferenciaSubtitulo",
        parent=styles["BodyText"],
        fontSize=9,
        textColor=colors.HexColor("#475569"),
        alignment=TA_CENTER,
        spaceAfter=14,
    )

    opcoes = _normalizar_opcoes_documento_transferencia(opcoes_documento)
    mostra_valores = any(
        opcoes[chave]
        for chave in ("mostrar_custo_unitario", "mostrar_total_item", "mostrar_totais")
    )

    elements = [
        Paragraph("TRANSFERENCIA COM RESSARCIMENTO", titulo_style),
        Paragraph(
            "Documento operacional de saida de estoque pelo custo"
            if mostra_valores
            else "Documento operacional de retirada de estoque",
            subtitulo_style,
        ),
    ]

    parceiro_nome = parceiro.nome if parceiro else "Pessoa nao encontrada"
    status_resolvido, status_label = _status_transferencia_parceiro(conta)
    saldo_aberto = _saldo_conta_receber(conta)
    valor_original = float(conta.valor_original or 0)
    valor_recebido = float(conta.valor_recebido or 0)

    bloco_info = Table(
        [
            [
                "Documento",
                conta.documento or f"TRP-{conta.id:06d}",
                "Pessoa",
                parceiro_nome,
            ],
            [
                "Emissao",
                conta.data_emissao.strftime("%d/%m/%Y") if conta.data_emissao else "-",
                "Vencimento",
                conta.data_vencimento.strftime("%d/%m/%Y")
                if conta.data_vencimento
                else "-",
            ],
            ["Status", status_label, "Email", getattr(parceiro, "email", None) or "-"],
        ],
        colWidths=[26 * mm, 58 * mm, 22 * mm, 74 * mm],
    )
    bloco_info.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(bloco_info)
    elements.append(Spacer(1, 8 * mm))

    colunas_itens = []
    largura_total = 180 * mm
    largura_fixa = 0
    if opcoes["mostrar_codigo"]:
        colunas_itens.append(("codigo", "Codigo", 22 * mm))
        largura_fixa += 22 * mm
    if opcoes["mostrar_descricao"]:
        colunas_itens.append(("produto", "Produto", None))
    if opcoes["mostrar_quantidade"]:
        colunas_itens.append(("quantidade", "Qtd", 18 * mm))
        largura_fixa += 18 * mm
    if opcoes["mostrar_custo_unitario"]:
        colunas_itens.append(("custo_unitario", "Custo un.", 28 * mm))
        largura_fixa += 28 * mm
    if opcoes["mostrar_total_item"]:
        colunas_itens.append(("total", "Total", 28 * mm))
        largura_fixa += 28 * mm

    largura_produto = max(54 * mm, largura_total - largura_fixa)
    col_widths = [
        largura_produto if chave == "produto" else largura
        for chave, _label, largura in colunas_itens
    ]
    tabela_itens = [[label for _chave, label, _largura in colunas_itens]]
    for item in itens:
        linha = []
        for chave, _label, _largura in colunas_itens:
            if chave == "codigo":
                linha.append(item.codigo or "-")
            elif chave == "produto":
                linha.append(Paragraph(item.produto_nome, styles["BodyText"]))
            elif chave == "quantidade":
                linha.append(
                    f"{float(item.quantidade or 0):.3f}".rstrip("0").rstrip(".")
                )
            elif chave == "custo_unitario":
                linha.append(f"R$ {float(item.custo_unitario or 0):.2f}")
            elif chave == "total":
                linha.append(f"R$ {float(item.valor_total or 0):.2f}")
        tabela_itens.append(linha)

    tabela = Table(
        tabela_itens,
        colWidths=col_widths,
        repeatRows=1,
    )
    estilos_tabela = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        (
            "ROWBACKGROUNDS",
            (0, 1),
            (-1, -1),
            [colors.white, colors.HexColor("#f8fafc")],
        ),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    for indice, (chave, _label, _largura) in enumerate(colunas_itens):
        if chave in {"quantidade", "custo_unitario", "total"}:
            estilos_tabela.append(("ALIGN", (indice, 1), (indice, -1), "RIGHT"))
    tabela.setStyle(TableStyle(estilos_tabela))
    elements.append(tabela)
    elements.append(Spacer(1, 6 * mm))

    if opcoes["mostrar_totais"]:
        totais = Table(
            [
                ["Valor transferido", f"R$ {valor_original:.2f}"],
                ["Valor recebido", f"R$ {valor_recebido:.2f}"],
                ["Saldo em aberto", f"R$ {saldo_aberto:.2f}"],
            ],
            colWidths=[48 * mm, 38 * mm],
            hAlign="RIGHT",
        )
        totais.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    (
                        "TEXTCOLOR",
                        (1, 2),
                        (1, 2),
                        colors.HexColor("#b45309")
                        if status_resolvido != "recebido"
                        else colors.HexColor("#047857"),
                    ),
                    ("LINEABOVE", (0, 2), (-1, 2), 1, colors.HexColor("#94a3b8")),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        elements.append(totais)

    if conta.observacoes:
        elements.append(Spacer(1, 6 * mm))
        elements.append(Paragraph("<b>Observacoes</b>", styles["Heading4"]))
        elements.append(
            Paragraph(
                (conta.observacoes or "").replace("\n", "<br/>"), styles["BodyText"]
            )
        )

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def _gerar_pdf_transferencias_parceiro_consolidado_bytes(
    contas: list[ContaReceber],
    itens_por_conta: dict[int, list[Any]],
    opcoes_documento: dict | None = None,
) -> bytes:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="Biblioteca reportlab nao instalada. Execute: pip install reportlab",
        )

    if not contas:
        raise HTTPException(
            status_code=404, detail="Nenhuma transferencia encontrada para consolidar"
        )

    opcoes = _normalizar_opcoes_documento_transferencia(opcoes_documento)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
    )

    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle(
        "TransferenciaConsolidadaTitulo",
        parent=styles["Heading1"],
        fontSize=17,
        textColor=colors.HexColor("#0f172a"),
        alignment=TA_CENTER,
        spaceAfter=6,
    )
    subtitulo_style = ParagraphStyle(
        "TransferenciaConsolidadaSubtitulo",
        parent=styles["BodyText"],
        fontSize=9,
        textColor=colors.HexColor("#475569"),
        alignment=TA_CENTER,
        spaceAfter=12,
    )
    secao_style = ParagraphStyle(
        "TransferenciaConsolidadaSecao",
        parent=styles["Heading4"],
        fontSize=11,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4,
        spaceBefore=8,
    )

    pessoas = sorted(
        {
            (conta.cliente.nome if conta.cliente else "Pessoa nao encontrada")
            for conta in contas
        }
    )
    total_transferido = sum(float(conta.valor_original or 0) for conta in contas)
    total_recebido = sum(float(conta.valor_recebido or 0) for conta in contas)
    total_saldo = sum(_saldo_conta_receber(conta) for conta in contas)
    datas_emissao = [conta.data_emissao for conta in contas if conta.data_emissao]
    periodo_texto = "-"
    if datas_emissao:
        periodo_texto = (
            f"{min(datas_emissao).strftime('%d/%m/%Y')} ate "
            f"{max(datas_emissao).strftime('%d/%m/%Y')}"
        )

    elements = [
        Paragraph("TRANSFERENCIAS CONSOLIDADAS", titulo_style),
        Paragraph(
            "Relatorio unico para acerto por periodo ou selecao manual",
            subtitulo_style,
        ),
    ]

    resumo_linhas = [
        ["Pessoas", ", ".join(pessoas[:4]) + ("..." if len(pessoas) > 4 else "")],
        ["Periodo", periodo_texto],
        ["Lancamentos", str(len(contas))],
    ]
    if opcoes["mostrar_totais"]:
        resumo_linhas.extend(
            [
                ["Valor transferido", f"R$ {total_transferido:.2f}"],
                ["Valor recebido", f"R$ {total_recebido:.2f}"],
                ["Saldo em aberto", f"R$ {total_saldo:.2f}"],
            ]
        )

    resumo = Table(
        resumo_linhas,
        colWidths=[34 * mm, 144 * mm],
    )
    resumo.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(resumo)
    elements.append(Spacer(1, 5 * mm))

    tabela_documentos = [["Documento", "Pessoa", "Emissao", "Status"]]
    col_widths_resumo = [30 * mm, 82 * mm, 24 * mm, 26 * mm]
    if opcoes["mostrar_totais"]:
        tabela_documentos[0].extend(["Valor", "Saldo"])
        col_widths_resumo = [28 * mm, 62 * mm, 22 * mm, 24 * mm, 28 * mm, 24 * mm]

    for conta in contas:
        pessoa = conta.cliente.nome if conta.cliente else "Pessoa nao encontrada"
        status_label = _status_transferencia_parceiro(conta)[1]
        linha_documento = [
            conta.documento or f"TRP-{conta.id:06d}",
            Paragraph(pessoa, styles["BodyText"]),
            conta.data_emissao.strftime("%d/%m/%Y") if conta.data_emissao else "-",
            status_label,
        ]
        if opcoes["mostrar_totais"]:
            linha_documento.extend(
                [
                    f"R$ {float(conta.valor_original or 0):.2f}",
                    f"R$ {_saldo_conta_receber(conta):.2f}",
                ]
            )
        tabela_documentos.append(linha_documento)

    tabela_resumo = Table(
        tabela_documentos,
        colWidths=col_widths_resumo,
        repeatRows=1,
    )
    tabela_resumo.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#f8fafc")],
                ),
            ]
        )
    )
    elements.append(tabela_resumo)
    elements.append(Spacer(1, 5 * mm))

    for conta in contas:
        parceiro_nome = conta.cliente.nome if conta.cliente else "Pessoa nao encontrada"
        documento = conta.documento or f"TRP-{conta.id:06d}"
        status_label = _status_transferencia_parceiro(conta)[1]
        elements.append(
            Paragraph(
                f"{documento} | {parceiro_nome} | {status_label}",
                secao_style,
            )
        )
        elementos_info = [
            f"Emissao: {conta.data_emissao.strftime('%d/%m/%Y') if conta.data_emissao else '-'}",
            f"Vencimento: {conta.data_vencimento.strftime('%d/%m/%Y') if conta.data_vencimento else '-'}",
        ]
        if opcoes["mostrar_totais"]:
            elementos_info.extend(
                [
                    f"Valor: R$ {float(conta.valor_original or 0):.2f}",
                    f"Recebido: R$ {float(conta.valor_recebido or 0):.2f}",
                    f"Saldo: R$ {_saldo_conta_receber(conta):.2f}",
                ]
            )
        elements.append(Paragraph(" | ".join(elementos_info), styles["BodyText"]))

        itens = itens_por_conta.get(conta.id, [])
        if itens:
            colunas_itens = []
            largura_total = 172 * mm
            largura_fixa = 0
            if opcoes["mostrar_codigo"]:
                colunas_itens.append(("codigo", "Codigo", 20 * mm))
                largura_fixa += 20 * mm
            if opcoes["mostrar_descricao"]:
                colunas_itens.append(("produto", "Produto", None))
            if opcoes["mostrar_quantidade"]:
                colunas_itens.append(("quantidade", "Qtd", 16 * mm))
                largura_fixa += 16 * mm
            if opcoes["mostrar_custo_unitario"]:
                colunas_itens.append(("custo_unitario", "Custo", 24 * mm))
                largura_fixa += 24 * mm
            if opcoes["mostrar_total_item"]:
                colunas_itens.append(("total", "Total", 24 * mm))
                largura_fixa += 24 * mm

            largura_produto = max(54 * mm, largura_total - largura_fixa)
            col_widths_itens = [
                largura_produto if chave == "produto" else largura
                for chave, _label, largura in colunas_itens
            ]
            tabela_itens = [[label for _chave, label, _largura in colunas_itens]]
            for item in itens:
                linha_item = []
                for chave, _label, _largura in colunas_itens:
                    if chave == "codigo":
                        linha_item.append(item.codigo or "-")
                    elif chave == "produto":
                        linha_item.append(
                            Paragraph(item.produto_nome, styles["BodyText"])
                        )
                    elif chave == "quantidade":
                        linha_item.append(
                            f"{float(item.quantidade or 0):.3f}".rstrip("0").rstrip(".")
                        )
                    elif chave == "custo_unitario":
                        linha_item.append(f"R$ {float(item.custo_unitario or 0):.2f}")
                    elif chave == "total":
                        linha_item.append(f"R$ {float(item.valor_total or 0):.2f}")
                tabela_itens.append(linha_item)
            tabela_itens_pdf = Table(
                tabela_itens,
                colWidths=col_widths_itens,
                repeatRows=1,
            )
            estilos_itens = [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
            for indice, (chave, _label, _largura) in enumerate(colunas_itens):
                if chave in {"quantidade", "custo_unitario", "total"}:
                    estilos_itens.append(("ALIGN", (indice, 1), (indice, -1), "RIGHT"))
            tabela_itens_pdf.setStyle(TableStyle(estilos_itens))
            elements.append(Spacer(1, 2 * mm))
            elements.append(tabela_itens_pdf)

        if conta.observacoes:
            elements.append(Spacer(1, 2 * mm))
            elements.append(
                Paragraph(
                    f"<b>Observacoes:</b> {(conta.observacoes or '').replace(chr(10), '<br/>')}",
                    styles["BodyText"],
                )
            )
        elements.append(Spacer(1, 4 * mm))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def _montar_email_transferencia_parceiro(
    conta: ContaReceber,
    parceiro: Cliente | None,
    itens: list[Any],
    mensagem_extra: str | None = None,
    opcoes_documento: dict | None = None,
) -> tuple[str, str, str]:
    def _formatar_quantidade_email(valor: float | int | None) -> str:
        texto = f"{float(valor or 0):.3f}"
        return texto.rstrip("0").rstrip(".")

    parceiro_nome = parceiro.nome if parceiro else "Pessoa nao encontrada"
    documento = conta.documento or f"TRP-{conta.id:06d}"
    status_label = _status_transferencia_parceiro(conta)[1]
    valor_original = float(conta.valor_original or 0)
    observacoes = (conta.observacoes or "").strip()
    mensagem_extra = (mensagem_extra or "").strip()
    opcoes = _normalizar_opcoes_documento_transferencia(opcoes_documento)
    mostra_valores = any(
        opcoes[chave]
        for chave in ("mostrar_custo_unitario", "mostrar_total_item", "mostrar_totais")
    )

    colunas_email = []
    if opcoes["mostrar_codigo"]:
        colunas_email.append(("codigo", "Codigo", "left"))
    if opcoes["mostrar_descricao"]:
        colunas_email.append(("produto", "Produto", "left"))
    if opcoes["mostrar_quantidade"]:
        colunas_email.append(("quantidade", "Qtd", "right"))
    if opcoes["mostrar_custo_unitario"]:
        colunas_email.append(("custo_unitario", "Custo un.", "right"))
    if opcoes["mostrar_total_item"]:
        colunas_email.append(("total", "Total", "right"))

    def _valor_coluna_email(item: Any, chave: str) -> str:
        if chave == "codigo":
            return item.codigo or "-"
        if chave == "produto":
            return item.produto_nome
        if chave == "quantidade":
            return _formatar_quantidade_email(item.quantidade)
        if chave == "custo_unitario":
            return f"R$ {float(item.custo_unitario or 0):.2f}"
        if chave == "total":
            return f"R$ {float(item.valor_total or 0):.2f}"
        return "-"

    cabecalho_itens_html = "".join(
        f"<th style='padding:8px 10px;text-align:{alinhamento};'>{label}</th>"
        for _chave, label, alinhamento in colunas_email
    )
    itens_html = "".join(
        "<tr>"
        + "".join(
            f"<td style='padding:8px 10px;border-bottom:1px solid #e5e7eb;text-align:{alinhamento};'>"
            f"{_valor_coluna_email(item, chave)}</td>"
            for chave, _label, alinhamento in colunas_email
        )
        + "</tr>"
        for item in itens
    )
    total_html = (
        f"<li><strong>Total:</strong> R$ {valor_original:.2f}</li>"
        if opcoes["mostrar_totais"]
        else ""
    )

    assunto = f"Transferencia {documento} - ressarcimento de estoque"
    html_body = f"""
    <html>
      <body style="font-family:Arial,sans-serif;color:#0f172a;max-width:720px;margin:0 auto;">
        <div style="background:#0f172a;color:#ffffff;padding:20px 24px;border-radius:12px 12px 0 0;">
          <h1 style="margin:0;font-size:22px;">Transferencia com ressarcimento</h1>
          <p style="margin:8px 0 0;opacity:0.9;">Documento {documento} • {parceiro_nome}</p>
        </div>
        <div style="border:1px solid #e5e7eb;border-top:none;border-radius:0 0 12px 12px;padding:24px;">
          <p>Ola,</p>
          <p>Segue em anexo o PDF da transferencia de estoque{(" com ressarcimento pelo custo" if mostra_valores else " para conferencia da retirada")}.</p>
          <ul>
            <li><strong>Status:</strong> {status_label}</li>
            <li><strong>Emissao:</strong> {conta.data_emissao.strftime("%d/%m/%Y") if conta.data_emissao else "-"}</li>
            <li><strong>Vencimento:</strong> {conta.data_vencimento.strftime("%d/%m/%Y") if conta.data_vencimento else "-"}</li>
            {total_html}
          </ul>
          <table style="width:100%;border-collapse:collapse;margin-top:16px;">
            <thead>
              <tr style="background:#f8fafc;color:#334155;">
                {cabecalho_itens_html}
              </tr>
            </thead>
            <tbody>{itens_html}</tbody>
          </table>
          {f"<p style='margin-top:16px;'><strong>Observacoes:</strong><br/>{observacoes.replace(chr(10), '<br/>')}</p>" if observacoes else ""}
          {f"<p style='margin-top:16px;'>{mensagem_extra.replace(chr(10), '<br/>')}</p>" if mensagem_extra else ""}
          <p style="margin-top:20px;">Se precisar de qualquer ajuste, basta responder este e-mail.</p>
        </div>
      </body>
    </html>
    """

    linhas_itens = []
    for item in itens:
        partes = []
        for chave, label, _alinhamento in colunas_email:
            partes.append(f"{label}: {_valor_coluna_email(item, chave)}")
        linhas_itens.append("- " + " | ".join(partes))

    text_body = (
        f"Transferencia {'com ressarcimento' if mostra_valores else 'para conferencia de retirada'}\n"
        f"Documento: {documento}\n"
        f"Pessoa: {parceiro_nome}\n"
        f"Status: {status_label}\n"
        f"Emissao: {conta.data_emissao.strftime('%d/%m/%Y') if conta.data_emissao else '-'}\n"
        f"Vencimento: {conta.data_vencimento.strftime('%d/%m/%Y') if conta.data_vencimento else '-'}\n"
        + (f"Total: R$ {valor_original:.2f}\n" if opcoes["mostrar_totais"] else "")
        + "\n"
        "Itens:\n" + "\n".join(linhas_itens)
    )
    if observacoes:
        text_body += f"\n\nObservacoes:\n{observacoes}"
    if mensagem_extra:
        text_body += f"\n\nMensagem:\n{mensagem_extra}"

    return assunto, html_body, text_body
