import pdfplumber

from app.pdf_caixa import gerar_pdf_fechamento_caixa


def test_pdf_fechamento_mostra_vendido_recebido_formas_e_saldo_zerado():
    pdf = gerar_pdf_fechamento_caixa(
        {
            "numero_caixa": 7,
            "status": "fechado",
            "saldo_inicial": 50,
            "total_vendido": 230,
            "total_vendas_crediario": 35,
            "total_recebido": 180,
            "vendas_por_forma_pagamento": {
                "Dinheiro": {"total": 80},
                "PIX": {"total": 100},
                "Crediário": {"total": 35},
                "Boleto": {"total": 15},
            },
            "recebimentos_por_forma_pagamento": {
                "Dinheiro": {"total": 80},
                "PIX": {"total": 100},
            },
            "totais": {
                "vendas": 80,
                "suprimentos": 20,
                "sangrias": 145,
                "despesas": 5,
                "devolucoes": 0,
                "transferencias": 0,
                "saldo_atual": 0,
            },
            "saldo_fechamento": 0,
            "diferenca": 0,
        },
        [
            {
                "tipo": "suprimento",
                "descricao": None,
                "forma_pagamento_nome": None,
                "valor": 20,
            }
        ],
    )
    with pdfplumber.open(pdf) as documento:
        texto = " ".join(page.extract_text() or "" for page in documento.pages)

    for trecho in (
        "Vendas vinculadas ao caixa",
        "Crediário das vendas vinculadas",
        "Quitações registradas no caixa",
        "R$ 230,00",
        "R$ 35,00",
        "R$ 180,00",
        "PIX",
        "dados legados",
        "Suprimentos",
        "Sangrias",
        "Saldo declarado",
        "Diferença",
    ):
        assert trecho.lower() in texto.lower()
    assert texto.index("Vendas vinculadas ao caixa") < texto.index(
        "Crediário das vendas vinculadas"
    )
    assert texto.index("Crediário das vendas vinculadas") < texto.index(
        "Quitações registradas no caixa"
    )


def test_pdf_separa_faturamento_liquido_recebimentos_anteriores_e_beneficios():
    pdf = gerar_pdf_fechamento_caixa(
        {
            "numero_caixa": 2,
            "status": "fechado",
            "saldo_inicial": 100,
            # Legados distintos: a impressão deve usar o contrato novo.
            "total_vendido": 500,
            "total_recebido": 500,
            "vendas_por_forma_pagamento": {"Cashback": {"total": 5}},
            "vendas_periodo": {
                "data_inicio": "2026-10-09",
                "data_fim": "2026-10-09",
                "faturamento_bruto": 220,
                "descontos": 10,
                "devolucoes": 25,
                "faturamento_liquido": 185,
                "taxa_entrega": 15,
                "total_vendas": 200,
                "valor_pago": 125,
                "creditos_utilizados": 5,
                "crediario_receber": 50,
                "em_aberto": 20,
            },
            "composicao_recebimentos": {
                "data_inicio": "2026-10-09",
                "data_fim": "2026-10-09",
                "vendas_periodo": 150,
                "vendas_anteriores": 60,
                "devolucoes": 25,
                "total_recebido": 185,
                "creditos_utilizados": 5,
                "por_forma_pagamento": {
                    "Dinheiro": {"total": 35},
                    "PIX": {"total": 150},
                },
            },
            "totais": {"vendas": 60, "devolucoes": 25, "saldo_atual": 135},
        },
        [],
    )
    with pdfplumber.open(pdf) as documento:
        texto = " ".join(page.extract_text() or "" for page in documento.pages)
    for trecho in (
        "Vendas de 09/10/2026 - empresa inteira",
        "Faturamento líquido (vendas - descontos - devoluções)",
        "R$ 185,00",
        "R$ 10,00",
        "De outras datas ou sem data",
        "R$ 60,00",
        "R$ 5,00",
        "Crediário a receber",
        "Em aberto sem crediário",
        "Total das formas de recebimento",
    ):
        assert trecho in texto
    assert "R$ 500,00" not in texto
    assert "Cashback" not in texto
