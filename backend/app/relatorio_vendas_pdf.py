"""Exportacao PDF do relatorio de vendas."""

from datetime import datetime
from io import BytesIO
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from .auth.dependencies import get_current_user_and_tenant
from .db import get_session
from .relatorio_vendas_common import _normalizar_canal_venda_relatorio
from .vendas_models import Venda, VendaItem, VendaPagamento


router = APIRouter()


@router.get("/vendas/export/pdf")
async def exportar_vendas_pdf(
    data_inicio: Optional[str] = Query(None),
    data_fim: Optional[str] = Query(None),
    funcionario: Optional[str] = Query(None),
    forma_pagamento: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None),
    canal_venda: Optional[str] = Query(None),
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Exporta relatório de vendas para PDF"""
    from fastapi import HTTPException
    import logging
    import traceback

    logger = logging.getLogger(__name__)
    _current_user, tenant_id = user_and_tenant

    try:
        from reportlab.lib.pagesizes import A4, landscape
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
    except ImportError as e:
        logger.error(f"Erro ao importar reportlab: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Biblioteca reportlab não instalada. Execute: pip install reportlab",
        )

    # Buscar dados do relatório - obter_relatorio_vendas retorna um dict diretamente
    try:
        logger.info("Gerando PDF de vendas")
        # Construir filtros de data
        if not data_inicio:
            data_inicio = datetime.now().replace(day=1).strftime("%Y-%m-%d")
        if not data_fim:
            data_fim = datetime.now().strftime("%Y-%m-%d")
        canal_normalizado = _normalizar_canal_venda_relatorio(canal_venda)

        # Buscar todas as vendas do período com filtro de tenant
        filtros_vendas = [
            Venda.tenant_id == tenant_id,
            func.date(Venda.data_venda) >= data_inicio,
            func.date(Venda.data_venda) <= data_fim,
            or_(Venda.status.is_(None), Venda.status != "cancelada"),
        ]
        if canal_normalizado:
            filtros_vendas.append(Venda.canal == canal_normalizado)

        vendas_query = db.query(Venda).filter(and_(*filtros_vendas))

        vendas = vendas_query.all()

        # Calcular resumo
        venda_bruta = sum(float(v.subtotal or 0) for v in vendas)
        taxa_entrega = sum(float(v.taxa_entrega or 0) for v in vendas)
        desconto = sum(float(v.desconto_valor or 0) for v in vendas)
        venda_liquida = sum(float(v.total or 0) for v in vendas)
        em_aberto = sum(float(v.total or 0) for v in vendas if v.status == "aberta")
        quantidade_vendas = len(vendas)

        resumo = {
            "venda_bruta": venda_bruta,
            "taxa_entrega": taxa_entrega,
            "desconto": desconto,
            "venda_liquida": venda_liquida,
            "em_aberto": em_aberto,
            "quantidade_vendas": quantidade_vendas,
        }

        # Agrupar vendas por data
        vendas_por_data_dict = {}
        for v in vendas:
            data_str = (
                v.data_venda.strftime("%Y-%m-%d")
                if isinstance(v.data_venda, datetime)
                else str(v.data_venda)
            )
            if data_str not in vendas_por_data_dict:
                vendas_por_data_dict[data_str] = {
                    "data": data_str,
                    "quantidade": 0,
                    "valor_bruto": 0,
                    "taxa_entrega": 0,
                    "desconto": 0,
                    "valor_liquido": 0,
                    "valor_recebido": 0,
                    "saldo_aberto": 0,
                }
            vendas_por_data_dict[data_str]["quantidade"] += 1
            vendas_por_data_dict[data_str]["valor_bruto"] += float(v.subtotal or 0)
            vendas_por_data_dict[data_str]["taxa_entrega"] += float(v.taxa_entrega or 0)
            vendas_por_data_dict[data_str]["desconto"] += float(v.desconto_valor or 0)
            vendas_por_data_dict[data_str]["valor_liquido"] += float(v.total or 0)
            if v.status != "aberta":
                vendas_por_data_dict[data_str]["valor_recebido"] += float(v.total or 0)
            else:
                vendas_por_data_dict[data_str]["saldo_aberto"] += float(v.total or 0)

        vendas_por_data = list(vendas_por_data_dict.values())
        for v in vendas_por_data:
            v["ticket_medio"] = (
                v["valor_liquido"] / v["quantidade"] if v["quantidade"] > 0 else 0
            )

        # Formas de recebimento
        formas_dict = {}
        for v in vendas:
            pagamentos = (
                db.query(VendaPagamento)
                .filter(
                    and_(
                        VendaPagamento.venda_id == v.id,
                        VendaPagamento.tenant_id == tenant_id,
                    )
                )
                .all()
            )
            for p in pagamentos:
                forma = p.forma_pagamento or "Não informado"
                if forma not in formas_dict:
                    formas_dict[forma] = 0
                formas_dict[forma] += p.valor or 0

        formas_recebimento = [
            {"forma_pagamento": k, "valor_total": v} for k, v in formas_dict.items()
        ]

        # Vendas por funcionário
        func_dict = {}
        for v in vendas:
            func_nome = v.vendedor.nome if v.vendedor else "Sem registro"
            if func_nome not in func_dict:
                func_dict[func_nome] = {
                    "funcionario": func_nome,
                    "quantidade": 0,
                    "valor_total": 0,
                }
            func_dict[func_nome]["quantidade"] += 1
            func_dict[func_nome]["valor_total"] += float(v.total or 0)

        vendas_por_funcionario = list(func_dict.values())
        for f in vendas_por_funcionario:
            f["ticket_medio"] = (
                f["valor_total"] / f["quantidade"] if f["quantidade"] > 0 else 0
            )

        # Produtos detalhados
        prod_dict = {}
        for v in vendas:
            itens = (
                db.query(VendaItem)
                .filter(
                    and_(VendaItem.venda_id == v.id, VendaItem.tenant_id == tenant_id)
                )
                .all()
            )
            for item in itens:
                prod_nome = item.produto.nome if item.produto else "Produto sem nome"
                if prod_nome not in prod_dict:
                    prod_dict[prod_nome] = {
                        "produto": prod_nome,
                        "nome": prod_nome,
                        "quantidade": 0,
                        "valor_total": 0,
                        "custo_total": 0,
                        "marca": item.produto.marca.nome
                        if (item.produto and item.produto.marca)
                        else None,
                        "categoria": item.produto.categoria.nome
                        if (item.produto and item.produto.categoria)
                        else None,
                    }
                prod_dict[prod_nome]["quantidade"] += float(item.quantidade or 0)
                prod_dict[prod_nome]["valor_total"] += float(item.subtotal or 0)
                # Adicionar custo do produto
                if item.produto and item.produto.preco_custo:
                    prod_dict[prod_nome]["custo_total"] += float(
                        item.produto.preco_custo
                    ) * float(item.quantidade or 0)

        produtos_detalhados = sorted(
            list(prod_dict.values()), key=lambda x: x["valor_total"], reverse=True
        )

        logger.info(
            f"Dados carregados: {len(vendas)} vendas, {len(produtos_detalhados)} produtos"
        )

    except Exception as e:
        logger.error(f"Erro ao buscar dados: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Erro ao buscar dados: {str(e)}")

    # Aplicar filtros se fornecidos
    if funcionario:
        vendas_por_funcionario = [
            v for v in vendas_por_funcionario if v.get("funcionario") == funcionario
        ]
    if forma_pagamento:
        formas_recebimento = [
            f for f in formas_recebimento if f.get("forma_pagamento") == forma_pagamento
        ]

    # Gerar PDF
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=landscape(A4), topMargin=15 * mm, bottomMargin=15 * mm
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
        elements.append(Paragraph("RELATÓRIO DE VENDAS", title_style))
        elements.append(Spacer(1, 5 * mm))

        # Período
        subtitle_style = ParagraphStyle(
            "Subtitle", parent=styles["Normal"], fontSize=11, alignment=TA_CENTER
        )
        periodo_text = f"Período: {data_inicio} até {data_fim}"
        elements.append(Paragraph(periodo_text, subtitle_style))
        elements.append(Spacer(1, 8 * mm))

        # Resumo Financeiro
        header_style = ParagraphStyle(
            "Header",
            parent=styles["Heading2"],
            fontSize=14,
            textColor=colors.HexColor("#1a56db"),
            spaceAfter=6,
        )
        elements.append(Paragraph("Resumo Financeiro", header_style))

        resumo_data = [
            ["Métrica", "Valor"],
            [
                "Venda Bruta",
                f"R$ {resumo['venda_bruta']:,.2f}".replace(",", "X")
                .replace(".", ",")
                .replace("X", "."),
            ],
            [
                "Taxa de Entrega",
                f"R$ {resumo['taxa_entrega']:,.2f}".replace(",", "X")
                .replace(".", ",")
                .replace("X", "."),
            ],
            [
                "Desconto",
                f"R$ {resumo['desconto']:,.2f}".replace(",", "X")
                .replace(".", ",")
                .replace("X", "."),
            ],
            [
                "Venda Líquida",
                f"R$ {resumo['venda_liquida']:,.2f}".replace(",", "X")
                .replace(".", ",")
                .replace("X", "."),
            ],
            [
                "Valor Recebido",
                f"R$ {resumo['venda_liquida'] - resumo['em_aberto']:,.2f}".replace(
                    ",", "X"
                )
                .replace(".", ",")
                .replace("X", "."),
            ],
            [
                "Em Aberto",
                f"R$ {resumo['em_aberto']:,.2f}".replace(",", "X")
                .replace(".", ",")
                .replace("X", "."),
            ],
            ["Quantidade de Vendas", str(resumo["quantidade_vendas"])],
        ]

        resumo_table = Table(resumo_data, colWidths=[60 * mm, 40 * mm])
        resumo_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3b82f6")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("ALIGN", (1, 1), (1, -1), "RIGHT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTSIZE", (0, 1), (-1, -1), 9),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.lightgrey],
                    ),
                ]
            )
        )
        elements.append(resumo_table)
        elements.append(Spacer(1, 10 * mm))

        # Vendas por Data (se houver)
        if vendas_por_data:
            elements.append(Paragraph("Vendas por Data", header_style))

            vendas_data_list = [
                [
                    "Data",
                    "Qtd",
                    "Tkt Médio",
                    "Vl Bruto",
                    "Taxa",
                    "Desc.",
                    "Vl Líq.",
                    "Recebido",
                    "Aberto",
                ]
            ]
            for v in vendas_por_data[:10]:  # Limitar a 10 linhas para caber na página
                vendas_data_list.append(
                    [
                        v["data"],
                        str(v["quantidade"]),
                        f"R$ {v['ticket_medio']:,.2f}".replace(",", "X")
                        .replace(".", ",")
                        .replace("X", "."),
                        f"R$ {v['valor_bruto']:,.2f}".replace(",", "X")
                        .replace(".", ",")
                        .replace("X", "."),
                        f"R$ {v['taxa_entrega']:,.2f}".replace(",", "X")
                        .replace(".", ",")
                        .replace("X", "."),
                        f"R$ {v['desconto']:,.2f}".replace(",", "X")
                        .replace(".", ",")
                        .replace("X", "."),
                        f"R$ {v['valor_liquido']:,.2f}".replace(",", "X")
                        .replace(".", ",")
                        .replace("X", "."),
                        f"R$ {v['valor_recebido']:,.2f}".replace(",", "X")
                        .replace(".", ",")
                        .replace("X", "."),
                        f"R$ {v['saldo_aberto']:,.2f}".replace(",", "X")
                        .replace(".", ",")
                        .replace("X", "."),
                    ]
                )

            vendas_table = Table(
                vendas_data_list,
                colWidths=[
                    22 * mm,
                    12 * mm,
                    22 * mm,
                    22 * mm,
                    18 * mm,
                    18 * mm,
                    22 * mm,
                    22 * mm,
                    22 * mm,
                ],
            )
            vendas_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#10b981")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 8),
                        ("FONTSIZE", (0, 1), (-1, -1), 7),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [colors.white, colors.lightgrey],
                        ),
                    ]
                )
            )
            elements.append(vendas_table)
            elements.append(Spacer(1, 10 * mm))

        # Formas de Pagamento
        if formas_recebimento:
            elements.append(Paragraph("Formas de Pagamento", header_style))

            formas_data_list = [["Forma de Pagamento", "Valor Total"]]
            for f in formas_recebimento:
                formas_data_list.append(
                    [
                        f["forma_pagamento"],
                        f"R$ {f['valor_total']:,.2f}".replace(",", "X")
                        .replace(".", ",")
                        .replace("X", "."),
                    ]
                )

            formas_table = Table(formas_data_list, colWidths=[80 * mm, 40 * mm])
            formas_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f59e0b")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (0, -1), "LEFT"),
                        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 10),
                        ("FONTSIZE", (0, 1), (-1, -1), 9),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [colors.white, colors.lightgrey],
                        ),
                    ]
                )
            )
            elements.append(formas_table)
            elements.append(Spacer(1, 10 * mm))

        # Vendas por Funcionário
        if vendas_por_funcionario:
            elements.append(Paragraph("Vendas por Funcionário", header_style))

            func_data_list = [
                ["Funcionário", "Qtd Vendas", "Valor Total", "Ticket Médio"]
            ]
            for f in vendas_por_funcionario[:10]:
                func_data_list.append(
                    [
                        f.get("funcionario", "Sem registro"),
                        str(f["quantidade"]),
                        f"R$ {f['valor_total']:,.2f}".replace(",", "X")
                        .replace(".", ",")
                        .replace("X", "."),
                        f"R$ {f['ticket_medio']:,.2f}".replace(",", "X")
                        .replace(".", ",")
                        .replace("X", "."),
                    ]
                )

            func_table = Table(
                func_data_list, colWidths=[80 * mm, 25 * mm, 35 * mm, 35 * mm]
            )
            func_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#8b5cf6")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (0, -1), "LEFT"),
                        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                        ("ALIGN", (2, 1), (3, -1), "RIGHT"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 10),
                        ("FONTSIZE", (0, 1), (-1, -1), 9),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [colors.white, colors.lightgrey],
                        ),
                    ]
                )
            )
            elements.append(func_table)
            elements.append(Spacer(1, 10 * mm))

        # Produtos Mais Vendidos (Top 20)
        if produtos_detalhados:
            elements.append(Paragraph("Produtos Mais Vendidos (Top 20)", header_style))

            prod_data_list = [["Produto", "Qtd", "Valor Total"]]
            for p in produtos_detalhados[:20]:
                prod_data_list.append(
                    [
                        p.get("produto", "Produto sem nome"),
                        str(p["quantidade"]),
                        f"R$ {p['valor_total']:,.2f}".replace(",", "X")
                        .replace(".", ",")
                        .replace("X", "."),
                    ]
                )

            prod_table = Table(prod_data_list, colWidths=[120 * mm, 20 * mm, 35 * mm])
            prod_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ec4899")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (0, -1), "LEFT"),
                        ("ALIGN", (1, 0), (1, -1), "CENTER"),
                        ("ALIGN", (2, 0), (2, -1), "RIGHT"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 10),
                        ("FONTSIZE", (0, 1), (-1, -1), 9),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [colors.white, colors.lightgrey],
                        ),
                    ]
                )
            )
            elements.append(prod_table)

        # Rodapé
        footer_style = ParagraphStyle(
            "Footer", parent=styles["Normal"], fontSize=8, alignment=TA_CENTER
        )
        elements.append(Spacer(1, 10 * mm))
        elements.append(
            Paragraph(
                f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
                footer_style,
            )
        )

        # Gerar PDF
        doc.build(elements)
        buffer.seek(0)

        logger.info("PDF gerado com sucesso")

        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=relatorio_vendas_{data_inicio}_{data_fim}.pdf"
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao gerar PDF: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Erro ao gerar PDF: {str(e)}")
