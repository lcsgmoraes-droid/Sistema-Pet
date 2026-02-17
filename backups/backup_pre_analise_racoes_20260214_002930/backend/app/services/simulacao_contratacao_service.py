"""
Serviço de Simulação de Contratação
Calcula impacto financeiro de contratar um funcionário SEM gravar no banco.
"""

from decimal import Decimal
from datetime import date, datetime
from typing import List, Dict, Optional


def simular_contratacao(
    salario_base: float,
    inss_percentual: float = 20.0,
    fgts_percentual: float = 8.0,
    meses: int = 6,
    cargo: Optional[str] = None,
    data_inicio: Optional[date] = None,
) -> Dict:
    """
    Simula o impacto financeiro de uma contratação.
    Não grava nada no banco.
    
    Args:
        salario_base: Salário bruto mensal
        inss_percentual: Percentual de INSS patronal (padrão: 20%)
        fgts_percentual: Percentual de FGTS (padrão: 8%)
        meses: Quantidade de meses para simular (padrão: 6)
        cargo: Nome do cargo (opcional)
        data_inicio: Data de início da contratação (opcional)
    
    Returns:
        Dicionário com detalhamento mês a mês e totais
    """

    salario = Decimal(str(salario_base))
    inss_pct = Decimal(str(inss_percentual)) / Decimal("100")
    fgts_pct = Decimal(str(fgts_percentual)) / Decimal("100")

    resultado_mensal = []
    
    # Se não informou data de início, usa mês atual
    if not data_inicio:
        data_inicio = date.today()

    for mes_idx in range(1, meses + 1):
        # Custos diretos
        custo_salario = salario
        custo_inss = (salario * inss_pct).quantize(Decimal("0.01"))
        custo_fgts = (salario * fgts_pct).quantize(Decimal("0.01"))

        # Provisões (acumuladas mensalmente)
        provisao_ferias = (salario / Decimal("12")).quantize(Decimal("0.01"))
        provisao_terco = (provisao_ferias / Decimal("3")).quantize(Decimal("0.01"))
        provisao_13 = (salario / Decimal("12")).quantize(Decimal("0.01"))

        # Custo total mensal
        custo_total = (
            custo_salario
            + custo_inss
            + custo_fgts
            + provisao_ferias
            + provisao_terco
            + provisao_13
        )

        # Calcular mês/ano futuro
        mes_futuro = data_inicio.month + mes_idx - 1
        ano_futuro = data_inicio.year
        
        while mes_futuro > 12:
            mes_futuro -= 12
            ano_futuro += 1

        resultado_mensal.append({
            "mes": mes_idx,
            "mes_calendario": mes_futuro,
            "ano": ano_futuro,
            "salario": float(custo_salario),
            "inss": float(custo_inss),
            "fgts": float(custo_fgts),
            "provisao_ferias": float(provisao_ferias),
            "provisao_1_3": float(provisao_terco),
            "provisao_13": float(provisao_13),
            "custo_total": float(custo_total),
        })

    # Calcular totais acumulados
    total_salarios = sum(m["salario"] for m in resultado_mensal)
    total_inss = sum(m["inss"] for m in resultado_mensal)
    total_fgts = sum(m["fgts"] for m in resultado_mensal)
    total_ferias = sum(m["provisao_ferias"] for m in resultado_mensal)
    total_terco = sum(m["provisao_1_3"] for m in resultado_mensal)
    total_13 = sum(m["provisao_13"] for m in resultado_mensal)
    total_geral = sum(m["custo_total"] for m in resultado_mensal)

    # Calcular médias
    media_mensal = total_geral / meses if meses > 0 else 0

    return {
        "parametros": {
            "cargo": cargo or "Não especificado",
            "salario_base": float(salario),
            "inss_percentual": float(inss_percentual),
            "fgts_percentual": float(fgts_percentual),
            "meses_simulados": meses,
            "data_inicio": data_inicio.isoformat() if data_inicio else None,
        },
        "resultado_mensal": resultado_mensal,
        "totais": {
            "total_salarios": total_salarios,
            "total_inss": total_inss,
            "total_fgts": total_fgts,
            "total_provisao_ferias": total_ferias,
            "total_provisao_1_3": total_terco,
            "total_provisao_13": total_13,
            "total_geral": total_geral,
            "media_mensal": media_mensal,
        },
        "analise": {
            "percentual_encargos": float((total_inss + total_fgts) / total_salarios * 100) if total_salarios > 0 else 0,
            "percentual_provisoes": float((total_ferias + total_terco + total_13) / total_salarios * 100) if total_salarios > 0 else 0,
            "custo_total_vs_salario": float(total_geral / total_salarios * 100) if total_salarios > 0 else 0,
        }
    }


def comparar_cenarios(
    cenario_atual: Dict,
    cenario_com_contratacao: Dict
) -> Dict:
    """
    Compara dois cenários (antes e depois da contratação).
    
    Args:
        cenario_atual: Dados financeiros atuais
        cenario_com_contratacao: Dados após simulação de contratação
    
    Returns:
        Comparação com diferenças e impactos
    """
    
    diferenca_custo_mensal = (
        cenario_com_contratacao["totais"]["media_mensal"] 
        - cenario_atual.get("custo_mensal_atual", 0)
    )
    
    return {
        "custo_atual": cenario_atual.get("custo_mensal_atual", 0),
        "custo_novo": cenario_com_contratacao["totais"]["media_mensal"],
        "diferenca_mensal": diferenca_custo_mensal,
        "percentual_aumento": (
            float(diferenca_custo_mensal / cenario_atual.get("custo_mensal_atual", 1) * 100)
            if cenario_atual.get("custo_mensal_atual", 0) > 0
            else 0
        ),
        "impacto_anual": diferenca_custo_mensal * 12,
    }
