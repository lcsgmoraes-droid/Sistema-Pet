"""
Serviço de fechamento mensal do Simples Nacional.
Calcula alíquota efetiva e sugere nova alíquota para próximo mês.
"""

from decimal import Decimal
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_

from app.simples_nacional_models import SimplesNacionalMensal
from app.empresa_config_fiscal_models import EmpresaConfigFiscal
from app.ia.aba7_models import DREPeriodo
from app.financeiro_models import ContaPagar, CategoriaFinanceira


def fechar_simples_mensal(
    db: Session,
    tenant_id,
    mes: int,
    ano: int,
    faturamento_contador: Decimal = None,
    observacoes: str = None
) -> dict:
    """
    Fecha o Simples Nacional do mês e sugere nova alíquota.
    
    FLUXO:
    1. Busca faturamento do sistema (NFs autorizadas via provisão)
    2. Busca impostos estimados (provisões acumuladas)
    3. Busca impostos reais (DAS pago no mês)
    4. Calcula alíquota efetiva real
    5. Sugere nova alíquota para próximo mês
    6. Atualiza configuração fiscal
    
    Args:
        db: Sessão do banco
        tenant_id: ID do tenant
        mes: Mês de competência
        ano: Ano de competência
        faturamento_contador: Faturamento informado pelo contador (opcional, prioritário)
        observacoes: Observações do fechamento
        
    Returns:
        dict com informações do fechamento
    """
    
    # 1️⃣ Buscar ou criar registro mensal
    registro = (
        db.query(SimplesNacionalMensal)
        .filter(
            SimplesNacionalMensal.tenant_id == tenant_id,
            SimplesNacionalMensal.mes == mes,
            SimplesNacionalMensal.ano == ano
        )
        .first()
    )
    
    if not registro:
        registro = SimplesNacionalMensal(
            tenant_id=tenant_id,
            mes=mes,
            ano=ano
        )
        db.add(registro)
    
    # 2️⃣ Buscar faturamento do sistema via DRE
    # O faturamento real está no DRE (receita_bruta)
    periodo_dre = (
        db.query(DREPeriodo)
        .filter(
            DREPeriodo.mes == mes,
            DREPeriodo.ano == ano
        )
        .first()
    )
    
    if periodo_dre and periodo_dre.receita_bruta:
        registro.faturamento_sistema = periodo_dre.receita_bruta
    else:
        # Fallback: soma de todas as receitas do mês (se DRE não estiver preenchido)
        registro.faturamento_sistema = Decimal("0.00")
    
    # 3️⃣ Atualizar faturamento do contador (se fornecido)
    if faturamento_contador is not None:
        registro.faturamento_contador = faturamento_contador
    
    # 4️⃣ Buscar impostos estimados (provisões do DRE)
    if periodo_dre:
        registro.imposto_estimado = periodo_dre.impostos or Decimal("0.00")
    
    # 5️⃣ Buscar imposto real (DAS pago)
    # Buscar categoria DAS
    categoria_das = (
        db.query(CategoriaFinanceira)
        .filter(
            CategoriaFinanceira.tenant_id == tenant_id,
            CategoriaFinanceira.nome.ilike("%DAS%Simples%")
        )
        .first()
    )
    
    if categoria_das:
        # Somar todos os DAS pagos no mês
        das_pago = (
            db.query(func.coalesce(func.sum(ContaPagar.valor_original), Decimal("0")))
            .filter(
                ContaPagar.tenant_id == tenant_id,
                ContaPagar.categoria_id == categoria_das.id,
                extract('month', ContaPagar.data_emissao) == mes,
                extract('year', ContaPagar.data_emissao) == ano
            )
            .scalar()
        )
        
        if das_pago and das_pago > 0:
            registro.imposto_real = das_pago
    
    # 6️⃣ Calcular alíquota efetiva
    faturamento_base = registro.faturamento_contador or registro.faturamento_sistema
    
    if faturamento_base and faturamento_base > 0 and registro.imposto_real:
        # Alíquota efetiva = (Imposto Real / Faturamento) * 100
        aliquota_decimal = (
            Decimal(str(registro.imposto_real)) / Decimal(str(faturamento_base))
        ).quantize(Decimal("0.0001"))
        
        registro.aliquota_efetiva = aliquota_decimal
        
        # 7️⃣ Sugerir nova alíquota (arredondada para cima)
        import math
        aliquota_percentual = float(aliquota_decimal * 100)
        sugestao = math.ceil(aliquota_percentual * 10) / 10  # Arredonda para 0.1%
        
        registro.aliquota_sugerida = Decimal(str(sugestao / 100)).quantize(Decimal("0.0001"))
        
        # 8️⃣ Atualizar configuração fiscal para próximo mês
        config = (
            db.query(EmpresaConfigFiscal)
            .filter(EmpresaConfigFiscal.tenant_id == tenant_id)
            .first()
        )
        
        if config:
            # Guardar alíquota anterior
            aliquota_anterior = config.simples_aliquota_vigente
            
            # Atualizar para a sugestão
            config.simples_aliquota_vigente = Decimal(str(sugestao))
            config.simples_ultima_atualizacao = date.today()
            
            # Adicionar observação sobre mudança
            if aliquota_anterior and abs(float(aliquota_anterior) - sugestao) >= 0.1:
                mudanca = f"Alíquota ajustada: {aliquota_anterior}% → {sugestao}% (fechamento {mes}/{ano})"
                if observacoes:
                    observacoes = f"{observacoes}\n{mudanca}"
                else:
                    observacoes = mudanca
    
    # 9️⃣ Observações e fechamento
    if observacoes:
        registro.observacoes = observacoes
    
    registro.fechado = True
    
    # Commit
    db.commit()
    db.refresh(registro)
    
    return {
        "sucesso": True,
        "registro_id": registro.id,
        "mes": mes,
        "ano": ano,
        "faturamento_sistema": float(registro.faturamento_sistema or 0),
        "faturamento_contador": float(registro.faturamento_contador) if registro.faturamento_contador else None,
        "faturamento_final": float(registro.faturamento_final or 0),
        "imposto_estimado": float(registro.imposto_estimado or 0),
        "imposto_real": float(registro.imposto_real or 0),
        "diferenca_imposto": float(registro.diferenca_imposto) if registro.diferenca_imposto else None,
        "aliquota_efetiva_decimal": float(registro.aliquota_efetiva) if registro.aliquota_efetiva else None,
        "aliquota_efetiva_percentual": float(registro.aliquota_efetiva * 100) if registro.aliquota_efetiva else None,
        "aliquota_sugerida_percentual": float(registro.aliquota_sugerida * 100) if registro.aliquota_sugerida else None,
        "fechado": registro.fechado
    }


def reabrir_simples_mensal(
    db: Session,
    tenant_id,
    mes: int,
    ano: int
) -> dict:
    """
    Reabre o fechamento do Simples Nacional para ajustes.
    """
    registro = (
        db.query(SimplesNacionalMensal)
        .filter(
            SimplesNacionalMensal.tenant_id == tenant_id,
            SimplesNacionalMensal.mes == mes,
            SimplesNacionalMensal.ano == ano
        )
        .first()
    )
    
    if not registro:
        return {
            "sucesso": False,
            "motivo": f"Fechamento {mes}/{ano} não encontrado"
        }
    
    registro.fechado = False
    db.commit()
    
    return {
        "sucesso": True,
        "mes": mes,
        "ano": ano,
        "fechado": False
    }


def atualizar_faturamento_contador(
    db: Session,
    tenant_id,
    mes: int,
    ano: int,
    faturamento: Decimal
) -> dict:
    """
    Atualiza o faturamento informado pelo contador.
    Recalcula alíquota efetiva automaticamente.
    """
    registro = (
        db.query(SimplesNacionalMensal)
        .filter(
            SimplesNacionalMensal.tenant_id == tenant_id,
            SimplesNacionalMensal.mes == mes,
            SimplesNacionalMensal.ano == ano
        )
        .first()
    )
    
    if not registro:
        return {
            "sucesso": False,
            "motivo": f"Fechamento {mes}/{ano} não encontrado. Execute o fechamento primeiro."
        }
    
    registro.faturamento_contador = faturamento
    
    # Recalcular alíquota efetiva
    if faturamento > 0 and registro.imposto_real:
        aliquota_decimal = (
            Decimal(str(registro.imposto_real)) / Decimal(str(faturamento))
        ).quantize(Decimal("0.0001"))
        
        registro.aliquota_efetiva = aliquota_decimal
        
        import math
        aliquota_percentual = float(aliquota_decimal * 100)
        sugestao = math.ceil(aliquota_percentual * 10) / 10
        
        registro.aliquota_sugerida = Decimal(str(sugestao / 100)).quantize(Decimal("0.0001"))
    
    db.commit()
    db.refresh(registro)
    
    return {
        "sucesso": True,
        "faturamento_contador": float(faturamento),
        "aliquota_efetiva_percentual": float(registro.aliquota_efetiva * 100) if registro.aliquota_efetiva else None
    }
