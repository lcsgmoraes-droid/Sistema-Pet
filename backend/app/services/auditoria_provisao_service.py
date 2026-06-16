"""
Serviço de Auditoria: Provisão × Realizado
Compara valores provisionados vs pagos para controle fiscal e trabalhista
"""

from sqlalchemy import func, extract
from sqlalchemy.orm import Session
from decimal import Decimal
from typing import List, Dict

from app.financeiro_models import CategoriaFinanceira, ContaPagar


# Mapa de auditoria: categorias de provisão e realizado
MAPA_AUDITORIA = [
    {
        "nome": "Simples Nacional",
        "provisao_nomes": ["Provisão Simples Nacional", "Simples Nacional - Provisão"],
        "real_nomes": ["DAS - Simples Nacional", "DAS", "Simples Nacional Pago"],
    },
    {
        "nome": "INSS",
        "provisao_nomes": ["Provisão INSS", "INSS - Provisão"],
        "real_nomes": ["INSS", "INSS Pago"],
    },
    {
        "nome": "FGTS",
        "provisao_nomes": ["Provisão FGTS", "FGTS - Provisão"],
        "real_nomes": ["FGTS", "FGTS Pago"],
    },
    {
        "nome": "Folha de Pagamento",
        "provisao_nomes": ["Provisão Folha", "Folha - Provisão"],
        "real_nomes": ["Folha de Pagamento", "Salários"],
    },
    {
        "nome": "Férias",
        "provisao_nomes": ["Provisão Férias", "Provisão Férias 1/3"],
        "real_nomes": ["Férias Pagas"],
    },
    {
        "nome": "13º Salário",
        "provisao_nomes": ["Provisão 13º", "Provisão Décimo Terceiro"],
        "real_nomes": ["13º Salário", "Décimo Terceiro"],
    },
]


def auditar_provisoes(db: Session, tenant_id: int, mes: int, ano: int) -> List[Dict]:
    """
    Gera relatório de auditoria comparando provisões vs realizado.

    Busca dados de ContaPagar filtrando por:
    - Categorias de provisão (estimado)
    - Categorias de realizado (pago)

    Args:
        db: Sessão do banco
        tenant_id: ID do tenant
        mes: Mês de competência
        ano: Ano de competência

    Returns:
        Lista de dicts com: item, provisao, realizado, diferenca, status
    """

    resultado = []

    for item in MAPA_AUDITORIA:
        # Buscar IDs das categorias de provisão (usando LIKE para buscar por nome)
        provisao_categorias = []
        for nome in item["provisao_nomes"]:
            cats = (
                db.query(CategoriaFinanceira.id)
                .filter(
                    CategoriaFinanceira.tenant_id == tenant_id,
                    CategoriaFinanceira.nome.ilike(f"%{nome}%"),
                )
                .all()
            )
            provisao_categorias.extend(cats)

        provisao_ids = (
            [cat.id for cat in provisao_categorias] if provisao_categorias else []
        )

        # Buscar IDs das categorias de realizado (usando LIKE para buscar por nome)
        real_categorias = []
        for nome in item["real_nomes"]:
            cats = (
                db.query(CategoriaFinanceira.id)
                .filter(
                    CategoriaFinanceira.tenant_id == tenant_id,
                    CategoriaFinanceira.nome.ilike(f"%{nome}%"),
                )
                .all()
            )
            real_categorias.extend(cats)

        real_ids = [cat.id for cat in real_categorias] if real_categorias else []

        # Buscar provisões (contas a pagar com categoria de provisão)
        provisao = Decimal("0.00")
        if provisao_ids:
            provisao_valor = (
                db.query(func.coalesce(func.sum(ContaPagar.valor_original), 0))
                .filter(
                    ContaPagar.tenant_id == tenant_id,
                    extract("month", ContaPagar.data_emissao) == mes,
                    extract("year", ContaPagar.data_emissao) == ano,
                    ContaPagar.categoria_id.in_(provisao_ids),
                )
                .scalar()
            )
            if provisao_valor:
                provisao = Decimal(str(provisao_valor))

        # Buscar valores realizados (pagos)
        realizado = Decimal("0.00")
        if real_ids:
            real_valor = (
                db.query(func.coalesce(func.sum(ContaPagar.valor_pago), 0))
                .filter(
                    ContaPagar.tenant_id == tenant_id,
                    extract("month", ContaPagar.data_pagamento) == mes,
                    extract("year", ContaPagar.data_pagamento) == ano,
                    ContaPagar.categoria_id.in_(real_ids),
                    ContaPagar.status == "Pago",
                )
                .scalar()
            )
            if real_valor:
                realizado = Decimal(str(real_valor))

        # Calcular diferença
        diferenca = provisao - realizado

        # Determinar status
        if diferenca == 0 and provisao > 0:
            status = "OK"
            status_emoji = "✅"
        elif realizado > 0 and diferenca != 0:
            status = "AJUSTE"
            status_emoji = "⚠️"
        elif provisao > 0 and realizado == 0:
            status = "ACUMULANDO"
            status_emoji = "🕒"
        else:
            status = "SEM_DADOS"
            status_emoji = "➖"

        resultado.append(
            {
                "item": item["nome"],
                "provisao": float(provisao),
                "realizado": float(realizado),
                "diferenca": float(diferenca),
                "status": status,
                "status_emoji": status_emoji,
                "percentual_realizado": float(
                    (realizado / provisao * 100) if provisao > 0 else 0
                ),
            }
        )

    return resultado


def auditar_provisoes_anual(db: Session, tenant_id: int, ano: int) -> Dict:
    """
    Gera auditoria consolidada do ano inteiro.

    Returns:
        Dict com totalizações anuais por item
    """

    resultado_anual = {}

    for mes in range(1, 13):
        resultado_mes = auditar_provisoes(db, tenant_id, mes, ano)

        for item_mes in resultado_mes:
            nome = item_mes["item"]

            if nome not in resultado_anual:
                resultado_anual[nome] = {
                    "provisao_total": 0,
                    "realizado_total": 0,
                    "diferenca_total": 0,
                    "meses": [],
                }

            resultado_anual[nome]["provisao_total"] += item_mes["provisao"]
            resultado_anual[nome]["realizado_total"] += item_mes["realizado"]
            resultado_anual[nome]["diferenca_total"] += item_mes["diferenca"]
            resultado_anual[nome]["meses"].append(
                {
                    "mes": mes,
                    "provisao": item_mes["provisao"],
                    "realizado": item_mes["realizado"],
                    "diferenca": item_mes["diferenca"],
                    "status": item_mes["status"],
                }
            )

    return resultado_anual
