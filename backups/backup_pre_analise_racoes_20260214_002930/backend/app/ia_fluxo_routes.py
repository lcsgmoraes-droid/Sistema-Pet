"""
Rotas para IA do Fluxo de Caixa
Endpoints para projeções, alertas e análises inteligentes
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, extract
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List

from .db import get_session
from .auth import get_current_user
from .auth.dependencies import get_current_user_and_tenant
from .models import User
from .financeiro_models import ContaPagar, ContaReceber, ContaBancaria, LancamentoManual

router = APIRouter(prefix="/api", tags=["IA Fluxo Caixa"])


@router.get("/financeiro/movimentacoes")
def listar_movimentacoes(
    data_inicio: str = Query(...),
    data_fim: str = Query(...),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Lista todas as movimentações financeiras (entradas e saídas) no período
    """
    try:
        data_ini = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        data_fi = datetime.strptime(data_fim, '%Y-%m-%d').date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de data inválido")

    movimentacoes = []

    # Contas a Pagar (Saídas)
    contas_pagar = db.query(ContaPagar).filter(
        and_(
            ContaPagar.user_id == current_user.id,
            ContaPagar.data_vencimento >= data_ini,
            ContaPagar.data_vencimento <= data_fi
        )
    ).all()

    for conta in contas_pagar:
        movimentacoes.append({
            'tipo': 'saida',
            'valor': float(conta.valor_original),
            'data': conta.data_vencimento.isoformat() if conta.data_vencimento else None,
            'descricao': conta.descricao,
            'categoria': 'Contas a Pagar',
            'status': 'realizado' if conta.status == 'pago' else 'previsto'
        })

    # Contas a Receber (Entradas)
    contas_receber = db.query(ContaReceber).filter(
        and_(
            ContaReceber.user_id == current_user.id,
            ContaReceber.data_vencimento >= data_ini,
            ContaReceber.data_vencimento <= data_fi
        )
    ).all()

    for conta in contas_receber:
        movimentacoes.append({
            'tipo': 'entrada',
            'valor': float(conta.valor_original),
            'data': conta.data_vencimento.isoformat() if conta.data_vencimento else None,
            'descricao': conta.descricao,
            'categoria': 'Contas a Receber',
            'status': 'realizado' if conta.status == 'recebido' else 'previsto'
        })

    return movimentacoes


@router.get("/financeiro/saldo-atual")
def obter_saldo_atual(
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Retorna o saldo atual somando todas as contas bancárias
    """
    contas = db.query(ContaBancaria).filter(
        ContaBancaria.user_id == current_user.id,
        ContaBancaria.ativa == True
    ).all()

    saldo_total = sum([float(conta.saldo_atual or 0) for conta in contas])

    return {
        'saldo': saldo_total,
        'quantidade_contas': len(contas),
        'data_consulta': datetime.now().isoformat()
    }


@router.get("/financeiro/contas-pagar")
def listar_contas_pagar(
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    status: Optional[str] = None,
    atrasadas: Optional[bool] = None,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Lista contas a pagar com diversos filtros
    """
    query = db.query(ContaPagar).filter(ContaPagar.user_id == current_user.id)

    # Filtrar por período
    if data_inicio and data_fim:
        try:
            data_ini = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            data_fi = datetime.strptime(data_fim, '%Y-%m-%d').date()
            query = query.filter(
                and_(
                    ContaPagar.data_vencimento >= data_ini,
                    ContaPagar.data_vencimento <= data_fi
                )
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de data inválido")

    # Filtrar por status
    if status:
        query = query.filter(ContaPagar.status == status)

    # Filtrar atrasadas
    if atrasadas:
        hoje = date.today()
        query = query.filter(
            and_(
                ContaPagar.data_vencimento < hoje,
                ContaPagar.status.in_(['pendente', 'parcial'])
            )
        )

    contas = query.all()

    return [{
        'id': c.id,
        'descricao': c.descricao,
        'valor': float(c.valor_original),
        'data_vencimento': c.data_vencimento.isoformat() if c.data_vencimento else None,
        'status': c.status,
        'fornecedor': c.fornecedor.nome if c.fornecedor else None
    } for c in contas]


@router.get("/financeiro/analise-gastos")
def analisar_gastos(
    data_inicio: str = Query(...),
    data_fim: str = Query(...),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Analisa gastos comparando com média histórica
    """
    try:
        data_ini = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        data_fi = datetime.strptime(data_fim, '%Y-%m-%d').date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de data inválido")

    # Gastos do período atual
    gastos_periodo = db.query(func.sum(ContaPagar.valor_original)).filter(
        and_(
            ContaPagar.user_id == current_user.id,
            ContaPagar.data_vencimento >= data_ini,
            ContaPagar.data_vencimento <= data_fi
        )
    ).scalar() or 0

    # Calcular média histórica (últimos 6 meses antes do período)
    data_historico_inicio = data_ini - timedelta(days=180)
    
    gastos_historicos = db.query(func.sum(ContaPagar.valor_original)).filter(
        and_(
            ContaPagar.user_id == current_user.id,
            ContaPagar.data_vencimento >= data_historico_inicio,
            ContaPagar.data_vencimento < data_ini
        )
    ).scalar() or 0

    # Calcular variação percentual
    if gastos_historicos > 0:
        media_mensal = float(gastos_historicos) / 6  # 6 meses
        variacao = ((float(gastos_periodo) - media_mensal) / media_mensal) * 100
    else:
        variacao = 0

    return {
        'gastos_periodo': float(gastos_periodo),
        'media_historica': float(gastos_historicos) / 6 if gastos_historicos > 0 else 0,
        'variacao': round(variacao, 2),
        'periodo_dias': (data_fi - data_ini).days + 1
    }


@router.get("/financeiro/recorrencias-proximas")
def listar_recorrencias_proximas(
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Lista despesas recorrentes que vencerão nos próximos 30 dias
    """
    hoje = date.today()
    data_limite = hoje + timedelta(days=30)

    recorrencias = db.query(ContaPagar).filter(
        and_(
            ContaPagar.user_id == current_user.id,
            ContaPagar.eh_recorrente == True,
            ContaPagar.proxima_recorrencia >= hoje,
            ContaPagar.proxima_recorrencia <= data_limite
        )
    ).all()

    return [{
        'id': c.id,
        'descricao': c.descricao,
        'valor': float(c.valor_original),
        'proxima_data': c.proxima_recorrencia.isoformat() if c.proxima_recorrencia else None,
        'tipo_recorrencia': c.tipo_recorrencia,
        'dias_ate': (c.proxima_recorrencia - hoje).days if c.proxima_recorrencia else 0
    } for c in recorrencias]


@router.get("/ia/fluxo/projecao-saldo")
def projecao_saldo(
    dias: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Projeta quando o saldo pode ficar negativo baseado em tendências
    """
    # Buscar saldo atual
    contas = db.query(ContaBancaria).filter(
        ContaBancaria.user_id == current_user.id,
        ContaBancaria.ativa == True
    ).all()
    saldo_atual = sum([float(conta.saldo_atual or 0) for conta in contas])

    # Calcular média diária de entradas e saídas (últimos 30 dias)
    data_inicio = date.today() - timedelta(days=30)
    data_fim = date.today()

    # Média de saídas
    total_saidas = db.query(func.sum(ContaPagar.valor_original)).filter(
        and_(
            ContaPagar.user_id == current_user.id,
            ContaPagar.data_vencimento >= data_inicio,
            ContaPagar.data_vencimento <= data_fim
        )
    ).scalar() or 0

    # Média de entradas
    total_entradas = db.query(func.sum(ContaReceber.valor_original)).filter(
        and_(
            ContaReceber.user_id == current_user.id,
            ContaReceber.data_vencimento >= data_inicio,
            ContaReceber.data_vencimento <= data_fim
        )
    ).scalar() or 0

    media_diaria_saidas = float(total_saidas) / 30
    media_diaria_entradas = float(total_entradas) / 30
    saldo_liquido_diario = media_diaria_entradas - media_diaria_saidas

    # Calcular em quantos dias o saldo ficará negativo
    dias_ate_negativo = 0
    if saldo_liquido_diario < 0 and saldo_atual > 0:
        dias_ate_negativo = int(saldo_atual / abs(saldo_liquido_diario))

    return {
        'saldo_atual': saldo_atual,
        'media_diaria_entradas': round(media_diaria_entradas, 2),
        'media_diaria_saidas': round(media_diaria_saidas, 2),
        'saldo_liquido_diario': round(saldo_liquido_diario, 2),
        'diasAteNegativo': dias_ate_negativo if dias_ate_negativo > 0 and dias_ate_negativo <= dias else 0,
        'projecao_dias': dias
    }
