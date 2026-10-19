from pypdf import PdfReader

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
    texto = " ".join(page.extract_text() for page in PdfReader(pdf).pages)

    for trecho in (
        "Total vendido no caixa",
        "Vendas no crediário",
        "Total recebido no caixa",
        "R$ 230,00",
        "R$ 35,00",
        "R$ 180,00",
        "PIX",
        "a prazo",
        "Suprimentos",
        "Sangrias",
        "Saldo declarado",
        "Diferença",
    ):
        assert trecho.lower() in texto.lower()
    assert texto.index("Total vendido no caixa") < texto.index("Vendas no crediário")
    assert texto.index("Vendas no crediário") < texto.index("Total recebido no caixa")
