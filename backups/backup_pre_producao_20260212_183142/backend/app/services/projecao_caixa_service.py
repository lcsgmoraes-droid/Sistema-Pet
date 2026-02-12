"""
Serviço de Projeção de Caixa
Gera projeções futuras baseadas em histórico real e provisões obrigatórias.
"""

from decimal import Decimal
from typing import List, Dict
from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.ia.aba7_dre_detalhada_models import DREDetalheCanal
from app.financeiro_models import ContaPagar
from app.simples_nacional_models import SimplesNacionalMensal


def projetar_caixa(
    db: Session,
    tenant_id: int,
    meses_a_frente: int = 3,
) -> List[Dict]:
    """
    Projeta o caixa considerando histórico e provisões.
    
    Args:
        db: Sessão do banco
        tenant_id: ID do tenant
        meses_a_frente: Número de meses para projetar (padrão: 3)
    
    Returns:
        Lista de dicionários com projeção mês a mês
    """

    resultado = []

    # 🔹 Média de receita últimos 3 meses (valores REAIS, não provisões)
    receita_media = (
        db.query(func.coalesce(func.avg(DREDetalheCanal.receita_bruta), Decimal("0")))
        .filter(
            DREDetalheCanal.tenant_id == tenant_id,
            DREDetalheCanal.origem.in_(["REAL", "PROVISAO"]),
            DREDetalheCanal.receita_bruta > 0
        )
        .scalar()
    )

    receita_media = Decimal(str(receita_media)) if receita_media else Decimal("0")

    # 🔹 Despesas fixas médias (impostos + custos + despesas operacionais)
    despesas_custos = (
        db.query(func.coalesce(func.avg(DREDetalheCanal.custos), Decimal("0")))
        .filter(
            DREDetalheCanal.tenant_id == tenant_id,
            DREDetalheCanal.origem.in_(["REAL", "PROVISAO"]),
            DREDetalheCanal.custos > 0
        )
        .scalar()
    )

    despesas_operacionais = (
        db.query(func.coalesce(func.avg(DREDetalheCanal.despesas_operacionais), Decimal("0")))
        .filter(
            DREDetalheCanal.tenant_id == tenant_id,
            DREDetalheCanal.origem.in_(["REAL", "PROVISAO"]),
            DREDetalheCanal.despesas_operacionais > 0
        )
        .scalar()
    )

    despesas_custos = Decimal(str(despesas_custos)) if despesas_custos else Decimal("0")
    despesas_operacionais = Decimal(str(despesas_operacionais)) if despesas_operacionais else Decimal("0")
    
    despesas_media = despesas_custos + despesas_operacionais

    # 🔹 Alíquota atual do Simples Nacional
    simples = (
        db.query(SimplesNacionalMensal)
        .filter(SimplesNacionalMensal.tenant_id == tenant_id)
        .order_by(SimplesNacionalMensal.ano.desc(), SimplesNacionalMensal.mes.desc())
        .first()
    )

    aliquota_simples = Decimal("0")
    if simples:
        if simples.aliquota_sugerida:
            aliquota_simples = Decimal(str(simples.aliquota_sugerida))
        elif simples.aliquota_vigente:
            aliquota_simples = Decimal(str(simples.aliquota_vigente))

    # 🔹 Folha de pagamento média (despesas com pessoal)
    folha_media = (
        db.query(func.coalesce(func.avg(DREDetalheCanal.despesas_pessoal), Decimal("0")))
        .filter(
            DREDetalheCanal.tenant_id == tenant_id,
            DREDetalheCanal.origem.in_(["REAL", "PROVISAO"]),
            DREDetalheCanal.despesas_pessoal > 0
        )
        .scalar()
    )

    folha_media = Decimal(str(folha_media)) if folha_media else Decimal("0")

    # 🔹 Encargos médios (INSS + FGTS)
    encargos_media = folha_media * Decimal("0.28")  # ~28% (INSS 20% + FGTS 8%)

    # 🔹 Data atual para calcular meses futuros
    hoje = datetime.now()

    # 🔹 Projetar cada mês futuro
    for i in range(1, meses_a_frente + 1):
        # Data do mês futuro
        mes_futuro = hoje + timedelta(days=30 * i)
        mes = mes_futuro.month
        ano = mes_futuro.year

        # Receita projetada (média histórica)
        receita = receita_media

        # Imposto Simples projetado
        imposto_simples = (receita * aliquota_simples / 100).quantize(Decimal("0.01"))

        # Folha + encargos
        folha_total = folha_media + encargos_media

        # Despesas totais = custos + despesas operacionais + impostos + folha + encargos
        despesas = despesas_media + imposto_simples + folha_total

        # Saldo projetado
        saldo = receita - despesas

        resultado.append({
            "mes": mes,
            "ano": ano,
            "mes_futuro": i,
            "receita_prevista": float(receita),
            "imposto_simples_previsto": float(imposto_simples),
            "folha_encargos_previstos": float(folha_total),
            "despesas_previstas": float(despesas),
            "saldo_previsto": float(saldo),
            "saldo_positivo": saldo > 0
        })

    return resultado


def obter_resumo_projecao(
    db: Session,
    tenant_id: int,
    meses_a_frente: int = 3
) -> Dict:
    """
    Retorna resumo da projeção de caixa.
    
    Returns:
        Dicionário com totais e indicadores
    """
    projecao = projetar_caixa(db, tenant_id, meses_a_frente)
    
    if not projecao:
        return {
            "meses_projetados": 0,
            "receita_total": 0.0,
            "despesas_totais": 0.0,
            "saldo_total": 0.0,
            "meses_positivos": 0,
            "meses_negativos": 0,
            "tendencia": "NEUTRO"
        }
    
    receita_total = sum(p["receita_prevista"] for p in projecao)
    despesas_totais = sum(p["despesas_previstas"] for p in projecao)
    saldo_total = sum(p["saldo_previsto"] for p in projecao)
    
    meses_positivos = sum(1 for p in projecao if p["saldo_positivo"])
    meses_negativos = len(projecao) - meses_positivos
    
    # Determinar tendência
    if meses_negativos == 0:
        tendencia = "POSITIVO"
    elif meses_positivos == 0:
        tendencia = "NEGATIVO"
    else:
        tendencia = "MISTO"
    
    return {
        "meses_projetados": len(projecao),
        "receita_total": receita_total,
        "despesas_totais": despesas_totais,
        "saldo_total": saldo_total,
        "meses_positivos": meses_positivos,
        "meses_negativos": meses_negativos,
        "tendencia": tendencia
    }
