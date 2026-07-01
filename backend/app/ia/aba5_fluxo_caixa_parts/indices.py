import logging
from datetime import timedelta
from typing import Dict, Optional

from sqlalchemy import and_, case, func
from sqlalchemy.orm import Session

from app.ia.aba5_fluxo_caixa_parts.base import _resolve_tenant_id, _utcnow_naive
from app.ia.aba5_models import FluxoCaixa, IndicesSaudeCaixa
from app.ia_config import Aba5Config

logger = logging.getLogger(__name__)


def calcular_indices_saude(
    usuario_id: int,
    db: Session,
    tenant_id: Optional[str] = None,
) -> Optional[Dict]:
    """
    Calcula os índices de saúde do caixa.

    Retorna:
    {
        'saldo_atual': float,
        'dias_de_caixa': float,
        'ciclo_operacional': float,
        'status': 'critico' | 'alerta' | 'ok',
        'score_saude': float (0-100),
        'tendencia': 'piorando' | 'estavel' | 'melhorando'
    }
    """

    try:
        tenant_id_resolvido = _resolve_tenant_id(usuario_id, db, tenant_id)
        if not tenant_id_resolvido:
            logger.error(f"❌ Usuário {usuario_id} não encontrado ou sem tenant")
            return None

        # 1. SALDO ATUAL
        # Soma movimentações dos últimos 90 dias (otimização)
        data_90d_atras = _utcnow_naive() - timedelta(days=90)

        movimentacoes = (
            db.query(
                func.sum(
                    case(
                        (FluxoCaixa.tipo == "receita", FluxoCaixa.valor),
                        else_=-FluxoCaixa.valor,
                    )
                )
            )
            .filter(
                and_(
                    FluxoCaixa.usuario_id == usuario_id,
                    FluxoCaixa.tenant_id == tenant_id_resolvido,
                    FluxoCaixa.status == "realizado",
                    FluxoCaixa.data_movimentacao >= data_90d_atras,
                )
            )
            .scalar()
        )

        saldo_atual = float(movimentacoes) if movimentacoes else 0.0

        # 2. DESPESA MÉDIA DIÁRIA (últimos 30 dias)
        data_30d_atras = _utcnow_naive() - timedelta(days=30)

        despesas_30d = (
            db.query(func.sum(FluxoCaixa.valor))
            .filter(
                and_(
                    FluxoCaixa.usuario_id == usuario_id,
                    FluxoCaixa.tenant_id == tenant_id_resolvido,
                    FluxoCaixa.tipo == "despesa",
                    FluxoCaixa.status == "realizado",
                    FluxoCaixa.data_movimentacao >= data_30d_atras,
                )
            )
            .scalar()
        )

        despesa_total_30d = float(despesas_30d) if despesas_30d else 0.0
        despesa_media_diaria = despesa_total_30d / 30

        # 3. DIAS DE CAIXA
        if despesa_media_diaria > 0:
            dias_de_caixa = saldo_atual / despesa_media_diaria
        else:
            dias_de_caixa = 999  # Se não tem despesa, tem infinito caixa

        # 4. CICLO OPERACIONAL
        # dias_para_receber: média de dias até receber de clientes
        # dias_para_pagar: média de dias até pagar fornecedores

        # Contas a receber (estima 15 dias padrão)
        dias_para_receber = 15.0

        # Contas a pagar (estima 30 dias padrão)
        dias_para_pagar = 30.0

        ciclo_operacional = dias_para_receber + dias_para_pagar

        # 5. ESTIMATIVAS MENSAIS
        receita_mensal = despesa_total_30d / 30 * 35  # Assume 35% margem (ajustável)
        despesa_mensal = despesa_total_30d
        saldo_mensal = receita_mensal - despesa_mensal

        # 6. STATUS E TENDÊNCIA
        if dias_de_caixa < Aba5Config.DIAS_CAIXA_CRITICO:
            status = "critico"
        elif dias_de_caixa < Aba5Config.DIAS_CAIXA_ALERTA:
            status = "alerta"
        else:
            status = "ok"

        # 7. TENDÊNCIA (variação em 7 dias) - SIMPLIFICADO
        # Se não temos histórico, assumir tendência estável
        percentual_variacao_7d = 0.0
        tendencia = "estavel"  # Default - simplificado para performance

        # 8. SCORE DE SAÚDE (0-100)
        # Baseado em: dias de caixa, ciclo operacional, tendência

        # Score baseado em dias de caixa
        if dias_de_caixa >= Aba5Config.DIAS_CAIXA_OK:
            score_caixa = 100
        elif dias_de_caixa >= Aba5Config.DIAS_CAIXA_ALERTA:
            score_caixa = 70
        elif dias_de_caixa >= Aba5Config.DIAS_CAIXA_CRITICO:
            score_caixa = 40
        else:
            score_caixa = 10

        # Score baseado em tendência
        score_tendencia = {"melhorando": 100, "estavel": 70, "piorando": 30}.get(
            tendencia, 50
        )

        # Score baseado em ciclo operacional
        if ciclo_operacional < Aba5Config.CICLO_OPERACIONAL_MAXIMO:
            score_ciclo = 100
        else:
            score_ciclo = max(
                10, 100 - (ciclo_operacional - Aba5Config.CICLO_OPERACIONAL_MAXIMO)
            )

        # Score final (média ponderada)
        score_saude = score_caixa * 0.5 + score_tendencia * 0.3 + score_ciclo * 0.2

        resultado = {
            "saldo_atual": round(saldo_atual, 2),
            "despesa_media_diaria": round(despesa_media_diaria, 2),
            "dias_de_caixa": round(dias_de_caixa, 1),
            "dias_para_receber": dias_para_receber,
            "dias_para_pagar": dias_para_pagar,
            "ciclo_operacional": ciclo_operacional,
            "receita_mensal_estimada": round(receita_mensal, 2),
            "despesa_mensal_estimada": round(despesa_mensal, 2),
            "saldo_mensal_estimado": round(saldo_mensal, 2),
            "status": status,
            "tendencia": tendencia,
            "percentual_variacao_7d": round(percentual_variacao_7d, 2),
            "score_saude": round(score_saude, 1),
        }

        # Salvar no cache
        indices = (
            db.query(IndicesSaudeCaixa)
            .filter(
                IndicesSaudeCaixa.usuario_id == usuario_id,
                IndicesSaudeCaixa.tenant_id == tenant_id_resolvido,
            )
            .first()
        )

        if not indices:
            indices = IndicesSaudeCaixa(
                usuario_id=usuario_id, tenant_id=tenant_id_resolvido
            )
            db.add(indices)

        for key, value in resultado.items():
            if hasattr(indices, key):
                setattr(indices, key, value)

        indices.proxima_atualizacao = _utcnow_naive() + timedelta(
            hours=Aba5Config.CACHE_PROJECTIONS_HOURS
        )
        db.commit()

        logger.info(f"✅ Índices calculados para usuário {usuario_id}: {status}")
        return resultado

    except Exception as e:
        logger.error(f"❌ Erro ao calcular índices: {str(e)}")
        return None
