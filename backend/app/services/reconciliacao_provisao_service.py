"""
Serviço genérico para reconciliação de provisões trabalhistas.
Substitui provisões estimadas por valores reais no DRE.
Usado para: INSS, FGTS, Folha de Pagamento, Férias, 13º, etc.

IMPORTANTE: Este serviço foi criado para preparar a estrutura, mas atualmente
o DRE usa modelo consolidado (DREPeriodo) com campos diretos, não lançamentos granulares.

Para implementação completa, será necessário:
1. Criar tabela de lançamentos DRE individuais, OU
2. Adaptar DREPeriodo para incluir campos de provisões trabalhistas

Por ora, este serviço registra o conceito e estará pronto quando a estrutura for expandida.
"""

from decimal import Decimal
from sqlalchemy import func, and_, extract
from sqlalchemy.orm import Session

from app.ia.aba7_models import DREPeriodo
from app.financeiro_models import CategoriaFinanceira


def reconciliar_provisao(
    db: Session,
    tenant_id,
    nome_provisao: str,
    nome_real: str,
    valor_real: Decimal,
    mes: int,
    ano: int,
    observacao_real: str,
):
    """
    Substitui provisão por valor real no DRE.
    Usado para INSS, FGTS, Folha, etc.
    
    VERSÃO ATUAL: Registra no DREPeriodo usando despesas_administrativas
    
    Args:
        db: Sessão do banco de dados
        tenant_id: ID do tenant
        nome_provisao: Nome da categoria de provisão (ex: "Provisão INSS Patronal")
        nome_real: Nome da categoria real (ex: "INSS Patronal")
        valor_real: Valor real a ser lançado
        mes: Mês de competência
        ano: Ano de competência
        observacao_real: Observação para o lançamento real
    """
    
    valor_real = Decimal(str(valor_real))
    
    # Buscar ou criar período DRE
    periodo = (
        db.query(DREPeriodo)
        .filter(
            and_(
                DREPeriodo.tenant_id == tenant_id,
                DREPeriodo.mes == mes,
                DREPeriodo.ano == ano
            )
        )
        .first()
    )
    
    if not periodo:
        # Criar período básico se não existir
        from datetime import date
        import calendar
        
        ultimo_dia = calendar.monthrange(ano, mes)[1]
        
        periodo = DREPeriodo(
            tenant_id=tenant_id,
            data_inicio=date(ano, mes, 1),
            data_fim=date(ano, mes, ultimo_dia),
            mes=mes,
            ano=ano,
            receita_bruta=0,
            deducoes_receita=0,
            receita_liquida=0,
            custo_produtos_vendidos=0,
            lucro_bruto=0,
            despesas_vendas=0,
            despesas_administrativas=0,
            despesas_financeiras=0,
            outras_despesas=0,
            total_despesas_operacionais=0,
            lucro_operacional=0,
            impostos=0,
            lucro_liquido=0
        )
        db.add(periodo)
        db.flush()
    
    # Determinar onde lançar a despesa
    if "INSS" in nome_real or "FGTS" in nome_real:
        # Tributos trabalhistas geralmente vão em despesas administrativas
        periodo.despesas_administrativas = (periodo.despesas_administrativas or 0) + float(valor_real)
    elif "Folha" in nome_real:
        # Folha também vai em despesas administrativas
        periodo.despesas_administrativas = (periodo.despesas_administrativas or 0) + float(valor_real)
    else:
        # Outras provisões em outras_despesas
        periodo.outras_despesas = (periodo.outras_despesas or 0) + float(valor_real)
    
    # Recalcular totais
    periodo.total_despesas_operacionais = (
        (periodo.despesas_vendas or 0) +
        (periodo.despesas_administrativas or 0) +
        (periodo.despesas_financeiras or 0) +
        (periodo.outras_despesas or 0)
    )
    
    periodo.lucro_operacional = (periodo.lucro_bruto or 0) - periodo.total_despesas_operacionais
    periodo.lucro_liquido = periodo.lucro_operacional - (periodo.impostos or 0)
    
    # Atualizar margens
    if periodo.receita_liquida and periodo.receita_liquida > 0:
        periodo.margem_operacional_percent = (periodo.lucro_operacional / periodo.receita_liquida) * 100
        periodo.margem_liquida_percent = (periodo.lucro_liquido / periodo.receita_liquida) * 100
    
    # Registrar no detalhamento (para rastreabilidade)
    import json
    detalhamento_atual = periodo.impostos_detalhamento or ""
    
    novo_lancamento = f"\n[{nome_real}] R$ {valor_real:.2f} - {observacao_real}"
    periodo.impostos_detalhamento = detalhamento_atual + novo_lancamento
    
    db.flush()
    
    return {
        "sucesso": True,
        "periodo_id": periodo.id,
        "valor_lancado": float(valor_real),
        "categoria": nome_real,
        "mes": mes,
        "ano": ano
    }
