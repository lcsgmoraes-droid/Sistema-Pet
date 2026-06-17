"""
Seed Data - Templates de Adquirentes

Criar templates básicos para Stone, Cielo e Rede.
Usuário não precisa cadastrar manualmente.
"""

import json

from sqlalchemy.orm import Session
from app.financeiro_models import TemplateAdquirente


def criar_templates_adquirentes(db: Session, tenant_id: str):
    """
    Cria templates básicos de parsing para operadoras.

    Executar UMA VEZ ao inicializar sistema ou tenant.
    """

    templates = [
        # ========================================
        # STONE - Template v1.0
        # ========================================
        {
            "nome_adquirente": "STONE",
            "tipo_relatorio": "recebimentos",
            "auto_aplicar": True,
            "palavras_chave": ["STONE ID", "DATA DA VENDA", "VALOR LIQUIDO"],
            "colunas_obrigatorias": [
                "STONE ID",
                "DATA DA VENDA",
                "VALOR BRUTO",
                "VALOR LIQUIDO",
            ],
            "mapeamento": {
                "separador": ";",
                "encoding": "utf-8",
                "tem_header": True,
                "pular_linhas": 0,
                "nsu": {
                    "coluna": "STONE ID",
                    "transformacao": "nsu",
                    "obrigatorio": True,
                },
                "data_venda": {
                    "coluna": "DATA DA VENDA",
                    "transformacao": "data_br",
                    "obrigatorio": True,
                },
                "data_pagamento": {
                    "coluna": "DATA DO ULTIMO STATUS",
                    "transformacao": "data_br",
                    "obrigatorio": False,
                },
                "valor_bruto": {
                    "coluna": "VALOR BRUTO",
                    "transformacao": "monetario_br",
                    "obrigatorio": True,
                },
                "taxa_mdr": {
                    "coluna": "DESCONTO DE MDR",
                    "transformacao": "monetario_br",
                    "obrigatorio": False,
                },
                "valor_taxa": {
                    "coluna": "DESCONTO UNIFICADO",
                    "transformacao": "monetario_br",
                    "obrigatorio": False,
                },
                "valor_liquido": {
                    "coluna": "VALOR LIQUIDO",
                    "transformacao": "monetario_br",
                    "obrigatorio": True,
                },
                "parcelas": {
                    "coluna": "N DE PARCELAS",
                    "transformacao": "inteiro",
                    "obrigatorio": False,
                },
                "tipo_transacao": {
                    "coluna": "PRODUTO",
                    "transformacao": "texto",
                    "obrigatorio": False,
                },
                "bandeira": {
                    "coluna": "BANDEIRA",
                    "transformacao": "texto",
                    "obrigatorio": False,
                },
            },
            "transformacoes": {
                "monetario_br": "R$ 1.234,56 -> Decimal",
                "percentual": "2.5% -> Decimal(2.5)",
                "data_br": "15/03/2025 -> datetime",
                "nsu": "Remove espaços e caracteres especiais",
                "texto": "Mantém como está",
            },
        },
        # ========================================
        # CIELO - Template v1.0
        # ========================================
        {
            "nome_adquirente": "CIELO",
            "tipo_relatorio": "recebimentos",
            "auto_aplicar": True,
            "palavras_chave": ["NSU", "DT_VENDA", "VLR_LIQUIDO"],
            "colunas_obrigatorias": ["NSU", "DT_VENDA", "VLR_BRUTO", "VLR_LIQUIDO"],
            "mapeamento": {
                "separador": ",",
                "encoding": "latin1",
                "tem_header": True,
                "pular_linhas": 0,
                "nsu": {"coluna": "NSU", "transformacao": "nsu", "obrigatorio": True},
                "data_venda": {
                    "coluna": "DT_VENDA",
                    "transformacao": "data_us",  # YYYY-MM-DD
                    "obrigatorio": True,
                },
                "data_pagamento": {
                    "coluna": "DT_PAGAMENTO",
                    "transformacao": "data_us",
                    "obrigatorio": False,
                },
                "valor_bruto": {
                    "coluna": "VLR_BRUTO",
                    "transformacao": "monetario_us",  # 1234.56
                    "obrigatorio": True,
                },
                "taxa_mdr": {
                    "coluna": "TAXA_CLIENTE",
                    "transformacao": "percentual",
                    "obrigatorio": False,
                },
                "valor_liquido": {
                    "coluna": "VLR_LIQUIDO",
                    "transformacao": "monetario_us",
                    "obrigatorio": True,
                },
                "parcela": {
                    "coluna": "PARCELA",
                    "transformacao": "texto",
                    "obrigatorio": False,
                },
                "tipo_transacao": {
                    "coluna": "TIPO_TRANSACAO",
                    "transformacao": "texto",
                    "obrigatorio": False,
                },
                "bandeira": {
                    "coluna": "PRODUTO",
                    "transformacao": "texto",
                    "obrigatorio": False,
                },
            },
            "transformacoes": {
                "monetario_us": "1234.56 -> Decimal",
                "percentual": "2.5 -> Decimal(2.5)",
                "data_us": "2025-03-15 -> datetime",
                "nsu": "Remove espaços e caracteres especiais",
                "texto": "Mantém como está",
            },
        },
        # ========================================
        # REDE - Template v1.0
        # ========================================
        {
            "nome_adquirente": "REDE",
            "tipo_relatorio": "recebimentos",
            "auto_aplicar": True,
            "palavras_chave": ["NSU", "Data da Venda", "Valor a Receber"],
            "colunas_obrigatorias": [
                "NSU",
                "Data da Venda",
                "Valor da Transação",
                "Valor a Receber",
            ],
            "mapeamento": {
                "separador": ";",
                "encoding": "utf-8",
                "tem_header": True,
                "pular_linhas": 1,  # Pula primeira linha (cabeçalho extra)
                "nsu": {"coluna": "NSU", "transformacao": "nsu", "obrigatorio": True},
                "data_venda": {
                    "coluna": "Data da Venda",
                    "transformacao": "data_br",
                    "obrigatorio": True,
                },
                "data_pagamento": {
                    "coluna": "Data do Pagamento",
                    "transformacao": "data_br",
                    "obrigatorio": False,
                },
                "valor_bruto": {
                    "coluna": "Valor da Transação",
                    "transformacao": "monetario_br",
                    "obrigatorio": True,
                },
                "taxa_mdr": {
                    "coluna": "Taxa Percentual",
                    "transformacao": "percentual",
                    "obrigatorio": False,
                },
                "valor_liquido": {
                    "coluna": "Valor a Receber",
                    "transformacao": "monetario_br",
                    "obrigatorio": True,
                },
                "parcela": {
                    "coluna": "Parcela",
                    "transformacao": "texto",
                    "obrigatorio": False,
                },
                "tipo_transacao": {
                    "coluna": "Tipo",
                    "transformacao": "texto",
                    "obrigatorio": False,
                },
                "bandeira": {
                    "coluna": "Bandeira do Cartão",
                    "transformacao": "texto",
                    "obrigatorio": False,
                },
            },
            "transformacoes": {
                "monetario_br": "R$ 1.234,56 -> Decimal",
                "percentual": "2,5% -> Decimal(2.5)",
                "data_br": "15/03/2025 -> datetime",
                "nsu": "Remove espaços e caracteres especiais",
                "texto": "Mantém como está",
            },
        },
    ]

    templates_criados = []

    for template_data in templates:
        # Verificar se já existe
        existente = (
            db.query(TemplateAdquirente)
            .filter(
                TemplateAdquirente.tenant_id == tenant_id,
                TemplateAdquirente.nome_adquirente == template_data["nome_adquirente"],
                TemplateAdquirente.tipo_relatorio == template_data["tipo_relatorio"],
            )
            .first()
        )

        if not existente:
            template = TemplateAdquirente(
                tenant_id=tenant_id,
                nome_adquirente=template_data["nome_adquirente"],
                tipo_relatorio=template_data["tipo_relatorio"],
                mapeamento=json.dumps(template_data["mapeamento"], ensure_ascii=False),
                palavras_chave=json.dumps(
                    template_data["palavras_chave"], ensure_ascii=False
                ),
                colunas_obrigatorias=json.dumps(
                    template_data["colunas_obrigatorias"],
                    ensure_ascii=False,
                ),
                auto_aplicar=template_data["auto_aplicar"],
            )
            db.add(template)
            templates_criados.append(template_data["nome_adquirente"])

    db.commit()

    return {"total_criados": len(templates_criados), "adquirentes": templates_criados}


# ========================================
# EXEMPLO DE CSV - STONE
# ========================================
"""
NSU;Data Transação;Data Pagamento;Valor Bruto;Taxa MDR %;Valor Taxa;Valor Líquido;Parcela;Tipo;Bandeira
123456;15/03/2025;16/03/2025;R$ 1.500,00;2,5%;R$ 37,50;R$ 1.462,50;1/1;Débito;Visa
123457;15/03/2025;16/03/2025;R$ 800,00;3,0%;R$ 24,00;R$ 776,00;1/1;Débito;Mastercard
123458;16/03/2025;16/04/2025;R$ 2.000,00;2,5%;R$ 50,00;R$ 1.950,00;1/1;Crédito à Vista;Visa
123459;16/03/2025;16/05/2025;R$ 1.200,00;5,2%;R$ 62,40;R$ 1.137,60;1/3;Crédito Parcelado;Elo
123460;16/03/2025;16/06/2025;R$ 1.200,00;5,2%;R$ 62,40;R$ 1.137,60;2/3;Crédito Parcelado;Elo
123461;16/03/2025;16/07/2025;R$ 1.200,00;5,2%;R$ 62,40;R$ 1.137,60;3/3;Crédito Parcelado;Elo
"""

# ========================================
# EXEMPLO DE CSV - CIELO
# ========================================
"""
NSU,DT_VENDA,DT_PAGAMENTO,VLR_BRUTO,TAXA_CLIENTE,VLR_LIQUIDO,PARCELA,TIPO_TRANSACAO,PRODUTO
123456,2025-03-15,2025-03-16,1500.00,2.5,1462.50,1/1,DEBITO,VISA
123457,2025-03-15,2025-03-16,800.00,3.0,776.00,1/1,DEBITO,MASTERCARD
123458,2025-03-16,2025-04-16,2000.00,2.5,1950.00,1/1,CREDITO_AV,VISA
"""
