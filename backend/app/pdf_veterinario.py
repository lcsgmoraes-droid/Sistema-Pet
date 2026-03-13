"""Geracao de PDF do modulo veterinario (prontuario e receituario)."""
from datetime import datetime
from io import BytesIO

from reportlab.graphics import renderPDF
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _fmt_data(valor):
    if not valor:
        return "-"
    if isinstance(valor, str):
        return valor
    if hasattr(valor, "strftime"):
        return valor.strftime("%d/%m/%Y")
    return str(valor)


def _fmt_datahora(valor):
    if not valor:
        return "-"
    if isinstance(valor, str):
        return valor
    if hasattr(valor, "strftime"):
        return valor.strftime("%d/%m/%Y %H:%M")
    return str(valor)


def _texto(valor):
    if valor is None:
        return "-"
    txt = str(valor).strip()
    return txt if txt else "-"


def _bloco_info(titulo, linhas):
    data = [["Campo", "Valor"], *linhas]
    tabela = Table(data, colWidths=[5.5 * cm, 10.5 * cm])
    tabela.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d4ed8")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 1), (1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d1d5db")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return [Paragraph(f"<b>{titulo}</b>", _style_subtitle()), Spacer(1, 0.2 * cm), tabela]


def _style_title():
    return ParagraphStyle(
        "VetTitle",
        parent=getSampleStyleSheet()["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=16,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=10,
    )


def _style_subtitle():
    return ParagraphStyle(
        "VetSubtitle",
        parent=getSampleStyleSheet()["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=colors.HexColor("#1e3a8a"),
        spaceBefore=6,
        spaceAfter=4,
    )


def _style_normal():
    return ParagraphStyle(
        "VetNormal",
        parent=getSampleStyleSheet()["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
    )


def _qr_drawing(conteudo, size=2.8 * cm):
    qr_widget = qr.QrCodeWidget(conteudo)
    bounds = qr_widget.getBounds()
    largura = bounds[2] - bounds[0]
    altura = bounds[3] - bounds[1]

    desenho = Drawing(size, size, transform=[size / largura, 0, 0, size / altura, 0, 0])
    desenho.add(qr_widget)
    return desenho


def gerar_pdf_prontuario(consulta, validacao_assinatura, prescricoes, url_validacao):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=1.7 * cm,
        bottomMargin=1.7 * cm,
    )

    elementos = []
    elementos.append(Paragraph("Prontuario Veterinario", _style_title()))
    elementos.append(Paragraph(f"Consulta #{consulta.id}", _style_normal()))
    elementos.append(Spacer(1, 0.4 * cm))

    elementos += _bloco_info(
        "Identificacao",
        [
            ["Pet", _texto(getattr(consulta.pet, "nome", None))],
            ["Tutor", _texto(getattr(consulta.cliente, "nome", None))],
            ["Veterinario", _texto(getattr(consulta.veterinario, "nome", None))],
            ["Status", _texto(consulta.status)],
            ["Inicio atendimento", _fmt_datahora(consulta.inicio_atendimento)],
            ["Fim atendimento", _fmt_datahora(consulta.fim_atendimento)],
            ["Finalizado em", _fmt_datahora(consulta.finalizado_em)],
        ],
    )

    elementos.append(Spacer(1, 0.35 * cm))
    elementos += _bloco_info(
        "Resumo clinico",
        [
            ["Queixa principal", _texto(consulta.queixa_principal)],
            ["Diagnostico", _texto(consulta.diagnostico)],
            ["Conduta", _texto(consulta.conduta)],
            ["Retorno (dias)", _texto(consulta.retorno_em_dias)],
            ["Peso na consulta (kg)", _texto(consulta.peso_consulta)],
            ["Temperatura", _texto(consulta.temperatura)],
            ["FC", _texto(consulta.frequencia_cardiaca)],
            ["FR", _texto(consulta.frequencia_respiratoria)],
        ],
    )

    elementos.append(Spacer(1, 0.35 * cm))
    elementos += _bloco_info(
        "Assinatura digital",
        [
            ["Assinada", "Sim" if validacao_assinatura.get("assinada") else "Nao"],
            ["Hash valido", "Sim" if validacao_assinatura.get("hash_valido") else "Nao"],
            ["Hash prontuario", _texto(validacao_assinatura.get("hash_prontuario"))],
            ["URL verificacao", _texto(url_validacao)],
        ],
    )

    if prescricoes:
        elementos.append(Spacer(1, 0.35 * cm))
        itens = [["Numero", "Data", "Tipo", "Itens"]]
        for p in prescricoes:
            itens.append(
                [
                    _texto(getattr(p, "numero", None)),
                    _fmt_data(getattr(p, "data_emissao", None)),
                    _texto(getattr(p, "tipo_receituario", None)),
                    str(len(getattr(p, "itens", []) or [])),
                ]
            )
        tabela_prescricoes = Table(itens, colWidths=[3.2 * cm, 3 * cm, 5 * cm, 4.8 * cm])
        tabela_prescricoes.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d4ed8")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d1d5db")),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ]
            )
        )
        elementos.append(Paragraph("<b>Prescricoes vinculadas</b>", _style_subtitle()))
        elementos.append(tabela_prescricoes)

    elementos.append(Spacer(1, 0.45 * cm))
    elementos.append(Paragraph("Valide este documento pelo QR code:", _style_normal()))
    elementos.append(Spacer(1, 0.15 * cm))
    elementos.append(_qr_drawing(url_validacao))

    elementos.append(Spacer(1, 0.3 * cm))
    elementos.append(
        Paragraph(
            f"Documento gerado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            ParagraphStyle("Rodape", parent=_style_normal(), fontSize=8, textColor=colors.HexColor("#64748b")),
        )
    )

    doc.build(elementos)
    buffer.seek(0)
    return buffer


def gerar_pdf_receita(prescricao, url_validacao):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=1.7 * cm,
        bottomMargin=1.7 * cm,
    )

    elementos = []
    elementos.append(Paragraph("Receituario Veterinario", _style_title()))
    elementos.append(
        Paragraph(
            f"Numero: {_texto(prescricao.numero)} | Emissao: {_fmt_data(prescricao.data_emissao)}",
            _style_normal(),
        )
    )
    elementos.append(Spacer(1, 0.35 * cm))

    elementos += _bloco_info(
        "Dados basicos",
        [
            ["Pet", _texto(getattr(prescricao.pet, "nome", None))],
            ["Veterinario", _texto(getattr(prescricao.consulta.veterinario, "nome", None) if prescricao.consulta else None)],
            ["Consulta", _texto(prescricao.consulta_id)],
            ["Tipo", _texto(prescricao.tipo_receituario)],
            ["Hash receita", _texto(prescricao.hash_receita)],
            ["URL verificacao", _texto(url_validacao)],
        ],
    )

    elementos.append(Spacer(1, 0.35 * cm))
    elementos.append(Paragraph("<b>Itens prescritos</b>", _style_subtitle()))

    dados_itens = [["Medicamento", "Posologia", "Via", "Duracao"]]
    for item in prescricao.itens:
        dados_itens.append(
            [
                _texto(item.nome_medicamento),
                _texto(item.posologia),
                _texto(item.via_administracao),
                f"{item.duracao_dias} dia(s)" if item.duracao_dias else "-",
            ]
        )

    tabela_itens = Table(dados_itens, colWidths=[4.5 * cm, 7.5 * cm, 2 * cm, 2 * cm])
    tabela_itens.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d4ed8")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d1d5db")),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    elementos.append(tabela_itens)

    elementos.append(Spacer(1, 0.45 * cm))
    elementos.append(Paragraph("Valide esta receita pelo QR code:", _style_normal()))
    elementos.append(Spacer(1, 0.15 * cm))
    elementos.append(_qr_drawing(url_validacao))

    elementos.append(Spacer(1, 0.3 * cm))
    elementos.append(
        Paragraph(
            f"Documento gerado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            ParagraphStyle("Rodape", parent=_style_normal(), fontSize=8, textColor=colors.HexColor("#64748b")),
        )
    )

    doc.build(elementos)
    buffer.seek(0)
    return buffer
