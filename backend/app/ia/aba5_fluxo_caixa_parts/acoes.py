import logging
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.ia.aba5_fluxo_caixa_parts.base import _resolve_tenant_id, _utcnow_naive
from app.ia.aba5_fluxo_caixa_parts.indices import calcular_indices_saude
from app.ia.aba5_fluxo_caixa_parts.projecoes import obter_projecoes_proximos_dias
from app.ia.aba5_models import FluxoCaixa, IndicesSaudeCaixa, ProjecaoFluxoCaixa

logger = logging.getLogger(__name__)


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
                        "data": _utcnow_naive().isoformat(),
                    }
                )
            elif indices.status == "alerta":
                alertas.append(
                    {
                        "tipo": "alerta",
                        "titulo": "⚠️ CAIXA EM ALERTA",
                        "mensagem": f"Caixa com {indices.dias_de_caixa:.1f} dias. Monitore de perto.",
                        "data": _utcnow_naive().isoformat(),
                    }
                )

            if indices.tendencia == "piorando":
                alertas.append(
                    {
                        "tipo": "aviso",
                        "titulo": "📉 TENDÊNCIA NEGATIVA",
                        "mensagem": f"Caixa piorou {abs(indices.percentual_variacao_7d):.1f}% nos últimos 7 dias",
                        "data": _utcnow_naive().isoformat(),
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
                    "data": _utcnow_naive().isoformat(),
                }
            )

        logger.info(f"✅ {len(alertas)} alertas gerados para usuário {usuario_id}")
        return alertas

    except Exception as e:
        logger.error(f"❌ Erro ao gerar alertas: {str(e)}")
        return []


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
            data_movimentacao=_utcnow_naive(),
            data_prevista=data_prevista or _utcnow_naive(),
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
