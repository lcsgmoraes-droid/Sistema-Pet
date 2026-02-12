"""
ABA 7: Detecção de Anomalias em DRE
Identifica valores fora do padrão usando estatística
"""

from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, datetime
from statistics import mean, stdev
import math

from app.ia.aba7_models import DREPeriodo, DREInsight


class DetectorAnomalias:
    """Detecta anomalias em indicadores financeiros do DRE"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def detectar_anomalias_periodo(
        self,
        usuario_id: int,
        dre_periodo_id: int
    ) -> List[Dict]:
        """
        Detecta anomalias no DRE atual comparando com histórico
        
        Returns:
            [
                {
                    'tipo': 'receita_anormal',
                    'categoria': 'receita',
                    'titulo': 'Receita 45% abaixo da média',
                    'descricao': '...',
                    'impacto': 'alto',
                    'valor_atual': 10000,
                    'valor_esperado': 18000,
                    'desvio_percent': -44.4
                }
            ]
        """
        # 1. Buscar DRE atual
        dre_atual = (
            self.db.query(DREPeriodo)
            .filter(DREPeriodo.id == dre_periodo_id)
            .first()
        )
        
        if not dre_atual:
            return []
        
        # 2. Buscar histórico (últimos 6 meses, excluindo o atual)
        dres_historico = (
            self.db.query(DREPeriodo)
            .filter(
                DREPeriodo.usuario_id == usuario_id,
                DREPeriodo.id != dre_periodo_id,
                DREPeriodo.receita_bruta > 0  # Apenas períodos com vendas
            )
            .order_by(DREPeriodo.data_fim.desc())
            .limit(6)
            .all()
        )
        
        if len(dres_historico) < 3:
            # Histórico insuficiente para análise estatística
            return []
        
        # 3. Detectar anomalias em cada indicador
        anomalias = []
        
        # Receita Bruta
        anomalia_receita = self._detectar_anomalia(
            nome='Receita Bruta',
            categoria='receita',
            valor_atual=dre_atual.receita_bruta,
            valores_historico=[d.receita_bruta for d in dres_historico],
            tipo_anomalia='receita_anormal'
        )
        if anomalia_receita:
            anomalias.append(anomalia_receita)
        
        # Custo de Produtos Vendidos (CMV)
        anomalia_cmv = self._detectar_anomalia(
            nome='Custo de Produtos (CMV)',
            categoria='custo',
            valor_atual=dre_atual.custo_produtos_vendidos,
            valores_historico=[d.custo_produtos_vendidos for d in dres_historico],
            tipo_anomalia='custo_anormal',
            inverter_impacto=True  # Custo alto = impacto negativo
        )
        if anomalia_cmv:
            anomalias.append(anomalia_cmv)
        
        # Margem Bruta
        anomalia_margem = self._detectar_anomalia(
            nome='Margem Bruta',
            categoria='lucro',
            valor_atual=dre_atual.margem_bruta_percent,
            valores_historico=[d.margem_bruta_percent for d in dres_historico],
            tipo_anomalia='margem_anormal',
            eh_percentual=True
        )
        if anomalia_margem:
            anomalias.append(anomalia_margem)
        
        # Despesas Operacionais
        anomalia_despesas = self._detectar_anomalia(
            nome='Despesas Operacionais',
            categoria='despesa',
            valor_atual=dre_atual.total_despesas_operacionais,
            valores_historico=[d.total_despesas_operacionais for d in dres_historico],
            tipo_anomalia='despesa_anormal',
            inverter_impacto=True
        )
        if anomalia_despesas:
            anomalias.append(anomalia_despesas)
        
        # Lucro Líquido
        anomalia_lucro = self._detectar_anomalia(
            nome='Lucro Líquido',
            categoria='lucro',
            valor_atual=dre_atual.lucro_liquido,
            valores_historico=[d.lucro_liquido for d in dres_historico],
            tipo_anomalia='lucro_anormal'
        )
        if anomalia_lucro:
            anomalias.append(anomalia_lucro)
        
        # Impostos (se houver histórico)
        if dre_atual.impostos and dre_atual.impostos > 0:
            impostos_hist = [d.impostos for d in dres_historico if d.impostos and d.impostos > 0]
            if len(impostos_hist) >= 3:
                anomalia_impostos = self._detectar_anomalia(
                    nome='Impostos',
                    categoria='despesa',
                    valor_atual=dre_atual.impostos,
                    valores_historico=impostos_hist,
                    tipo_anomalia='imposto_anormal',
                    inverter_impacto=True
                )
                if anomalia_impostos:
                    anomalias.append(anomalia_impostos)
        
        # 4. Salvar insights no banco
        for anomalia in anomalias:
            self._salvar_insight(
                dre_periodo_id=dre_periodo_id,
                usuario_id=usuario_id,
                anomalia=anomalia
            )
        
        return anomalias
    
    def _detectar_anomalia(
        self,
        nome: str,
        categoria: str,
        valor_atual: float,
        valores_historico: List[float],
        tipo_anomalia: str,
        inverter_impacto: bool = False,
        eh_percentual: bool = False
    ) -> Optional[Dict]:
        """
        Detecta se um valor está fora do padrão usando desvio padrão
        
        Critério: Valor é anômalo se estiver a mais de 1.5 desvios padrão da média
        """
        if not valores_historico or len(valores_historico) < 3:
            return None
        
        # Calcular estatísticas
        media = mean(valores_historico)
        desvio = stdev(valores_historico) if len(valores_historico) > 1 else 0
        
        # Evitar divisão por zero
        if media == 0:
            return None
        
        # Calcular desvio em Z-score
        z_score = (valor_atual - media) / desvio if desvio > 0 else 0
        
        # Threshold: 1.5 desvios padrão (captura ~86% dos dados normais)
        THRESHOLD = 1.5
        
        if abs(z_score) < THRESHOLD:
            # Valor normal, sem anomalia
            return None
        
        # Calcular variação percentual
        desvio_percent = ((valor_atual - media) / media) * 100
        
        # Determinar impacto
        if abs(desvio_percent) > 50:
            impacto = 'alto'
        elif abs(desvio_percent) > 25:
            impacto = 'medio'
        else:
            impacto = 'baixo'
        
        # Inverter impacto para custos/despesas (alto = negativo)
        if inverter_impacto and desvio_percent > 0:
            impacto = 'alto' if impacto == 'baixo' else 'baixo' if impacto == 'alto' else impacto
        
        # Gerar descrição
        direcao = "acima" if desvio_percent > 0 else "abaixo"
        simbolo_moeda = "" if eh_percentual else "R$ "
        sufixo = "%" if eh_percentual else ""
        
        titulo = f"{nome} {abs(desvio_percent):.1f}% {direcao} da média"
        
        descricao = (
            f"O indicador '{nome}' está em {simbolo_moeda}{valor_atual:,.2f}{sufixo}, "
            f"enquanto a média histórica dos últimos {len(valores_historico)} períodos é "
            f"{simbolo_moeda}{media:,.2f}{sufixo}. "
            f"Isso representa uma variação de {abs(desvio_percent):.1f}% {direcao} do esperado."
        )
        
        # Ação sugerida
        if categoria == 'receita' and desvio_percent < 0:
            acao = "Investigar queda nas vendas. Verificar sazonalidade, concorrência ou problemas operacionais."
        elif categoria == 'custo' and desvio_percent > 0:
            acao = "Analisar aumento de custos. Verificar fornecedores, desperdício ou mudanças de mix de produtos."
        elif categoria == 'despesa' and desvio_percent > 0:
            acao = "Revisar despesas operacionais. Identificar gastos extraordinários ou fora do orçamento."
        elif categoria == 'lucro' and desvio_percent < 0:
            acao = "Atenção: lucratividade comprometida. Analisar causas (receita, custos ou despesas)."
        else:
            acao = "Monitorar tendência e verificar se é pontual ou estrutural."
        
        return {
            'tipo': tipo_anomalia,
            'categoria': categoria,
            'titulo': titulo,
            'descricao': descricao,
            'impacto': impacto,
            'valor_atual': valor_atual,
            'valor_esperado': media,
            'desvio_percent': desvio_percent,
            'z_score': z_score,
            'acao_sugerida': acao
        }
    
    def _salvar_insight(
        self,
        dre_periodo_id: int,
        usuario_id: int,
        anomalia: Dict
    ):
        """Salva anomalia como insight no banco"""
        # Verificar se já existe
        insight_existente = (
            self.db.query(DREInsight)
            .filter(
                DREInsight.dre_periodo_id == dre_periodo_id,
                DREInsight.tipo == 'alerta',
                DREInsight.categoria == anomalia['categoria'],
                DREInsight.titulo == anomalia['titulo']
            )
            .first()
        )
        
        if insight_existente:
            # Atualizar
            insight_existente.descricao = anomalia['descricao']
            insight_existente.impacto = anomalia['impacto']
            insight_existente.acao_sugerida = anomalia['acao_sugerida']
            insight_existente.impacto_estimado = abs(
                anomalia['valor_atual'] - anomalia['valor_esperado']
            )
        else:
            # Criar novo
            insight = DREInsight(
                dre_periodo_id=dre_periodo_id,
                usuario_id=usuario_id,
                tipo='alerta',
                categoria=anomalia['categoria'],
                titulo=anomalia['titulo'],
                descricao=anomalia['descricao'],
                impacto=anomalia['impacto'],
                acao_sugerida=anomalia['acao_sugerida'],
                impacto_estimado=abs(
                    anomalia['valor_atual'] - anomalia['valor_esperado']
                ),
                foi_lido=False,
                foi_aplicado=False
            )
            self.db.add(insight)
        
        self.db.commit()
    
    def obter_alertas_ativos(self, usuario_id: int, dre_periodo_id: int) -> List[Dict]:
        """Retorna todos os alertas não lidos de um período"""
        insights = (
            self.db.query(DREInsight)
            .filter(
                DREInsight.dre_periodo_id == dre_periodo_id,
                DREInsight.usuario_id == usuario_id,
                DREInsight.tipo == 'alerta',
                DREInsight.foi_lido == False
            )
            .order_by(DREInsight.impacto.desc(), DREInsight.criado_em.desc())
            .all()
        )
        
        return [
            {
                'id': i.id,
                'tipo': i.tipo,
                'categoria': i.categoria,
                'titulo': i.titulo,
                'descricao': i.descricao,
                'impacto': i.impacto,
                'acao_sugerida': i.acao_sugerida,
                'impacto_estimado': i.impacto_estimado,
                'criado_em': i.criado_em.isoformat()
            }
            for i in insights
        ]
