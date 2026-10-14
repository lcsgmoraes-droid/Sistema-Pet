"""PDF de orçamento veterinário para compartilhar com o tutor."""

from datetime import datetime
from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .pdf_veterinario import VET_FONT, VET_FONT_BOLD

VERDE = colors.HexColor("#087f70")
VERDE_ESCURO = colors.HexColor("#075e55")
TEXTO = colors.HexColor("#243447")
SUAVE = colors.HexColor("#64748b")
FUNDO = colors.HexColor("#f0f8f5")
BORDA = colors.HexColor("#dce9e5")


def _texto(valor, padrao="—"):
    return str(valor).strip() if valor is not None and str(valor).strip() else padrao


def _par(valor, estilo):
    return Paragraph(escape(_texto(valor)).replace("\n", "<br/>"), estilo)


def _dinheiro(valor):
    numero = Decimal(str(valor or 0)).quantize(Decimal("0.01"))
    return "R$ " + f"{numero:,.2f}".replace(",", "X").replace(".", ",").replace(
        "X", "."
    )


def _quantidade(valor):
    numero = Decimal(str(valor or 0))
    return (
        f"{numero:,.3f}".replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
        .rstrip("0")
        .rstrip(",")
    )


def _endereco(clinica):
    logradouro = " ".join(
        parte for parte in [clinica.endereco, clinica.numero] if parte
    )
    localidade = "/".join(parte for parte in [clinica.cidade, clinica.uf] if parte)
    return " · ".join(
        parte
        for parte in [
            logradouro,
            clinica.complemento,
            clinica.bairro,
            localidade,
            clinica.cep,
        ]
        if parte
    )


def gerar_pdf_orcamento_vet(orcamento, clinica):
    """Gera apresentação comercial a partir do orçamento persistido, sem custos internos."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=1.7 * cm,
        bottomMargin=1.8 * cm,
        title=f"Orçamento veterinário #{orcamento.id}",
        author=_texto(clinica.name, "Clínica veterinária"),
    )
    largura = A4[0] - doc.leftMargin - doc.rightMargin
    estilos = {
        "clinica": ParagraphStyle(
            "OrcVetClinica",
            fontName=VET_FONT_BOLD,
            fontSize=17,
            leading=21,
            textColor=VERDE_ESCURO,
        ),
        "titulo": ParagraphStyle(
            "OrcVetTitulo",
            fontName=VET_FONT_BOLD,
            fontSize=19,
            leading=24,
            textColor=TEXTO,
        ),
        "subtitulo": ParagraphStyle(
            "OrcVetSubtitulo",
            fontName=VET_FONT_BOLD,
            fontSize=10,
            leading=14,
            textColor=VERDE_ESCURO,
        ),
        "corpo": ParagraphStyle(
            "OrcVetCorpo", fontName=VET_FONT, fontSize=8.8, leading=13, textColor=TEXTO
        ),
        "detalhe": ParagraphStyle(
            "OrcVetDetalhe", fontName=VET_FONT, fontSize=8, leading=11, textColor=SUAVE
        ),
        "celula": ParagraphStyle(
            "OrcVetCelula", fontName=VET_FONT, fontSize=8.2, leading=11, textColor=TEXTO
        ),
        "valor": ParagraphStyle(
            "OrcVetValor",
            fontName=VET_FONT_BOLD,
            fontSize=8.2,
            leading=11,
            textColor=TEXTO,
            alignment=TA_RIGHT,
        ),
        "total": ParagraphStyle(
            "OrcVetTotal",
            fontName=VET_FONT_BOLD,
            fontSize=14,
            leading=18,
            textColor=VERDE_ESCURO,
            alignment=TA_RIGHT,
        ),
    }

    elementos = [_par(clinica.name, estilos["clinica"])]
    identificacao = []
    if clinica.razao_social and clinica.razao_social != clinica.name:
        identificacao.append(clinica.razao_social)
    if clinica.cnpj:
        identificacao.append(f"CNPJ {clinica.cnpj}")
    if identificacao:
        elementos.append(_par(" · ".join(identificacao), estilos["detalhe"]))
    endereco = _endereco(clinica)
    if endereco:
        elementos.append(_par(endereco, estilos["detalhe"]))
    contato = " · ".join(parte for parte in [clinica.telefone, clinica.email] if parte)
    if contato:
        elementos.append(_par(contato, estilos["detalhe"]))

    elementos.extend(
        [Spacer(1, 0.35 * cm), _par("ORÇAMENTO VETERINÁRIO", estilos["titulo"])]
    )
    data = getattr(orcamento, "created_at", None)
    emissao = data.strftime("%d/%m/%Y") if isinstance(data, datetime) else "—"
    vinculo = (
        f"Internação #{orcamento.internacao_id}"
        if orcamento.internacao_id
        else f"Consulta #{orcamento.consulta_id}"
        if orcamento.consulta_id
        else None
    )
    meta = f"Nº {orcamento.id}   ·   Emissão: {emissao}"
    if vinculo:
        meta += f"   ·   {vinculo}"
    elementos.append(_par(meta, estilos["detalhe"]))
    elementos.append(Spacer(1, 0.55 * cm))

    pet = orcamento.pet
    tutor = orcamento.cliente
    veterinario = orcamento.veterinario
    pet_descricao = _texto(getattr(pet, "nome", None))
    especie = getattr(pet, "especie", None)
    if especie:
        pet_descricao += f" · {especie}"
    crmv = getattr(veterinario, "crmv", None)
    vet_descricao = _texto(getattr(veterinario, "nome", None), "Não informado")
    if crmv:
        vet_descricao += f" · CRMV {crmv}"

    dados = Table(
        [
            [
                [
                    _par("TUTOR", estilos["subtitulo"]),
                    _par(getattr(tutor, "nome", None), estilos["corpo"]),
                ],
                [
                    _par("PACIENTE", estilos["subtitulo"]),
                    _par(pet_descricao, estilos["corpo"]),
                ],
            ],
            [
                [
                    _par("VETERINÁRIO RESPONSÁVEL", estilos["subtitulo"]),
                    _par(vet_descricao, estilos["corpo"]),
                ],
                [
                    _par("REFERÊNCIA", estilos["subtitulo"]),
                    _par(
                        _texto(orcamento.titulo, "Atendimento veterinário"),
                        estilos["corpo"],
                    ),
                ],
            ],
        ],
        colWidths=[largura / 2, largura / 2],
    )
    dados.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), FUNDO),
                ("BOX", (0, 0), (-1, -1), 0.5, BORDA),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, BORDA),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 11),
                ("RIGHTPADDING", (0, 0), (-1, -1), 11),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )
    elementos.extend(
        [
            dados,
            Spacer(1, 0.55 * cm),
            _par("ITENS PREVISTOS", estilos["subtitulo"]),
            Spacer(1, 0.15 * cm),
        ]
    )

    linhas = [["Descrição", "Qtd.", "Valor unit.", "Total"]]
    for item in sorted(
        orcamento.itens or [], key=lambda atual: (atual.ordem, atual.id or 0)
    ):
        quantidade = _quantidade(item.quantidade)
        if item.unidade:
            quantidade += f" {item.unidade}"
        linhas.append(
            [
                _par(item.nome, estilos["celula"]),
                _par(quantidade, estilos["celula"]),
                _par(_dinheiro(item.preco_unitario), estilos["valor"]),
                _par(_dinheiro(item.preco_total), estilos["valor"]),
            ]
        )
    tabela = Table(
        linhas,
        colWidths=[largura * 0.46, largura * 0.14, largura * 0.19, largura * 0.21],
        repeatRows=1,
    )
    tabela.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), VERDE),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), VET_FONT_BOLD),
                ("FONTSIZE", (0, 0), (-1, 0), 8.5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, FUNDO]),
                ("LINEBELOW", (0, 1), (-1, -1), 0.35, BORDA),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 0), (-1, 0), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )
    elementos.extend([tabela, Spacer(1, 0.38 * cm)])
    total = Table(
        [
            [
                _par("VALOR TOTAL ESTIMADO", estilos["subtitulo"]),
                _par(_dinheiro(orcamento.preco_total), estilos["total"]),
            ]
        ],
        colWidths=[largura * 0.58, largura * 0.42],
    )
    total.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), FUNDO),
                ("BOX", (0, 0), (-1, -1), 0.6, BORDA),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    elementos.extend(
        [
            total,
            Spacer(1, 0.45 * cm),
            _par(
                "Itens e valores previstos para este atendimento. Confirme com a clínica antes da realização dos serviços.",
                estilos["detalhe"],
            ),
        ]
    )

    def rodape(canvas, documento):
        canvas.saveState()
        canvas.setStrokeColor(BORDA)
        canvas.line(doc.leftMargin, 1.25 * cm, A4[0] - doc.rightMargin, 1.25 * cm)
        canvas.setFont(VET_FONT, 7.5)
        canvas.setFillColor(SUAVE)
        canvas.drawString(
            doc.leftMargin,
            0.95 * cm,
            f"Orçamento #{orcamento.id} · {_texto(clinica.name)}",
        )
        canvas.drawRightString(
            A4[0] - doc.rightMargin, 0.95 * cm, f"Página {documento.page}"
        )
        canvas.restoreState()

    doc.build(elementos, onFirstPage=rodape, onLaterPages=rodape)
    buffer.seek(0)
    return buffer
