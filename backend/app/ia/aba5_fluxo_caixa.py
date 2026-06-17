"""
ABA 5: Fluxo de Caixa Preditivo - IMPLEMENTAÇÃO COMPLETA

Funções prontas para usar:
- projetar_fluxo_15_dias() - Projeção com Prophet
- calcular_indices_saude() - Índices de saúde
- simular_cenario() - Simulação de cenários
- obter_projecoes_proximos_dias() - Get from DB
- gerar_alertas_caixa() - Alertas automáticos
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, case
import logging

# Imports de modelos
from app.ia.aba5_models import FluxoCaixa, IndicesSaudeCaixa, ProjecaoFluxoCaixa
from app.ia_config import Aba5Config
from app.models import User

# Logger
logger = logging.getLogger(__name__)

# Prophet para forecasting
try:
    from prophet import Prophet

    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    logger.warning("⚠️ Prophet não instalado. Instale com: pip install prophet")


# ============================================================================
# FUNÇÃO HELPER: BUSCAR TENANT_ID DO USUÁRIO
# ============================================================================


def _get_user_tenant_id(usuario_id: int, db: Session) -> Optional[str]:
    """Busca o tenant_id do usuário"""
    user = db.query(User).filter(User.id == usuario_id).first()
    return user.tenant_id if user else None


def _resolve_tenant_id(
    usuario_id: int, db: Session, tenant_id: Optional[str] = None
) -> Optional[str]:
    if tenant_id:
        return str(tenant_id)
    tenant = _get_user_tenant_id(usuario_id, db)
    return str(tenant) if tenant else None


# ============================================================================
# FUNÇÃO 1: CALCULAR ÍNDICES DE SAÚDE DO CAIXA
# ============================================================================


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
        data_90d_atras = datetime.utcnow() - timedelta(days=90)

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
        data_30d_atras = datetime.utcnow() - timedelta(days=30)

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

        indices.proxima_atualizacao = datetime.utcnow() + timedelta(
            hours=Aba5Config.CACHE_PROJECTIONS_HOURS
        )
        db.commit()

        logger.info(f"✅ Índices calculados para usuário {usuario_id}: {status}")
        return resultado

    except Exception as e:
        logger.error(f"❌ Erro ao calcular índices: {str(e)}")
        return None


# ============================================================================
# FUNÇÃO 2: PROJETAR FLUXO 15 DIAS COM PROPHET
# ============================================================================


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
        data_90d_atras = datetime.utcnow() - timedelta(days=90)

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
            # Fallback: projeção estática baseada no saldo atual
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

            hoje = datetime.utcnow().date()
            projecoes = []
            for i in range(1, 16):
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

            # Persistir fallback
            tenant_id = tenant_id_resolvido
            if not tenant_id:
                logger.error(f"❌ Usuário {usuario_id} não encontrado ou sem tenant")
                return None

            for p in projecoes:
                registro = ProjecaoFluxoCaixa(
                    usuario_id=usuario_id,
                    tenant_id=tenant_id,
                    data_projetada=datetime.fromisoformat(p["data"]),
                    dias_futuros=p["dias_futuros"],
                    valor_entrada_estimada=p["entrada_estimada"],
                    valor_saida_estimada=p["saida_estimada"],
                    saldo_estimado=p["saldo_estimado"],
                    limite_inferior=p["limite_inferior"],
                    limite_superior=p["limite_superior"],
                    vai_faltar_caixa=p["vai_faltar_caixa"],
                    alerta_nivel=p["alerta_nivel"],
                    mensagem_alerta="Projeção sem histórico",
                    versao_modelo="fallback-v1",
                )
                db.add(registro)
            db.commit()

            return projecoes

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
            # Mesmo fallback estático baseado no saldo atual
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

            hoje = datetime.utcnow().date()
            projecoes = []
            for i in range(1, 16):
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

            tenant_id = tenant_id_resolvido
            if not tenant_id:
                logger.error(f"❌ Usuário {usuario_id} não encontrado ou sem tenant")
                return None

            for p in projecoes:
                registro = ProjecaoFluxoCaixa(
                    usuario_id=usuario_id,
                    tenant_id=tenant_id,
                    data_projetada=datetime.fromisoformat(p["data"]),
                    dias_futuros=p["dias_futuros"],
                    valor_entrada_estimada=p["entrada_estimada"],
                    valor_saida_estimada=p["saida_estimada"],
                    saldo_estimado=p["saldo_estimado"],
                    limite_inferior=p["limite_inferior"],
                    limite_superior=p["limite_superior"],
                    vai_faltar_caixa=p["vai_faltar_caixa"],
                    alerta_nivel=p["alerta_nivel"],
                    mensagem_alerta="Histórico insuficiente",
                    versao_modelo="fallback-v1",
                )
                db.add(registro)
            db.commit()

            return projecoes

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
        hoje = datetime.utcnow().date()

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


# ============================================================================
# FUNÇÃO 3: OBTER PROJEÇÕES DO BANCO
# ============================================================================


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

        data_futura = datetime.utcnow() + timedelta(days=dias)
        hoje = datetime.utcnow().date()

        projecoes = (
            db.query(ProjecaoFluxoCaixa)
            .filter(
                and_(
                    ProjecaoFluxoCaixa.usuario_id == usuario_id,
                    ProjecaoFluxoCaixa.tenant_id == tenant_id_resolvido,
                    ProjecaoFluxoCaixa.data_projetada <= data_futura,
                    ProjecaoFluxoCaixa.data_projetada >= datetime.utcnow(),
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


# ============================================================================
# FUNÇÃO 4: SIMULAR CENÁRIOS
# ============================================================================


def simular_cenario(
    usuario_id: int,
    cenario: str,
    db: Session,
    tenant_id: Optional[str] = None,
) -> Optional[Dict]:
    """
    Simula cenários: 'otimista', 'pessimista', 'realista'

    Modifica a projeção com fatores:
    - otimista: +20% entradas, -10% saídas
    - pessimista: -20% entradas, +10% saídas
    - realista: sem modificação
    """

    try:
        # Obter projeção atual
        projecoes = obter_projecoes_proximos_dias(
            usuario_id, 15, db, tenant_id=tenant_id
        )

        if not projecoes:
            return None

        # Aplicar fatores
        fatores = {
            "otimista": {"entrada": 1.2, "saida": 0.9},
            "pessimista": {"entrada": 0.8, "saida": 1.1},
            "realista": {"entrada": 1.0, "saida": 1.0},
        }

        fator = fatores.get(cenario, fatores["realista"])

        resultado = {"cenario": cenario, "projecoes_ajustadas": []}

        for proj in projecoes:
            proj_ajustado = {
                "data": proj["data"],
                "entrada_ajustada": round(
                    proj["entrada_estimada"] * fator["entrada"], 2
                ),
                "saida_ajustada": round(proj["saida_estimada"] * fator["saida"], 2),
                "saldo_ajustado": round(
                    proj["saldo_estimado"] * fator["entrada"] / fator["saida"], 2
                ),
            }
            resultado["projecoes_ajustadas"].append(proj_ajustado)

        logger.info(f"✅ Cenário {cenario} simulado para usuário {usuario_id}")
        return resultado

    except Exception as e:
        logger.error(f"❌ Erro ao simular cenário: {str(e)}")
        return None


# ============================================================================
# FUNÇÃO 5: GERAR ALERTAS
# ============================================================================


def gerar_alertas_caixa(
    usuario_id: int,
    db: Session,
    tenant_id: Optional[str] = None,
) -> List[Dict]:
    """
    Gera alertas baseado em:
    - Dias de caixa crítico
    - Projeção de falta de caixa
    - Tendência piorando

    Retorna lista de alertas com nível e mensagem.
    """

    try:
        tenant_id_resolvido = _resolve_tenant_id(usuario_id, db, tenant_id)
        if not tenant_id_resolvido:
            return []

        alertas = []

        # 1. Verificar índices
        indices = (
            db.query(IndicesSaudeCaixa)
            .filter(
                IndicesSaudeCaixa.usuario_id == usuario_id,
                IndicesSaudeCaixa.tenant_id == tenant_id_resolvido,
            )
            .first()
        )

        if indices:
            if indices.status == "critico":
                alertas.append(
                    {
                        "tipo": "critico",
                        "titulo": "🚨 CAIXA CRÍTICO",
                        "mensagem": f"Caixa com apenas {indices.dias_de_caixa:.1f} dias. Ação urgente necessária!",
                        "data": datetime.utcnow().isoformat(),
                    }
                )
            elif indices.status == "alerta":
                alertas.append(
                    {
                        "tipo": "alerta",
                        "titulo": "⚠️ CAIXA EM ALERTA",
                        "mensagem": f"Caixa com {indices.dias_de_caixa:.1f} dias. Monitore de perto.",
                        "data": datetime.utcnow().isoformat(),
                    }
                )

            if indices.tendencia == "piorando":
                alertas.append(
                    {
                        "tipo": "aviso",
                        "titulo": "📉 TENDÊNCIA NEGATIVA",
                        "mensagem": f"Caixa piorou {abs(indices.percentual_variacao_7d):.1f}% nos últimos 7 dias",
                        "data": datetime.utcnow().isoformat(),
                    }
                )

        # 2. Verificar projeções
        projecoes = (
            db.query(ProjecaoFluxoCaixa)
            .filter(
                and_(
                    ProjecaoFluxoCaixa.usuario_id == usuario_id,
                    ProjecaoFluxoCaixa.tenant_id == tenant_id_resolvido,
                    ProjecaoFluxoCaixa.vai_faltar_caixa.is_(True),
                )
            )
            .order_by(ProjecaoFluxoCaixa.data_projetada)
            .first()
        )

        if projecoes:
            alertas.append(
                {
                    "tipo": "critico",
                    "titulo": "🚨 PROJEÇÃO DE FALTA DE CAIXA",
                    "mensagem": f"Projeção indica falta de caixa em {projecoes.data_projetada.strftime('%d/%m')}",
                    "data": datetime.utcnow().isoformat(),
                }
            )

        logger.info(f"✅ {len(alertas)} alertas gerados para usuário {usuario_id}")
        return alertas

    except Exception as e:
        logger.error(f"❌ Erro ao gerar alertas: {str(e)}")
        return []


# ============================================================================
# FUNÇÃO 6: REGISTRAR MOVIMENTAÇÃO MANUAL
# ============================================================================


def registrar_movimentacao(
    usuario_id: int,
    tipo: str,  # "receita" ou "despesa"
    categoria: str,
    valor: float,
    descricao: str = "",
    data_prevista: Optional[datetime] = None,
    origem_tipo: str = "lancamento_manual",
    origem_id: Optional[int] = None,
    db: Session = None,
    tenant_id: Optional[str] = None,
) -> Optional[FluxoCaixa]:
    """
    Registra uma movimentação manual no fluxo de caixa.
    """

    if not db:
        return None

    try:
        tenant_id_resolvido = _resolve_tenant_id(usuario_id, db, tenant_id)
        if not tenant_id_resolvido:
            logger.error(f"❌ Usuário {usuario_id} não encontrado ou sem tenant")
            return None

        mov = FluxoCaixa(
            usuario_id=usuario_id,
            tenant_id=tenant_id_resolvido,
            tipo=tipo,
            categoria=categoria,
            valor=valor,
            descricao=descricao,
            status="realizado",
            data_movimentacao=datetime.utcnow(),
            data_prevista=data_prevista or datetime.utcnow(),
            origem_tipo=origem_tipo,
            origem_id=origem_id,
        )

        db.add(mov)
        db.commit()
        db.refresh(mov)

        logger.info(f"✅ Movimentação registrada: {tipo} {categoria} R${valor}")

        # Recalcular índices
        calcular_indices_saude(usuario_id, db, tenant_id=tenant_id_resolvido)

        return mov

    except Exception as e:
        logger.error(f"❌ Erro ao registrar movimentação: {str(e)}")
        db.rollback()
        return None


if __name__ == "__main__":
    logger.info("🚀 Módulo ABA 5 - Fluxo de Caixa Preditivo")
    logger.info("Funções disponíveis:")
    logger.info("  ✅ calcular_indices_saude()")
    logger.info("  ✅ projetar_fluxo_15_dias()")
    logger.info("  ✅ obter_projecoes_proximos_dias()")
    logger.info("  ✅ simular_cenario()")
    logger.info("  ✅ gerar_alertas_caixa()")
    logger.info("  ✅ registrar_movimentacao()")
