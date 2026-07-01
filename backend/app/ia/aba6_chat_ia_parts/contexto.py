"""Contexto financeiro usado pelo chat IA."""

from typing import Any, Dict, Optional

from app.ia.aba5_fluxo_caixa import (
    calcular_indices_saude,
    gerar_alertas_caixa,
    obter_projecoes_proximos_dias,
)
from app.utils.logger import logger


class ChatIAContextoMixin:
    def obter_contexto_financeiro(
        self, usuario_id: int, tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Obtém contexto financeiro do usuário (dados do ABA 5)"""
        contexto = {}
        tenant_id_resolvido = self._resolver_tenant_id(usuario_id, tenant_id)

        try:
            # 1. Índices de saúde
            indices = calcular_indices_saude(
                usuario_id, self.db, tenant_id=tenant_id_resolvido
            )
            contexto["indices_saude"] = {
                "saldo_atual": float(indices.get("saldo_atual", 0)),
                "dias_de_caixa": float(indices.get("dias_de_caixa", 0)),
                "status": indices.get("status", "desconhecido"),
                "tendencia": indices.get("tendencia", "estavel"),
                "score_saude": int(indices.get("score_saude", 0)),
            }

            # 2. Projeções 15 dias
            projecoes = obter_projecoes_proximos_dias(
                usuario_id,
                dias=15,
                db=self.db,
                tenant_id=tenant_id_resolvido,
            )
            contexto["projecoes"] = [
                {
                    "data": p.get("data_projetada"),
                    "saldo_estimado": float(p.get("saldo_estimado", 0)),
                    "entrada_prevista": float(p.get("entrada_prevista", 0)),
                    "saida_prevista": float(p.get("saida_prevista", 0)),
                }
                for p in projecoes[:7]  # Últimos 7 dias para resumo
            ]

            # 3. Alertas
            alertas = gerar_alertas_caixa(
                usuario_id, self.db, tenant_id=tenant_id_resolvido
            )
            contexto["alertas"] = [
                {
                    "tipo": a.get("tipo", ""),
                    "titulo": a.get("titulo", ""),
                    "mensagem": a.get("mensagem", ""),
                }
                for a in alertas
            ]

            inicio_dia, fim_dia = self._date_bounds_for_today()
            inicio_mes, fim_mes = self._date_bounds_for_current_month()

            contexto["vendas_hoje"] = self._obter_resumo_vendas_periodo(
                tenant_id_resolvido, inicio_dia, fim_dia
            )
            contexto["vendas_mes"] = self._obter_resumo_vendas_periodo(
                tenant_id_resolvido, inicio_mes, fim_mes
            )
            contexto["produtos_mes"] = self._obter_produtos_periodo(
                tenant_id_resolvido, inicio_mes, fim_mes, limite=5
            )
            contexto["dre_simplificada_mes"] = self._obter_dre_simplificada_mes(
                tenant_id_resolvido, inicio_mes, fim_mes
            )

        except Exception as e:
            logger.info(f"Erro ao obter contexto financeiro: {e}")
            contexto["erro"] = str(e)

        return contexto
