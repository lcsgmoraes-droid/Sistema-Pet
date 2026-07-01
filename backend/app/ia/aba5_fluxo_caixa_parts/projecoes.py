import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import and_, case, func
from sqlalchemy.orm import Session

from app.ia.aba5_fluxo_caixa_parts.base import (
    _resolve_tenant_id,
    _saldo_realizado_atual,
    _utcnow_naive,
)
from app.ia.aba5_models import FluxoCaixa, ProjecaoFluxoCaixa
from app.ia_config import Aba5Config

logger = logging.getLogger(__name__)

try:
    from prophet import Prophet

    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    logger.warning("⚠️ Prophet não instalado. Instale com: pip install prophet")


def _montar_projecoes_estaticas(saldo_atual: float, hoje, dias: int = 15) -> List[Dict]:
    projecoes = []
    for i in range(1, dias + 1):
        data_proj = hoje + timedelta(days=i)
        dt_proj = datetime.combine(data_proj, datetime.min.time())
        projecoes.append(
            {
                "data": dt_proj.isoformat(),
                "dias_futuros": i,
                "entrada_estimada": 0.0,
                "saida_estimada": 0.0,
                "saldo_estimado": float(saldo_atual),
                "limite_inferior": float(saldo_atual),
                "limite_superior": float(saldo_atual),
                "vai_faltar_caixa": saldo_atual < 0,
                "alerta_nivel": "info",
            }
        )
    return projecoes


def _persistir_projecoes_estaticas(
    usuario_id: int,
    tenant_id: str,
    projecoes: List[Dict],
    mensagem_alerta: str,
    db: Session,
) -> None:
    for projecao in projecoes:
        registro = ProjecaoFluxoCaixa(
            usuario_id=usuario_id,
            tenant_id=tenant_id,
            data_projetada=datetime.fromisoformat(projecao["data"]),
            dias_futuros=projecao["dias_futuros"],
            valor_entrada_estimada=projecao["entrada_estimada"],
            valor_saida_estimada=projecao["saida_estimada"],
            saldo_estimado=projecao["saldo_estimado"],
            limite_inferior=projecao["limite_inferior"],
            limite_superior=projecao["limite_superior"],
            vai_faltar_caixa=projecao["vai_faltar_caixa"],
            alerta_nivel=projecao["alerta_nivel"],
            mensagem_alerta=mensagem_alerta,
            versao_modelo="fallback-v1",
        )
        db.add(registro)
    db.commit()


def _gerar_projecoes_estaticas(
    usuario_id: int,
    tenant_id: str,
    db: Session,
    mensagem_alerta: str,
) -> List[Dict]:
    saldo_atual = _saldo_realizado_atual(usuario_id, tenant_id, db)
    projecoes = _montar_projecoes_estaticas(saldo_atual, _utcnow_naive().date())
    _persistir_projecoes_estaticas(
        usuario_id=usuario_id,
        tenant_id=tenant_id,
        projecoes=projecoes,
        mensagem_alerta=mensagem_alerta,
        db=db,
    )
    return projecoes


def projetar_fluxo_15_dias(
    usuario_id: int,
    db: Session,
    tenant_id: Optional[str] = None,
) -> Optional[List[Dict]]:
    """
    Projeta o fluxo de caixa para os próximos 15 dias usando Prophet.

    Retorna lista de dicts:
    [
        {
            'data': '2026-01-12',
            'saldo_estimado': 5000.00,
            'entrada_estimada': 1200.00,
            'saida_estimada': 800.00,
            'limite_inferior': 4500.00,
            'limite_superior': 5500.00,
            'vai_faltar_caixa': False,
            'alerta_nivel': 'ok'
        },
        ...
    ]
    """

    if not PROPHET_AVAILABLE:
        logger.error("Prophet não está instalado!")
        return None

    try:
        tenant_id_resolvido = _resolve_tenant_id(usuario_id, db, tenant_id)
        if not tenant_id_resolvido:
            logger.error(f"❌ Usuário {usuario_id} não encontrado ou sem tenant")
            return None

        # 1. COLETAR DADOS HISTÓRICOS (últimos 90 dias)
        data_90d_atras = _utcnow_naive() - timedelta(days=90)

        movimentacoes = (
            db.query(FluxoCaixa.data_movimentacao, FluxoCaixa.tipo, FluxoCaixa.valor)
            .filter(
                and_(
                    FluxoCaixa.usuario_id == usuario_id,
                    FluxoCaixa.tenant_id == tenant_id_resolvido,
                    FluxoCaixa.status == "realizado",
                    FluxoCaixa.data_movimentacao >= data_90d_atras,
                )
            )
            .order_by(FluxoCaixa.data_movimentacao)
            .all()
        )

        if not movimentacoes:
            logger.warning(f"Sem dados históricos para usuário {usuario_id}")
            return _gerar_projecoes_estaticas(
                usuario_id,
                tenant_id_resolvido,
                db,
                "Projeção sem histórico",
            )

        # 2. AGREGAR POR DIA
        saldo_por_dia = {}
        saldo_acumulado = 0.0

        for mov in movimentacoes:
            data = mov.data_movimentacao.date()
            valor = mov.valor if mov.tipo == "receita" else -mov.valor

            if data not in saldo_por_dia:
                saldo_por_dia[data] = 0

            saldo_por_dia[data] += valor
            saldo_acumulado += valor

        # 3. PREPARAR DATAFRAME PARA PROPHET
        import pandas as pd

        df_dados = []
        saldo_acumulado = 0.0

        for data in sorted(saldo_por_dia.keys()):
            saldo_acumulado += saldo_por_dia[data]
            df_dados.append({"ds": pd.Timestamp(data), "y": saldo_acumulado})

        df = pd.DataFrame(df_dados)

        if len(df) < 10:
            logger.warning(f"Dados insuficientes para Prophet ({len(df)} dias)")
            return _gerar_projecoes_estaticas(
                usuario_id,
                tenant_id_resolvido,
                db,
                "Histórico insuficiente",
            )

        # 4. TREINAR PROPHET
        model = Prophet(
            yearly_seasonality=False,
            weekly_seasonality=True,
            daily_seasonality=False,
            interval_width=0.95,
        )

        model.fit(df)

        # 5. FAZER FORECAST (15 dias)
        future = model.make_future_dataframe(periods=15)
        forecast = model.predict(future)

        # Pegar só os próximos 15 dias
        forecast_15d = forecast.tail(15).copy()

        # 6. PROCESSAR RESULTADOS
        projecoes = []
        hoje = _utcnow_naive().date()

        # Buscar tenant_id
        tenant_id = tenant_id_resolvido
        if not tenant_id:
            logger.error(f"❌ Usuário {usuario_id} não encontrado ou sem tenant")
            return None

        # Obter saldo atual
        saldo_atual = (
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
                )
            )
            .scalar()
            or 0.0
        )

        for idx, row in forecast_15d.iterrows():
            data_forecast = row["ds"].date()
            dias_futuros = (data_forecast - hoje).days

            # Calcular valores
            saldo_estimado = float(row["yhat"])
            limite_inf = float(row["yhat_lower"])
            limite_sup = float(row["yhat_upper"])

            # Assumir proporção 60% entrada, 40% saída
            movimento_estimado = abs(saldo_estimado - saldo_atual)
            entrada_estimada = movimento_estimado * 0.6
            saida_estimada = movimento_estimado * 0.4

            # Verificar alerta
            vai_faltar_caixa = limite_inf < 0

            if saldo_estimado < Aba5Config.DIAS_CAIXA_CRITICO * (saida_estimada / 30):
                alerta_nivel = "critico"
            elif saldo_estimado < Aba5Config.DIAS_CAIXA_ALERTA * (saida_estimada / 30):
                alerta_nivel = "alerta"
            else:
                alerta_nivel = "ok"

            projecoes.append(
                {
                    "data": data_forecast.isoformat(),
                    "dias_futuros": dias_futuros,
                    "saldo_estimado": round(saldo_estimado, 2),
                    "entrada_estimada": round(entrada_estimada, 2),
                    "saida_estimada": round(saida_estimada, 2),
                    "limite_inferior": round(limite_inf, 2),
                    "limite_superior": round(limite_sup, 2),
                    "vai_faltar_caixa": bool(vai_faltar_caixa),
                    "alerta_nivel": alerta_nivel,
                }
            )

            # Salvar no banco
            proj = ProjecaoFluxoCaixa(
                usuario_id=usuario_id,
                tenant_id=tenant_id,
                data_projetada=datetime.combine(data_forecast, datetime.min.time()),
                dias_futuros=dias_futuros,
                valor_entrada_estimada=entrada_estimada,
                valor_saida_estimada=saida_estimada,
                saldo_estimado=saldo_estimado,
                limite_inferior=limite_inf,
                limite_superior=limite_sup,
                vai_faltar_caixa=vai_faltar_caixa,
                alerta_nivel=alerta_nivel,
                versao_modelo="prophet_1.1.5",
            )
            db.add(proj)

        db.commit()

        logger.info(f"✅ Projeção 15 dias feita para usuário {usuario_id}")
        return projecoes

    except Exception as e:
        logger.error(f"❌ Erro ao projetar fluxo: {str(e)}")
        import traceback

        traceback.print_exc()
        return None


def obter_projecoes_proximos_dias(
    usuario_id: int,
    dias: int = 15,
    db: Session = None,
    tenant_id: Optional[str] = None,
) -> List[Dict]:
    """
    Retorna projeções já calculadas do banco de dados.
    """
    if not db:
        return []

    try:
        tenant_id_resolvido = _resolve_tenant_id(usuario_id, db, tenant_id)
        if not tenant_id_resolvido:
            return []

        agora = _utcnow_naive()
        data_futura = agora + timedelta(days=dias)
        hoje = agora.date()

        projecoes = (
            db.query(ProjecaoFluxoCaixa)
            .filter(
                and_(
                    ProjecaoFluxoCaixa.usuario_id == usuario_id,
                    ProjecaoFluxoCaixa.tenant_id == tenant_id_resolvido,
                    ProjecaoFluxoCaixa.data_projetada <= data_futura,
                    ProjecaoFluxoCaixa.data_projetada >= agora,
                )
            )
            .order_by(ProjecaoFluxoCaixa.data_projetada)
            .limit(dias)
            .all()
        )

        return [
            {
                "data": p.data_projetada.date().isoformat(),
                "dias_futuros": (p.data_projetada.date() - hoje).days,
                "saldo_estimado": p.saldo_estimado,
                "entrada_estimada": p.valor_entrada_estimada,
                "saida_estimada": p.valor_saida_estimada,
                "limite_inferior": p.limite_inferior,
                "limite_superior": p.limite_superior,
                "vai_faltar_caixa": p.vai_faltar_caixa,
                "alerta_nivel": p.alerta_nivel,
            }
            for p in projecoes
        ]

    except Exception as e:
        logger.error(f"Erro ao obter projeções: {str(e)}")
        return []
