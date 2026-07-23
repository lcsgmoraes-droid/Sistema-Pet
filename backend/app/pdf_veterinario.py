"""Geracao de PDF do modulo veterinario (prontuario e receituario)."""

from datetime import datetime
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

import reportlab
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _registrar_fontes_pdf() -> tuple[str, str]:
    """Usa a fonte Unicode distribuída com o ReportLab."""
    try:
        fontes_dir = Path(reportlab.__file__).resolve().parent / "fonts"
        pdfmetrics.registerFont(TTFont("VetSans", str(fontes_dir / "Vera.ttf")))
        pdfmetrics.registerFont(TTFont("VetSans-Bold", str(fontes_dir / "VeraBd.ttf")))
        return "VetSans", "VetSans-Bold"
    except Exception:
        return "Helvetica", "Helvetica-Bold"


VET_FONT, VET_FONT_BOLD = _registrar_fontes_pdf()


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
    data = [["Campo", "Valor"]]
    data.extend([[_par(campo, bold=True), _par(valor)] for campo, valor in linhas])
    tabela = Table(data, colWidths=[5.5 * cm, 10.5 * cm])
    tabela.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d4ed8")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), VET_FONT_BOLD),
                ("FONTNAME", (0, 1), (0, -1), VET_FONT_BOLD),
                ("FONTNAME", (1, 1), (1, -1), VET_FONT),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d1d5db")),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#f8fafc")],
                ),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return [
        Paragraph(f"<b>{titulo}</b>", _style_subtitle()),
        Spacer(1, 0.2 * cm),
        tabela,
    ]


def _style_title():
    return ParagraphStyle(
        "VetTitle",
        parent=getSampleStyleSheet()["Heading1"],
        fontName=VET_FONT_BOLD,
        fontSize=16,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=10,
    )


def _style_subtitle():
    return ParagraphStyle(
        "VetSubtitle",
        parent=getSampleStyleSheet()["Heading3"],
        fontName=VET_FONT_BOLD,
        fontSize=11,
        textColor=colors.HexColor("#1e3a8a"),
        spaceBefore=6,
        spaceAfter=4,
    )


def _style_normal():
    return ParagraphStyle(
        "VetNormal",
        parent=getSampleStyleSheet()["Normal"],
        fontName=VET_FONT,
        fontSize=9,
        leading=12,
    )


def _style_cell(bold=False):
    return ParagraphStyle(
        "VetCellBold" if bold else "VetCell",
        parent=_style_normal(),
        fontName=VET_FONT_BOLD if bold else VET_FONT,
        fontSize=8,
        leading=10,
    )


def _par(valor, bold=False):
    return Paragraph(escape(_texto(valor)), _style_cell(bold=bold))


def _qr_drawing(conteudo, size=2.8 * cm):
    qr_widget = qr.QrCodeWidget(conteudo)
    bounds = qr_widget.getBounds()
    largura = bounds[2] - bounds[0]
    altura = bounds[3] - bounds[1]

    desenho = Drawing(size, size, transform=[size / largura, 0, 0, size / altura, 0, 0])
    desenho.add(qr_widget)
    return desenho


def _veterinario_rotulo(veterinario) -> str:
    nome = _texto(getattr(veterinario, "nome", None))
    crmv = str(getattr(veterinario, "crmv", None) or "").strip()
    return f"{nome} — CRMV {crmv}" if crmv else nome


def _bloco_assinatura_qr(veterinario, url_validacao, *, legenda_qr: str):
    assinatura = [
        Spacer(1, 0.7 * cm),
        Paragraph("________________________________________", _style_normal()),
        Paragraph(_veterinario_rotulo(veterinario), _style_normal()),
        Paragraph("Assinatura do médico-veterinário", _style_normal()),
    ]
    validacao = [
        Paragraph(escape(legenda_qr), _style_cell(bold=True)),
        Spacer(1, 0.1 * cm),
        _qr_drawing(url_validacao, size=2.35 * cm),
    ]
    tabela = Table([[assinatura, validacao]], colWidths=[12.5 * cm, 3.5 * cm])
    tabela.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return KeepTogether([tabela])


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
            ["Veterinario", _veterinario_rotulo(consulta.veterinario)],
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
        "Validação do documento",
        [
            [
                "Assinatura / integridade",
                (
                    "Assinada e hash válido"
                    if validacao_assinatura.get("assinada")
                    and validacao_assinatura.get("hash_valido")
                    else "Verificação pendente ou inválida"
                ),
            ],
            ["Hash prontuario", _texto(validacao_assinatura.get("hash_prontuario"))],
        ],
    )

    if prescricoes:
        elementos.append(Spacer(1, 0.35 * cm))
        itens = [["Numero", "Data", "Tipo", "Itens"]]
        for p in prescricoes:
            itens.append(
                [
                    _par(getattr(p, "numero", None)),
                    _par(_fmt_data(getattr(p, "data_emissao", None))),
                    _par(getattr(p, "tipo_receituario", None)),
                    _par(str(len(getattr(p, "itens", []) or []))),
                ]
            )
        tabela_prescricoes = Table(
            itens, colWidths=[3.2 * cm, 3 * cm, 5 * cm, 4.8 * cm]
        )
        tabela_prescricoes.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d4ed8")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), VET_FONT_BOLD),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d1d5db")),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ]
            )
        )
        elementos.append(Paragraph("<b>Prescricoes vinculadas</b>", _style_subtitle()))
        elementos.append(tabela_prescricoes)

    elementos.append(Spacer(1, 0.35 * cm))
    elementos.append(
        _bloco_assinatura_qr(
            consulta.veterinario,
            url_validacao,
            legenda_qr="Validar prontuário",
        )
    )

    elementos.append(Spacer(1, 0.3 * cm))
    elementos.append(
        Paragraph(
            f"Documento gerado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            ParagraphStyle(
                "Rodape",
                parent=_style_normal(),
                fontSize=8,
                textColor=colors.HexColor("#64748b"),
            ),
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
            [
                "Tutor",
                _texto(
                    getattr(prescricao.consulta.cliente, "nome", None)
                    if prescricao.consulta
                    else None
                ),
            ],
            [
                "Veterinario",
                _veterinario_rotulo(
                    prescricao.consulta.veterinario if prescricao.consulta else None
                ),
            ],
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
                _par(item.nome_medicamento),
                _par(item.posologia),
                _par(item.via_administracao),
                _par(f"{item.duracao_dias} dia(s)" if item.duracao_dias else "-"),
            ]
        )

    tabela_itens = Table(dados_itens, colWidths=[4.5 * cm, 7.5 * cm, 2 * cm, 2 * cm])
    tabela_itens.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d4ed8")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), VET_FONT_BOLD),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d1d5db")),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    elementos.append(tabela_itens)

    elementos.append(Spacer(1, 0.35 * cm))
    elementos.append(
        _bloco_assinatura_qr(
            prescricao.consulta.veterinario if prescricao.consulta else None,
            url_validacao,
            legenda_qr="Validar receita",
        )
    )

    elementos.append(Spacer(1, 0.3 * cm))
    elementos.append(
        Paragraph(
            f"Documento gerado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            ParagraphStyle(
                "Rodape",
                parent=_style_normal(),
                fontSize=8,
                textColor=colors.HexColor("#64748b"),
            ),
        )
    )

    doc.build(elementos)
    buffer.seek(0)
    return buffer
