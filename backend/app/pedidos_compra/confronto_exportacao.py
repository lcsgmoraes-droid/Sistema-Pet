"""Exportacoes e texto operacional do confronto de pedidos de compra."""

import io
import json
from io import BytesIO
from typing import List, Optional
from xml.sax.saxutils import escape

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.models import Cliente
from app.produtos_models import PedidoCompra

from .confronto_calculo import _formatar_numeros_notas
from .confronto_vinculos import _obter_notas_vinculadas


def _aplicar_filtros_confronto(itens: List[dict], filtros: Optional[str]) -> List[dict]:
    if not filtros:
        return itens
    status_list = [s.strip() for s in filtros.split(",") if s.strip()]
    if not status_list:
        return itens
    return [i for i in itens if i.get("status") in status_list]


def _resumo_por_itens(itens: List[dict], resumo_base: dict) -> dict:
    total_pedido = round(sum(float(i.get("valor_pedido", 0) or 0) for i in itens), 2)
    total_nf = round(sum(float(i.get("valor_nf", 0) or 0) for i in itens), 2)
    return {
        "total_pedido": total_pedido,
        "total_nf": total_nf,
        "dif_total": round(total_nf - total_pedido, 2),
        "frete_pedido": resumo_base.get("frete_pedido", 0),
        "frete_nf": resumo_base.get("frete_nf", 0),
        "desconto_pedido": resumo_base.get("desconto_pedido", 0),
        "desconto_nf": resumo_base.get("desconto_nf", 0),
        "itens_pedido": resumo_base.get("itens_pedido", 0),
        "itens_nf": resumo_base.get("itens_nf", 0),
    }


def _numero_nota_confronto_exportacao(
    db: Session, pedido: PedidoCompra, tenant_id: int, resumo: dict, default: str = "-"
) -> str:
    from app.produtos_models import NotaEntrada

    nota = (
        db.query(NotaEntrada)
        .filter(
            NotaEntrada.id == pedido.nota_entrada_id,
            NotaEntrada.tenant_id == tenant_id,
        )
        .first()
        if pedido.nota_entrada_id
        else None
    )
    return (
        _formatar_numeros_notas(_obter_notas_vinculadas(db, pedido, tenant_id))
        or resumo.get("numeros_nota")
        or (nota.numero_nota if nota and nota.numero_nota else default)
    )


def _carregar_confronto_exportacao(
    db: Session,
    pedido_id: int,
    tenant_id: int,
    filtros: Optional[str],
    numero_nota_default: Optional[str] = "-",
) -> tuple[PedidoCompra, List[dict], dict, str]:
    pedido = (
        db.query(PedidoCompra)
        .filter(PedidoCompra.id == pedido_id, PedidoCompra.tenant_id == tenant_id)
        .first()
    )
    if not pedido or not pedido.resumo_confronto:
        raise HTTPException(status_code=404, detail="Confronto não encontrado")

    confronto = json.loads(pedido.resumo_confronto)
    itens = _aplicar_filtros_confronto(confronto.get("itens", []), filtros)
    resumo = _resumo_por_itens(itens, confronto.get("resumo", {}))
    if numero_nota_default is None:
        numero_nota_default = str(pedido.nota_entrada_id or "")
    numero_nota = _numero_nota_confronto_exportacao(
        db, pedido, tenant_id, resumo, numero_nota_default
    )
    return pedido, itens, resumo, numero_nota


def _fmt_csv(valor):
    if valor is None or valor == "":
        return ""
    return str(valor).replace(".", ",")


def criar_confronto_csv_response(
    pedido: PedidoCompra, itens: List[dict], resumo: dict, numero_nota: str
) -> StreamingResponse:
    linhas = [
        f"Pedido;{pedido.numero_pedido}",
        f"NF;{numero_nota}",
        "",
        "Produto;Código;Qtd Pedida;Qtd NF;Dif. Qtd;Preço Pedido (R$);Preço NF (R$);Dif. Unit. (R$);Dif. Preço (%);Valor Pedido (R$);Valor NF (R$);Dif. Valor (R$);Status",
    ]
    for item in itens:
        linhas.append(
            f"{item.get('produto_nome', '')};{item.get('produto_codigo', '')};{_fmt_csv(item.get('qtd_pedida', 0))};{_fmt_csv(item.get('qtd_nf', 0))};{_fmt_csv(item.get('dif_qtd', 0))};{_fmt_csv(item.get('preco_pedido', 0))};{_fmt_csv(item.get('preco_nf', 0))};{_fmt_csv(item.get('dif_preco_unit', ''))};{_fmt_csv(item.get('dif_preco_pct', 0))};{_fmt_csv(item.get('valor_pedido', 0))};{_fmt_csv(item.get('valor_nf', 0))};{_fmt_csv(item.get('dif_valor', 0))};{item.get('status', '')}"
        )
    linhas.append("")
    linhas.append(f";;Total Pedido (R$);;{_fmt_csv(resumo.get('total_pedido', 0))}")
    linhas.append(f";;Total NF (R$);;{_fmt_csv(resumo.get('total_nf', 0))}")
    linhas.append(f";;Diferença Total (R$);;{_fmt_csv(resumo.get('dif_total', 0))}")

    return StreamingResponse(
        io.StringIO("\n".join(linhas)),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename=confronto_{pedido.numero_pedido}.csv"
        },
    )


def _buscar_nome_fornecedor(db: Session, pedido: PedidoCompra, tenant_id: int) -> str:
    fornecedor = (
        db.query(Cliente)
        .filter(Cliente.id == pedido.fornecedor_id, Cliente.tenant_id == tenant_id)
        .first()
    )
    return fornecedor.nome if fornecedor else f"Fornecedor {pedido.fornecedor_id}"


def _criar_pdf_styles():
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    except ImportError:
        raise HTTPException(status_code=500, detail="reportlab não instalado")

    styles = getSampleStyleSheet()
    return (
        colors,
        ParagraphStyle(
            "T",
            parent=styles["Heading1"],
            fontSize=16,
            textColor=colors.HexColor("#1a56db"),
            alignment=TA_CENTER,
            spaceAfter=8,
        ),
        ParagraphStyle("S", parent=styles["Normal"], fontSize=9, spaceAfter=4),
        ParagraphStyle(
            "Sm", parent=styles["Normal"], fontSize=6.5, leading=8, wordWrap="CJK"
        ),
    )


def _pdf_header(pedido: PedidoCompra, numero_nota: str, fornecedor_nome: str):
    pedido_pdf = escape(str(pedido.numero_pedido or "-"))
    numero_nota_pdf = escape(str(numero_nota or "-"))
    fornecedor_pdf = escape(str(fornecedor_nome or "-"))
    data_confronto_pdf = escape(
        pedido.data_confronto.strftime("%d/%m/%Y %H:%M")
        if pedido.data_confronto
        else "-"
    )
    return (
        "CONFRONTO PEDIDO x NOTA FISCAL",
        f"Pedido: <b>{pedido_pdf}</b> &nbsp;|&nbsp; NF: <b>{numero_nota_pdf}</b> &nbsp;|&nbsp; Fornecedor: <b>{fornecedor_pdf}</b> &nbsp;|&nbsp; Data confronto: <b>{data_confronto_pdf}</b>",
    )


def _pdf_table_data(itens: List[dict], colors, small_style):
    from reportlab.platypus import Paragraph

    def cell(valor):
        return Paragraph(escape(str(valor if valor is not None else "-")), small_style)

    status_labels = {
        "ok": "OK",
        "divergencia_quantidade": "Dif. Qtd",
        "divergencia_preco": "Dif. Preço",
        "divergencia_mista": "Dif. Mista",
        "nao_encontrado": "Não Recebido",
        "nao_pedido": "Não Pedido",
    }
    status_colors = {
        "ok": colors.HexColor("#d1fae5"),
        "divergencia_quantidade": colors.HexColor("#fef3c7"),
        "divergencia_preco": colors.HexColor("#fef3c7"),
        "divergencia_mista": colors.HexColor("#fee2e2"),
        "nao_encontrado": colors.HexColor("#fee2e2"),
        "nao_pedido": colors.HexColor("#ede9fe"),
    }
    table_data = [
        [
            "Produto",
            "Cód.",
            "Qtd Ped.",
            "Qtd NF",
            "Dif.Qtd",
            "R$ Ped.",
            "R$ NF",
            "Dif.Unit",
            "Dif.%",
            "Vl.Ped.",
            "Vl.NF",
            "Dif.R$",
            "Status",
        ]
    ]
    row_colors = []

    for idx, item in enumerate(itens):
        status = item.get("status", "ok")
        row_colors.append((idx + 1, status_colors.get(status, colors.white)))
        table_data.append(
            [
                cell(item.get("produto_nome", "")),
                cell(item.get("produto_codigo") or ""),
                cell(f"{item.get('qtd_pedida', 0):.2f}".rstrip("0").rstrip(".")),
                cell(f"{item.get('qtd_nf', 0):.2f}".rstrip("0").rstrip(".")),
                cell(f"{item.get('dif_qtd', 0):+.2f}".rstrip("0").rstrip(".")),
                cell(f"R$ {item.get('preco_pedido', 0):.2f}"),
                cell(f"R$ {item.get('preco_nf', 0):.2f}"),
                cell(
                    f"R$ {item.get('dif_preco_unit', 0):+.2f}"
                    if item.get("dif_preco_unit") is not None
                    else "-"
                ),
                cell(f"{item.get('dif_preco_pct', 0):+.1f}%"),
                cell(f"R$ {item.get('valor_pedido', 0):.2f}"),
                cell(f"R$ {item.get('valor_nf', 0):.2f}"),
                cell(f"R$ {item.get('dif_valor', 0):+.2f}"),
                cell(status_labels.get(status, status)),
            ]
        )
    return table_data, row_colors


def _adicionar_tabela_itens_pdf(elements, itens: List[dict], colors, mm, small_style):
    from reportlab.platypus import Spacer, Table, TableStyle

    table_data, row_colors = _pdf_table_data(itens, colors, small_style)
    col_widths = [
        54 * mm,
        16 * mm,
        14 * mm,
        14 * mm,
        14 * mm,
        16 * mm,
        16 * mm,
        16 * mm,
        12 * mm,
        18 * mm,
        18 * mm,
        16 * mm,
        16 * mm,
    ]
    tabela = Table(table_data, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a56db")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("ALIGN", (2, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]
    for row_idx, color in row_colors:
        style_cmds.append(("BACKGROUND", (0, row_idx), (-1, row_idx), color))
    tabela.setStyle(TableStyle(style_cmds))
    elements.append(tabela)
    elements.append(Spacer(1, 5 * mm))


def _adicionar_resumo_pdf(elements, resumo: dict, colors, mm):
    from reportlab.platypus import Table, TableStyle

    resumo_data = [
        ["", "Total Produtos", "Frete", "Desconto"],
        [
            "Pedido",
            f"R$ {resumo.get('total_pedido', 0):.2f}",
            f"R$ {resumo.get('frete_pedido', 0):.2f}",
            f"R$ {resumo.get('desconto_pedido', 0):.2f}",
        ],
        [
            "NF",
            f"R$ {resumo.get('total_nf', 0):.2f}",
            f"R$ {resumo.get('frete_nf', 0):.2f}",
            f"R$ {resumo.get('desconto_nf', 0):.2f}",
        ],
        [
            "Diferença",
            f"R$ {resumo.get('dif_total', 0):+.2f}",
            f"R$ {(resumo.get('frete_nf', 0) - resumo.get('frete_pedido', 0)):+.2f}",
            "-",
        ],
    ]
    resumo_table = Table(resumo_data, colWidths=[30 * mm, 45 * mm, 35 * mm, 35 * mm])
    resumo_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    elements.append(resumo_table)


def criar_confronto_pdf_response(
    db: Session,
    tenant_id: int,
    pedido: PedidoCompra,
    itens: List[dict],
    resumo: dict,
    numero_nota: str,
) -> StreamingResponse:
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    except ImportError:
        raise HTTPException(status_code=500, detail="reportlab não instalado")

    colors, title_style, sub_style, small_style = _criar_pdf_styles()
    fornecedor_nome = _buscar_nome_fornecedor(db, pedido, tenant_id)
    titulo, subtitulo = _pdf_header(pedido, numero_nota, fornecedor_nome)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        leftMargin=10 * mm,
        rightMargin=10 * mm,
    )
    elements = [
        Paragraph(titulo, title_style),
        Paragraph(subtitulo, sub_style),
        Spacer(1, 4 * mm),
    ]
    _adicionar_tabela_itens_pdf(elements, itens, colors, mm, small_style)
    _adicionar_resumo_pdf(elements, resumo, colors, mm)

    doc.build(elements)
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=confronto_{pedido.numero_pedido}.pdf"
        },
    )


def _linhas_divergencia_email(divergencias: List[dict]) -> list[str]:
    linhas = []
    for divergencia in divergencias:
        partes = []
        status = divergencia.get("status")
        if status in ("divergencia_quantidade", "divergencia_mista", "nao_encontrado"):
            partes.append(
                f"qtd. pedida: {divergencia['qtd_pedida']}, qtd. recebida: {divergencia['qtd_nf']}"
            )
        if status in ("divergencia_preco", "divergencia_mista"):
            partes.append(
                f"preço pedido: R$ {divergencia['preco_pedido']:.2f}, preço NF: R$ {divergencia['preco_nf']:.2f} ({divergencia['dif_preco_pct']:+.1f}%)"
            )
        if status == "nao_pedido":
            partes.append("produto não constava no pedido")
        linhas.append(f"- {divergencia['produto_nome']}: {'; '.join(partes)}")
    return linhas


def gerar_texto_email_confronto(
    db: Session,
    tenant_id: int,
    pedido: PedidoCompra,
    itens: List[dict],
    resumo: dict,
    numero_nota: str,
) -> dict:
    fornecedor_nome = _buscar_nome_fornecedor(db, pedido, tenant_id)
    divergencias = [i for i in itens if i.get("status") != "ok"]
    linhas_divergencia = _linhas_divergencia_email(divergencias)
    dif_total = resumo.get("dif_total", 0)
    sinal = "a maior" if dif_total > 0 else "a menor"

    corpo = f"""Assunto: Divergências na NF {numero_nota} referente ao pedido {pedido.numero_pedido}

Prezados {fornecedor_nome},

Ao realizar a conferência do pedido {pedido.numero_pedido} com a nota fiscal recebida, identificamos as seguintes divergências:

{chr(10).join(linhas_divergencia)}

Resumo financeiro:
- Total do pedido: R$ {resumo.get("total_pedido", 0):.2f}
- Total da NF:     R$ {resumo.get("total_nf", 0):.2f}
- Diferença:       R$ {abs(dif_total):.2f} {sinal}

Solicitamos gentilmente que nos informem o motivo das divergências e, se aplicável, o prazo para envio dos itens faltantes ou emissão de nota de crédito pela diferença de valores.

Ficamos à disposição para esclarecimentos.

Atenciosamente,
[Seu nome]
"""

    return {"texto": corpo, "divergencias_count": len(divergencias)}
