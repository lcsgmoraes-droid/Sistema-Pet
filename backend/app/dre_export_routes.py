"""Exportacoes PDF e Excel da DRE."""

from datetime import date, datetime
from decimal import Decimal
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .auth.dependencies import get_current_user_and_tenant
from .db import get_session
from .dre_canais.routes import gerar_dre_por_canais
from .dre_schemas import DREResponse

router = APIRouter(prefix="/financeiro/dre", tags=["DRE"])


def _dre_para_exportacao(
    *,
    ano: int,
    mes: int,
    mes_inicial: int | None,
    data_final: date | None,
    canais: str,
    db: Session,
    user_and_tenant,
) -> DREResponse:
    """Usa a mesma fonte e os mesmos filtros da DRE exibida por canais."""
    dre_canais = gerar_dre_por_canais(
        ano=ano,
        mes=mes,
        mes_inicial=mes_inicial,
        data_final=data_final,
        canais=canais,
        db=db,
        user_and_tenant=user_and_tenant,
    )
    totais = dre_canais.totais

    def valor_total(campo: str) -> Decimal:
        return Decimal(str(totais.get(campo, 0) or 0))

    def valor_linhas(campo: str) -> Decimal:
        return sum(
            (
                Decimal(str(linha.valor))
                for linha in dre_canais.linhas
                if linha.campo == campo and linha.canal != "total"
            ),
            Decimal("0"),
        )

    despesas_pessoal = valor_linhas("despesas_pessoal")
    despesas_administrativas = valor_linhas("despesas_administrativas")
    taxas_cartao = valor_linhas("taxas_cartao")
    despesas_operacionais = valor_total("despesas_operacionais")
    receita_liquida = valor_total("receita_liquida")
    resultado_operacional = valor_total("resultado_operacional")

    return DREResponse(
        periodo=dre_canais.periodo,
        mes=mes,
        ano=ano,
        receita_bruta=valor_total("receita_bruta"),
        vendas_produtos=valor_total("vendas_produtos"),
        vendas_servicos=valor_total("vendas_servicos"),
        receita_frete=valor_total("receita_frete"),
        outras_receitas=valor_total("outras_receitas"),
        deducoes_total=valor_total("deducoes_total"),
        descontos=valor_total("descontos"),
        devolucoes=valor_total("devolucoes"),
        receita_liquida=receita_liquida,
        cmv=valor_total("cmv"),
        custo_servicos=valor_total("custo_servicos"),
        lucro_bruto=valor_total("lucro_bruto"),
        margem_bruta=float(totais.get("margem_bruta", 0) or 0),
        despesas_operacionais=despesas_operacionais,
        despesas_pessoal=despesas_pessoal,
        despesas_administrativas=despesas_administrativas,
        taxas_cartao=taxas_cartao,
        outras_despesas=(
            despesas_operacionais
            - despesas_pessoal
            - despesas_administrativas
            - taxas_cartao
        ),
        resultado_operacional=resultado_operacional,
        margem_operacional=(
            round(float(resultado_operacional / receita_liquida * 100), 2)
            if receita_liquida > 0
            else 0
        ),
        resultado_financeiro=Decimal("0"),
        receitas_financeiras=Decimal("0"),
        despesas_financeiras=Decimal("0"),
        lucro_liquido=valor_total("lucro_liquido"),
        margem_liquida=float(totais.get("margem_liquida", 0) or 0),
    )


@router.get("/export/pdf")
async def exportar_dre_pdf(
    ano: int = Query(...),
    mes: int = Query(...),
    mes_inicial: int | None = None,
    data_final: date | None = None,
    canais: str = "",
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Exporta DRE para PDF"""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            SimpleDocTemplate,
            Table,
            TableStyle,
            Paragraph,
            Spacer,
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="Biblioteca reportlab não instalada. Execute: pip install reportlab",
        )

    # Buscar dados da DRE
    dre = _dre_para_exportacao(
        ano=ano,
        mes=mes,
        mes_inicial=mes_inicial,
        data_final=data_final,
        canais=canais,
        db=db,
        user_and_tenant=user_and_tenant,
    )

    # Nomes dos meses
    meses = [
        "Janeiro",
        "Fevereiro",
        "Março",
        "Abril",
        "Maio",
        "Junho",
        "Julho",
        "Agosto",
        "Setembro",
        "Outubro",
        "Novembro",
        "Dezembro",
    ]
    mes_nome = meses[mes - 1]

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, topMargin=15 * mm, bottomMargin=15 * mm
    )
    elements = []
    styles = getSampleStyleSheet()

    # Título
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=18,
        textColor=colors.HexColor("#1a56db"),
        spaceAfter=12,
        alignment=TA_CENTER,
    )
    elements.append(
        Paragraph("DEMONSTRAÇÃO DO RESULTADO DO EXERCÍCIO (DRE)", title_style)
    )
    elements.append(Spacer(1, 5 * mm))

    # Período
    subtitle_style = ParagraphStyle(
        "Subtitle", parent=styles["Normal"], fontSize=12, alignment=TA_CENTER
    )
    periodo_text = f"Período: {dre.periodo}"
    elements.append(Paragraph(periodo_text, subtitle_style))
    elements.append(Spacer(1, 10 * mm))

    # Função para formatar moeda
    def formatar_moeda(valor):
        return (
            f"R$ {float(valor):,.2f}".replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

    # Tabela DRE
    dre_data = [
        ["DESCRIÇÃO", "VALOR", "%"],
        ["", "", ""],
        ["RECEITA BRUTA", formatar_moeda(dre.receita_bruta), "100,00%"],
        [
            "  Vendas de Produtos",
            formatar_moeda(dre.vendas_produtos),
            f"{(float(dre.vendas_produtos) / float(dre.receita_bruta) * 100 if float(dre.receita_bruta) > 0 else 0):.2f}%",
        ],
        [
            "  Vendas de Serviços",
            formatar_moeda(dre.vendas_servicos),
            f"{(float(dre.vendas_servicos) / float(dre.receita_bruta) * 100 if float(dre.receita_bruta) > 0 else 0):.2f}%",
        ],
        ["  Receita de Frete", formatar_moeda(dre.receita_frete), ""],
        [
            "  Outras Receitas",
            formatar_moeda(dre.outras_receitas),
            f"{(float(dre.outras_receitas) / float(dre.receita_bruta) * 100 if float(dre.receita_bruta) > 0 else 0):.2f}%",
        ],
        ["", "", ""],
        [
            "(-) DEDUÇÕES",
            formatar_moeda(dre.deducoes_total),
            f"-{(float(dre.deducoes_total) / float(dre.receita_bruta) * 100 if float(dre.receita_bruta) > 0 else 0):.2f}%",
        ],
        ["  Descontos", formatar_moeda(dre.descontos), ""],
        ["  Devoluções de Vendas", formatar_moeda(dre.devolucoes), ""],
        [
            "  Impostos sobre Vendas",
            formatar_moeda(dre.deducoes_total - dre.descontos - dre.devolucoes),
            "",
        ],
        ["", "", ""],
        [
            "(=) RECEITA LÍQUIDA",
            formatar_moeda(dre.receita_liquida),
            f"{(float(dre.receita_liquida) / float(dre.receita_bruta) * 100 if float(dre.receita_bruta) > 0 else 0):.2f}%",
        ],
        ["", "", ""],
        ["(-) CMV (Custo Mercadorias Vendidas)", formatar_moeda(dre.cmv), ""],
        ["(-) Custo dos Serviços Prestados", formatar_moeda(dre.custo_servicos), ""],
        ["", "", ""],
        [
            "(=) LUCRO BRUTO",
            formatar_moeda(dre.lucro_bruto),
            f"{dre.margem_bruta:.2f}%",
        ],
        ["", "", ""],
        ["(-) DESPESAS OPERACIONAIS", formatar_moeda(dre.despesas_operacionais), ""],
        ["  Despesas de Pessoal", formatar_moeda(dre.despesas_pessoal), ""],
        [
            "  Despesas Administrativas",
            formatar_moeda(dre.despesas_administrativas),
            "",
        ],
        ["  Taxas de Cartão", formatar_moeda(dre.taxas_cartao), ""],
        ["  Outras Despesas", formatar_moeda(dre.outras_despesas), ""],
        ["", "", ""],
        [
            "(=) RESULTADO OPERACIONAL",
            formatar_moeda(dre.resultado_operacional),
            f"{dre.margem_operacional:.2f}%",
        ],
        ["", "", ""],
        ["RESULTADO FINANCEIRO", formatar_moeda(dre.resultado_financeiro), ""],
        ["  (+) Receitas Financeiras", formatar_moeda(dre.receitas_financeiras), ""],
        ["  (-) Despesas Financeiras", formatar_moeda(dre.despesas_financeiras), ""],
        ["", "", ""],
        [
            "(=) LUCRO LÍQUIDO",
            formatar_moeda(dre.lucro_liquido),
            f"{dre.margem_liquida:.2f}%",
        ],
    ]

    indices_totais = {
        linha[0]: indice for indice, linha in enumerate(dre_data) if linha and linha[0]
    }
    receita_bruta_idx = indices_totais["RECEITA BRUTA"]
    receita_liquida_idx = indices_totais["(=) RECEITA LÍQUIDA"]
    lucro_bruto_idx = indices_totais["(=) LUCRO BRUTO"]
    resultado_operacional_idx = indices_totais["(=) RESULTADO OPERACIONAL"]
    lucro_liquido_idx = indices_totais["(=) LUCRO LÍQUIDO"]

    dre_table = Table(dre_data, colWidths=[100 * mm, 40 * mm, 30 * mm])
    dre_table.setStyle(
        TableStyle(
            [
                # Cabeçalho
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a56db")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 11),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
                # Totais principais (negrito)
                (
                    "FONTNAME",
                    (0, receita_bruta_idx),
                    (0, receita_bruta_idx),
                    "Helvetica-Bold",
                ),
                (
                    "FONTNAME",
                    (0, receita_liquida_idx),
                    (0, receita_liquida_idx),
                    "Helvetica-Bold",
                ),
                (
                    "FONTNAME",
                    (0, lucro_bruto_idx),
                    (0, lucro_bruto_idx),
                    "Helvetica-Bold",
                ),
                (
                    "FONTNAME",
                    (0, resultado_operacional_idx),
                    (0, resultado_operacional_idx),
                    "Helvetica-Bold",
                ),
                (
                    "FONTNAME",
                    (0, lucro_liquido_idx),
                    (0, lucro_liquido_idx),
                    "Helvetica-Bold",
                ),
                ("FONTSIZE", (0, lucro_liquido_idx), (-1, lucro_liquido_idx), 12),
                # Background nos totais
                (
                    "BACKGROUND",
                    (0, receita_bruta_idx),
                    (-1, receita_bruta_idx),
                    colors.lightblue,
                ),
                (
                    "BACKGROUND",
                    (0, receita_liquida_idx),
                    (-1, receita_liquida_idx),
                    colors.lightgreen,
                ),
                (
                    "BACKGROUND",
                    (0, lucro_bruto_idx),
                    (-1, lucro_bruto_idx),
                    colors.lightyellow,
                ),
                (
                    "BACKGROUND",
                    (0, resultado_operacional_idx),
                    (-1, resultado_operacional_idx),
                    colors.lightcyan,
                ),
                (
                    "BACKGROUND",
                    (0, lucro_liquido_idx),
                    (-1, lucro_liquido_idx),
                    colors.HexColor("#10b981"),
                ),
                (
                    "TEXTCOLOR",
                    (0, lucro_liquido_idx),
                    (-1, lucro_liquido_idx),
                    colors.whitesmoke,
                ),
                # Grid
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
            ]
        )
    )
    elements.append(dre_table)

    # Rodapé
    elements.append(Spacer(1, 10 * mm))
    footer_style = ParagraphStyle(
        "Footer", parent=styles["Normal"], fontSize=8, alignment=TA_CENTER
    )
    elements.append(
        Paragraph(
            f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", footer_style
        )
    )

    # Gerar PDF
    doc.build(elements)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=dre_{mes_nome}_{ano}.pdf"
        },
    )


@router.get("/export/excel")
async def exportar_dre_excel(
    ano: int = Query(...),
    mes: int = Query(...),
    mes_inicial: int | None = None,
    data_final: date | None = None,
    canais: str = "",
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Exporta DRE para Excel"""
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="Biblioteca openpyxl não instalada. Execute: pip install openpyxl",
        )

    # Buscar dados da DRE
    dre = _dre_para_exportacao(
        ano=ano,
        mes=mes,
        mes_inicial=mes_inicial,
        data_final=data_final,
        canais=canais,
        db=db,
        user_and_tenant=user_and_tenant,
    )

    # Nomes dos meses
    meses = [
        "Janeiro",
        "Fevereiro",
        "Março",
        "Abril",
        "Maio",
        "Junho",
        "Julho",
        "Agosto",
        "Setembro",
        "Outubro",
        "Novembro",
        "Dezembro",
    ]
    mes_nome = meses[mes - 1]

    # Criar workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "DRE"

    # Estilos
    title_font = Font(name="Arial", size=14, bold=True, color="1a56db")
    header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(
        start_color="1a56db", end_color="1a56db", fill_type="solid"
    )
    total_font = Font(name="Arial", size=10, bold=True)
    total_fill = PatternFill(
        start_color="E0E0E0", end_color="E0E0E0", fill_type="solid"
    )
    final_fill = PatternFill(
        start_color="10b981", end_color="10b981", fill_type="solid"
    )
    border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    # Título
    ws["A1"] = "DEMONSTRAÇÃO DO RESULTADO DO EXERCÍCIO (DRE)"
    ws["A1"].font = title_font
    ws.merge_cells("A1:C1")
    ws["A1"].alignment = Alignment(horizontal="center")

    # Período
    ws["A2"] = f"Período: {dre.periodo}"
    ws.merge_cells("A2:C2")
    ws["A2"].alignment = Alignment(horizontal="center")

    # Cabeçalho
    row = 4
    ws[f"A{row}"] = "DESCRIÇÃO"
    ws[f"B{row}"] = "VALOR"
    ws[f"C{row}"] = "%"
    for col in ["A", "B", "C"]:
        ws[f"{col}{row}"].font = header_font
        ws[f"{col}{row}"].fill = header_fill
        ws[f"{col}{row}"].border = border
        ws[f"{col}{row}"].alignment = Alignment(horizontal="center")

    # Função para adicionar linha
    def add_row(descricao, valor, percentual="", is_total=False, is_final=False):
        nonlocal row
        row += 1
        ws[f"A{row}"] = descricao
        ws[f"B{row}"] = float(valor) if valor else ""
        ws[f"C{row}"] = percentual

        # Aplicar estilos
        if is_final:
            for col in ["A", "B", "C"]:
                ws[f"{col}{row}"].font = Font(bold=True, color="FFFFFF")
                ws[f"{col}{row}"].fill = final_fill
        elif is_total:
            for col in ["A", "B", "C"]:
                ws[f"{col}{row}"].font = total_font
                ws[f"{col}{row}"].fill = total_fill

        for col in ["A", "B", "C"]:
            ws[f"{col}{row}"].border = border

        ws[f"B{row}"].number_format = "R$ #,##0.00"
        ws[f"B{row}"].alignment = Alignment(horizontal="right")
        ws[f"C{row}"].alignment = Alignment(horizontal="right")

    # Dados da DRE
    add_row("RECEITA BRUTA", dre.receita_bruta, "100,00%", is_total=True)
    add_row(
        "  Vendas de Produtos",
        dre.vendas_produtos,
        f"{(float(dre.vendas_produtos) / float(dre.receita_bruta) * 100 if float(dre.receita_bruta) > 0 else 0):.2f}%",
    )
    add_row(
        "  Vendas de Serviços",
        dre.vendas_servicos,
        f"{(float(dre.vendas_servicos) / float(dre.receita_bruta) * 100 if float(dre.receita_bruta) > 0 else 0):.2f}%",
    )
    add_row("  Receita de Frete", dre.receita_frete)
    add_row(
        "  Outras Receitas",
        dre.outras_receitas,
        f"{(float(dre.outras_receitas) / float(dre.receita_bruta) * 100 if float(dre.receita_bruta) > 0 else 0):.2f}%",
    )
    row += 1  # Linha em branco
    add_row(
        "(-) DEDUÇÕES",
        dre.deducoes_total,
        f"-{(float(dre.deducoes_total) / float(dre.receita_bruta) * 100 if float(dre.receita_bruta) > 0 else 0):.2f}%",
    )
    add_row("  Descontos", dre.descontos)
    add_row("  Devoluções de Vendas", dre.devolucoes)
    add_row(
        "  Impostos sobre Vendas", dre.deducoes_total - dre.descontos - dre.devolucoes
    )
    row += 1
    add_row(
        "(=) RECEITA LÍQUIDA",
        dre.receita_liquida,
        f"{(float(dre.receita_liquida) / float(dre.receita_bruta) * 100 if float(dre.receita_bruta) > 0 else 0):.2f}%",
        is_total=True,
    )
    row += 1
    add_row("(-) CMV (Custo Mercadorias Vendidas)", dre.cmv)
    add_row("(-) Custo dos Serviços Prestados", dre.custo_servicos)
    row += 1
    add_row(
        "(=) LUCRO BRUTO", dre.lucro_bruto, f"{dre.margem_bruta:.2f}%", is_total=True
    )
    row += 1
    add_row("(-) DESPESAS OPERACIONAIS", dre.despesas_operacionais)
    add_row("  Despesas de Pessoal", dre.despesas_pessoal)
    add_row("  Despesas Administrativas", dre.despesas_administrativas)
    add_row("  Taxas de Cartão", dre.taxas_cartao)
    add_row("  Outras Despesas", dre.outras_despesas)
    row += 1
    add_row(
        "(=) RESULTADO OPERACIONAL",
        dre.resultado_operacional,
        f"{dre.margem_operacional:.2f}%",
        is_total=True,
    )
    row += 1
    add_row("RESULTADO FINANCEIRO", dre.resultado_financeiro)
    add_row("  (+) Receitas Financeiras", dre.receitas_financeiras)
    add_row("  (-) Despesas Financeiras", dre.despesas_financeiras)
    row += 1
    add_row(
        "(=) LUCRO LÍQUIDO",
        dre.lucro_liquido,
        f"{dre.margem_liquida:.2f}%",
        is_final=True,
    )

    # Ajustar largura das colunas
    ws.column_dimensions["A"].width = 40
    ws.column_dimensions["B"].width = 20
    ws.column_dimensions["C"].width = 15

    # Salvar em buffer
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=dre_{mes_nome}_{ano}.xlsx"
        },
    )
