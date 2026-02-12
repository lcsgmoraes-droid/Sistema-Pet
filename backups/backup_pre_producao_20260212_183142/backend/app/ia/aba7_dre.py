"""
ABA 7: DRE Inteligente - Lógica de Negócio
Cálculo e análise de Demonstração de Resultado do Exercício
"""

from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
import json

from app.utils.logger import logger
from app.ia.aba7_models import (
    DREPeriodo,
    DREProduto,
    DRECategoriaAnalise,
    DREComparacao,
    DREInsight
)


class DREService:
    """Serviço para cálculo e análise de DRE"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ==================== CÁLCULO DO DRE ====================
    
    def calcular_dre_periodo(
        self,
        usuario_id: int,
        data_inicio: date,
        data_fim: date
    ) -> DREPeriodo:
        """Calcula DRE para um período"""
        
        # 1. Buscar vendas do período
        from app.models import Venda, VendaItem, Produto
        
        vendas = (
            self.db.query(Venda)
            .filter(
                Venda.user_id == usuario_id,
                Venda.criado_em >= data_inicio,
                Venda.criado_em <= data_fim,
                Venda.status.in_(['finalizada', 'paga'])
            )
            .all()
        )
        
        # 2. Calcular receitas
        receita_bruta = sum(v.valor_total or 0 for v in vendas)
        deducoes_receita = sum(v.desconto or 0 for v in vendas)
        receita_liquida = receita_bruta - deducoes_receita
        
        # 3. Calcular custo dos produtos vendidos (CMV)
        custo_produtos = 0
        for venda in vendas:
            itens = (
                self.db.query(VendaItem)
                .filter(VendaItem.venda_id == venda.id)
                .all()
            )
            for item in itens:
                produto = (
                    self.db.query(Produto)
                    .filter(Produto.id == item.produto_id)
                    .first()
                )
                if produto and produto.preco_custo:
                    custo_produtos += (produto.preco_custo * item.quantidade)
        
        lucro_bruto = receita_liquida - custo_produtos
        margem_bruta = (lucro_bruto / receita_liquida * 100) if receita_liquida > 0 else 0
        
        # 4. Calcular despesas operacionais
        from app.models import LancamentoFluxoCaixa
        
        despesas_vendas = self.db.query(
            func.sum(LancamentoFluxoCaixa.valor)
        ).filter(
            LancamentoFluxoCaixa.user_id == usuario_id,
            LancamentoFluxoCaixa.data >= data_inicio,
            LancamentoFluxoCaixa.data <= data_fim,
            LancamentoFluxoCaixa.tipo == 'saida',
            LancamentoFluxoCaixa.categoria.in_(['Vendas', 'Marketing', 'Comissões'])
        ).scalar() or 0
        
        despesas_administrativas = self.db.query(
            func.sum(LancamentoFluxoCaixa.valor)
        ).filter(
            LancamentoFluxoCaixa.user_id == usuario_id,
            LancamentoFluxoCaixa.data >= data_inicio,
            LancamentoFluxoCaixa.data <= data_fim,
            LancamentoFluxoCaixa.tipo == 'saida',
            LancamentoFluxoCaixa.categoria.in_(['Administrativo', 'Salários', 'Aluguel'])
        ).scalar() or 0
        
        despesas_financeiras = self.db.query(
            func.sum(LancamentoFluxoCaixa.valor)
        ).filter(
            LancamentoFluxoCaixa.user_id == usuario_id,
            LancamentoFluxoCaixa.data >= data_inicio,
            LancamentoFluxoCaixa.data <= data_fim,
            LancamentoFluxoCaixa.tipo == 'saida',
            LancamentoFluxoCaixa.categoria.in_(['Financeiro', 'Juros', 'Taxas'])
        ).scalar() or 0
        
        outras_despesas = self.db.query(
            func.sum(LancamentoFluxoCaixa.valor)
        ).filter(
            LancamentoFluxoCaixa.user_id == usuario_id,
            LancamentoFluxoCaixa.data >= data_inicio,
            LancamentoFluxoCaixa.data <= data_fim,
            LancamentoFluxoCaixa.tipo == 'saida',
            ~LancamentoFluxoCaixa.categoria.in_([
                'Vendas', 'Marketing', 'Comissões',
                'Administrativo', 'Salários', 'Aluguel',
                'Financeiro', 'Juros', 'Taxas'
            ])
        ).scalar() or 0
        
        total_despesas = (
            despesas_vendas +
            despesas_administrativas +
            despesas_financeiras +
            outras_despesas
        )
        
        # 5. Calcular resultados
        lucro_operacional = lucro_bruto - total_despesas
        margem_operacional = (lucro_operacional / receita_liquida * 100) if receita_liquida > 0 else 0
        
        # 5.1 Calcular impostos (se configurado)
        from app.ia.aba7_tributacao import CalculadoraTributaria
        
        calculadora_impostos = CalculadoraTributaria(self.db)
        resultado_impostos = calculadora_impostos.calcular_impostos(
            usuario_id=usuario_id,
            receita_bruta=receita_bruta,
            receita_liquida=receita_liquida,
            lucro_operacional=lucro_operacional
        )
        
        impostos_totais = resultado_impostos['impostos']
        
        lucro_liquido = lucro_operacional - impostos_totais
        margem_liquida = (lucro_liquido / receita_liquida * 100) if receita_liquida > 0 else 0
        
        # 6. Determinar status
        if lucro_liquido > 0:
            status = "lucro"
        elif lucro_liquido < 0:
            status = "prejuizo"
        else:
            status = "equilibrio"
        
        # 7. Calcular score de saúde (0-100)
        score = 50  # Base
        if margem_liquida > 20:
            score += 30
        elif margem_liquida > 10:
            score += 20
        elif margem_liquida > 5:
            score += 10
        
        if lucro_liquido > receita_liquida * 0.15:
            score += 20
        elif lucro_liquido > 0:
            score += 10
        else:
            score -= 20
        
        score = max(0, min(100, score))
        
        # 8. Criar ou atualizar registro
        dre_existente = (
            self.db.query(DREPeriodo)
            .filter(
                DREPeriodo.usuario_id == usuario_id,
                DREPeriodo.data_inicio == data_inicio,
                DREPeriodo.data_fim == data_fim
            )
            .first()
        )
        
        if dre_existente:
            dre = dre_existente
        else:
            dre = DREPeriodo(
                usuario_id=usuario_id,
                data_inicio=data_inicio,
                data_fim=data_fim,
                mes=data_inicio.month,
                ano=data_inicio.year
            )
            self.db.add(dre)
        
        # Atualizar valores
        dre.receita_bruta = receita_bruta
        dre.deducoes_receita = deducoes_receita
        dre.receita_liquida = receita_liquida
        dre.custo_produtos_vendidos = custo_produtos
        dre.lucro_bruto = lucro_bruto
        dre.margem_bruta_percent = margem_bruta
        dre.despesas_vendas = despesas_vendas
        dre.despesas_administrativas = despesas_administrativas
        dre.despesas_financeiras = despesas_financeiras
        dre.outras_despesas = outras_despesas
        dre.total_despesas_operacionais = total_despesas
        dre.lucro_operacional = lucro_operacional
        dre.margem_operacional_percent = margem_operacional
        dre.impostos = impostos_totais
        dre.impostos_detalhamento = json.dumps(resultado_impostos['detalhamento'])
        dre.aliquota_efetiva_percent = resultado_impostos['aliquota_efetiva']
        dre.regime_tributario = resultado_impostos['regime']
        dre.lucro_liquido = lucro_liquido
        dre.margem_liquida_percent = margem_liquida
        dre.status = status
        dre.score_saude = score
        dre.atualizado_em = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(dre)
        
        # 9. Calcular análises por produto e categoria
        self._calcular_analise_produtos(dre.id, usuario_id, data_inicio, data_fim)
        self._calcular_analise_categorias(dre.id, usuario_id, data_inicio, data_fim)
        self._gerar_insights(dre.id, usuario_id, dre)
        
        # 10. Detectar anomalias (valores fora do padrão)
        from app.ia.aba7_anomalias import DetectorAnomalias
        detector = DetectorAnomalias(self.db)
        anomalias = detector.detectar_anomalias_periodo(usuario_id, dre.id)
        
        return dre
    
    def _calcular_analise_produtos(
        self,
        dre_periodo_id: int,
        usuario_id: int,
        data_inicio: date,
        data_fim: date
    ):
        """Calcula rentabilidade por produto"""
        from app.models import Venda, VendaItem, Produto
        
        # Limpar análises antigas
        self.db.query(DREProduto).filter(
            DREProduto.dre_periodo_id == dre_periodo_id
        ).delete()
        
        # Buscar vendas do período
        vendas = (
            self.db.query(Venda)
            .filter(
                Venda.user_id == usuario_id,
                Venda.criado_em >= data_inicio,
                Venda.criado_em <= data_fim,
                Venda.status.in_(['finalizada', 'paga'])
            )
            .all()
        )
        
        # Agregar por produto
        produtos_stats = {}
        
        for venda in vendas:
            itens = (
                self.db.query(VendaItem)
                .filter(VendaItem.venda_id == venda.id)
                .all()
            )
            
            for item in itens:
                if item.produto_id not in produtos_stats:
                    produtos_stats[item.produto_id] = {
                        'quantidade': 0,
                        'receita': 0,
                        'custo': 0
                    }
                
                produtos_stats[item.produto_id]['quantidade'] += item.quantidade
                produtos_stats[item.produto_id]['receita'] += (item.preco_unitario * item.quantidade)
                
                # Buscar custo
                produto = self.db.query(Produto).filter(Produto.id == item.produto_id).first()
                if produto and produto.preco_custo:
                    produtos_stats[item.produto_id]['custo'] += (produto.preco_custo * item.quantidade)
        
        # Criar registros
        ranking = 1
        for produto_id, stats in sorted(
            produtos_stats.items(),
            key=lambda x: x[1]['receita'] - x[1]['custo'],
            reverse=True
        ):
            produto = self.db.query(Produto).filter(Produto.id == produto_id).first()
            if not produto:
                continue
            
            lucro = stats['receita'] - stats['custo']
            margem = (lucro / stats['receita'] * 100) if stats['receita'] > 0 else 0
            
            # Recomendação
            if margem > 30:
                recomendacao = "Excelente! Produto altamente lucrativo. Considere aumentar estoque."
            elif margem > 15:
                recomendacao = "Boa rentabilidade. Continue investindo neste produto."
            elif margem > 5:
                recomendacao = "Margem baixa. Avalie possibilidade de reajuste de preço."
            else:
                recomendacao = "Atenção: Produto com baixa ou nenhuma lucratividade. Considere descontinuar."
            
            dre_produto = DREProduto(
                dre_periodo_id=dre_periodo_id,
                usuario_id=usuario_id,
                produto_id=produto_id,
                produto_nome=produto.nome,
                categoria=produto.categoria or "Sem categoria",
                quantidade_vendida=stats['quantidade'],
                receita_total=stats['receita'],
                custo_total=stats['custo'],
                lucro_total=lucro,
                margem_percent=margem,
                ranking_rentabilidade=ranking,
                eh_lucrativo=(lucro > 0),
                recomendacao=recomendacao
            )
            
            self.db.add(dre_produto)
            ranking += 1
        
        self.db.commit()
    
    def _calcular_analise_categorias(
        self,
        dre_periodo_id: int,
        usuario_id: int,
        data_inicio: date,
        data_fim: date
    ):
        """Calcula rentabilidade por categoria"""
        from app.models import Venda, VendaItem, Produto
        
        # Limpar análises antigas
        self.db.query(DRECategoriaAnalise).filter(
            DRECategoriaAnalise.dre_periodo_id == dre_periodo_id
        ).delete()
        
        # Buscar produtos por categoria
        categorias_stats = {}
        
        produtos = self.db.query(DREProduto).filter(
            DREProduto.dre_periodo_id == dre_periodo_id
        ).all()
        
        for prod in produtos:
            cat = prod.categoria or "Sem categoria"
            if cat not in categorias_stats:
                categorias_stats[cat] = {
                    'quantidade': 0,
                    'receita': 0,
                    'custo': 0
                }
            
            categorias_stats[cat]['quantidade'] += prod.quantidade_vendida
            categorias_stats[cat]['receita'] += prod.receita_total
            categorias_stats[cat]['custo'] += prod.custo_total
        
        # Calcular receita total para percentual
        receita_total_geral = sum(c['receita'] for c in categorias_stats.values())
        
        # Criar registros
        for categoria, stats in categorias_stats.items():
            lucro = stats['receita'] - stats['custo']
            margem = (lucro / stats['receita'] * 100) if stats['receita'] > 0 else 0
            participacao = (stats['receita'] / receita_total_geral * 100) if receita_total_geral > 0 else 0
            
            dre_cat = DRECategoriaAnalise(
                dre_periodo_id=dre_periodo_id,
                usuario_id=usuario_id,
                categoria_nome=categoria,
                quantidade_vendida=stats['quantidade'],
                receita_total=stats['receita'],
                custo_total=stats['custo'],
                lucro_total=lucro,
                margem_percent=margem,
                participacao_receita_percent=participacao,
                eh_categoria_principal=(participacao > 30)
            )
            
            self.db.add(dre_cat)
        
        self.db.commit()
    
    def _gerar_insights(self, dre_periodo_id: int, usuario_id: int, dre: DREPeriodo):
        """Gera insights automáticos sobre o DRE comparando com benchmarks de mercado"""
        from app.ia.aba7_models import IndicesMercado
        
        # Limpar insights antigos
        self.db.query(DREInsight).filter(
            DREInsight.dre_periodo_id == dre_periodo_id
        ).delete()
        
        insights = []
        
        # Buscar índices de mercado (pet_shop por padrão)
        indices = self.db.query(IndicesMercado).filter(
            IndicesMercado.setor == 'pet_shop',
            IndicesMercado.ativo == True
        ).first()
        
        if not indices:
            # Fallback: criar índices padrão se não existir
            logger.warning("⚠️  Índices de mercado não encontrados, usando valores padrão")
            indices = type('obj', (object,), {
                'margem_liquida_ideal_min': 10,
                'margem_liquida_ideal_max': 20,
                'cmv_ideal_min': 35,
                'cmv_ideal_max': 50,
                'margem_bruta_ideal_min': 45,
                'margem_bruta_ideal_max': 60,
                'despesas_totais_ideal_max': 35,
                'despesas_admin_ideal_max': 15,
                'despesas_vendas_ideal_max': 8,
                'despesas_financeiras_ideal_max': 3
            })()
        
        # ===== INSIGHT 1: Margem Líquida vs Mercado =====
        if dre.margem_liquida_percent < indices.margem_liquida_ideal_min:
            diferenca = indices.margem_liquida_ideal_min - dre.margem_liquida_percent
            impacto_valor = (diferenca / 100) * dre.receita_liquida if dre.receita_liquida > 0 else 0
            
            insights.append({
                'tipo': 'alerta',
                'categoria': 'lucro',
                'titulo': '📉 Margem Líquida Abaixo do Mercado',
                'descricao': f'Sua margem líquida está em {dre.margem_liquida_percent:.1f}%, abaixo do ideal para pet shops ({indices.margem_liquida_ideal_min}-{indices.margem_liquida_ideal_max}%). Você está deixando de ganhar aproximadamente R$ {impacto_valor:,.2f}.',
                'impacto': 'alto' if diferenca > 5 else 'medio',
                'acao_sugerida': f'Para atingir a margem ideal, você precisa: 1) Reduzir custos em {diferenca:.1f}% da receita, ou 2) Aumentar preços, ou 3) Otimizar mix de produtos (vender mais itens de alta margem).',
                'impacto_estimado': impacto_valor
            })
        elif dre.margem_liquida_percent > indices.margem_liquida_ideal_max:
            insights.append({
                'tipo': 'recomendacao',
                'categoria': 'lucro',
                'titulo': '🎉 Margem Líquida Acima do Mercado!',
                'descricao': f'Parabéns! Sua margem de {dre.margem_liquida_percent:.1f}% está acima da média do mercado pet ({indices.margem_liquida_ideal_max}%). Você está mais rentável que a concorrência!',
                'impacto': 'baixo',
                'acao_sugerida': 'Mantenha o foco nos produtos mais rentáveis. Considere expandir operação ou investir em marketing para crescer mantendo essa eficiência.',
                'impacto_estimado': 0
            })
        
        # ===== INSIGHT 2: CMV vs Mercado =====
        if dre.receita_liquida > 0:
            perc_cmv = (dre.custo_produtos_vendidos / dre.receita_liquida * 100)
            
            if perc_cmv > indices.cmv_ideal_max:
                diferenca = perc_cmv - indices.cmv_ideal_max
                impacto_valor = (diferenca / 100) * dre.receita_liquida
                
                insights.append({
                    'tipo': 'alerta',
                    'categoria': 'custo',
                    'titulo': '💰 Custo de Produtos Muito Alto',
                    'descricao': f'Seu CMV está em {perc_cmv:.1f}% da receita, acima do ideal ({indices.cmv_ideal_min}-{indices.cmv_ideal_max}%). Isso consome {diferenca:.1f}% a mais que o mercado.',
                    'impacto': 'alto' if diferenca > 10 else 'medio',
                    'acao_sugerida': f'Reduza CMV: 1) Negocie melhores condições com fornecedores (5-10% desconto), 2) Busque fornecedores alternativos, 3) Compre em maior volume, 4) Revise markup (aumente preços em {diferenca/2:.1f}%).',
                    'impacto_estimado': impacto_valor
                })
            elif perc_cmv < indices.cmv_ideal_min:
                insights.append({
                    'tipo': 'oportunidade',
                    'categoria': 'custo',
                    'titulo': '✅ Excelente Controle de Custos!',
                    'descricao': f'Seu CMV de {perc_cmv:.1f}% está abaixo da média ({indices.cmv_ideal_min}%). Você está comprando bem!',
                    'impacto': 'baixo',
                    'acao_sugerida': 'Aproveite essa vantagem competitiva para: 1) Oferecer preços mais agressivos em produtos estratégicos, ou 2) Manter preços e aumentar margem.',
                    'impacto_estimado': 0
                })
        
        # ===== INSIGHT 3: Margem Bruta vs Mercado =====
        if dre.margem_bruta_percent < indices.margem_bruta_ideal_min:
            diferenca = indices.margem_bruta_ideal_min - dre.margem_bruta_percent
            
            insights.append({
                'tipo': 'alerta',
                'categoria': 'lucro',
                'titulo': '📊 Margem Bruta Baixa',
                'descricao': f'Margem bruta de {dre.margem_bruta_percent:.1f}% vs ideal de {indices.margem_bruta_ideal_min}-{indices.margem_bruta_ideal_max}%. Problema nos preços ou custos de compra.',
                'impacto': 'medio',
                'acao_sugerida': f'Aumente margem bruta: 1) Revise precificação (calcule markup correto), 2) Foque produtos premium (margem >60%), 3) Reduza mix de commodities.',
                'impacto_estimado': (diferenca / 100) * dre.receita_liquida if dre.receita_liquida > 0 else 0
            })
        
        # ===== INSIGHT 4: Despesas Totais vs Mercado =====
        if dre.receita_liquida > 0:
            perc_despesas = (dre.total_despesas_operacionais / dre.receita_liquida * 100)
            
            if perc_despesas > indices.despesas_totais_ideal_max:
                diferenca = perc_despesas - indices.despesas_totais_ideal_max
                impacto_valor = (diferenca / 100) * dre.receita_liquida
                
                insights.append({
                    'tipo': 'alerta',
                    'categoria': 'despesa',
                    'titulo': '⚠️ Despesas Operacionais Elevadas',
                    'descricao': f'Despesas de {perc_despesas:.1f}% vs ideal de até {indices.despesas_totais_ideal_max}%. Você está gastando {diferenca:.1f}% a mais que deveria.',
                    'impacto': 'alto' if diferenca > 10 else 'medio',
                    'acao_sugerida': f'Corte despesas: 1) Analise cada categoria (admin: max {indices.despesas_admin_ideal_max}%, vendas: max {indices.despesas_vendas_ideal_max}%), 2) Renegocie aluguel, 3) Reduza custos fixos, 4) Automatize processos.',
                    'impacto_estimado': impacto_valor
                })
        
        # ===== INSIGHT 5: Prejuízo =====
        if dre.status == "prejuizo":
            insights.append({
                'tipo': 'alerta',
                'categoria': 'lucro',
                'titulo': '🔴 Operação em Prejuízo',
                'descricao': f'Prejuízo de R$ {abs(dre.lucro_liquido):,.2f}. AÇÃO IMEDIATA NECESSÁRIA! Você está perdendo dinheiro.',
                'impacto': 'alto',
                'acao_sugerida': 'PLANO DE EMERGÊNCIA: 1) Corte 20% das despesas não essenciais HOJE, 2) Aumente preços em produtos com alta demanda (5-10%), 3) Elimine produtos com margem negativa, 4) Renegocie dívidas com fornecedores.',
                'impacto_estimado': abs(dre.lucro_liquido)
            })
        
        # ===== INSIGHT 6: Análise de Despesas Administrativas =====
        if dre.receita_liquida > 0 and dre.despesas_administrativas > 0:
            perc_admin = (dre.despesas_administrativas / dre.receita_liquida * 100)
            if perc_admin > indices.despesas_admin_ideal_max:
                diferenca = perc_admin - indices.despesas_admin_ideal_max
                insights.append({
                    'tipo': 'oportunidade',
                    'categoria': 'despesa',
                    'titulo': '🏢 Despesas Administrativas Altas',
                    'descricao': f'Despesas administrativas em {perc_admin:.1f}% (ideal: até {indices.despesas_admin_ideal_max}%). Principais vilões: aluguel, salários, água, luz.',
                    'impacto': 'medio',
                    'acao_sugerida': f'Reduza admin: 1) Renegocie aluguel (meta: -10%), 2) Revise quadro de funcionários, 3) Economize energia (LED, ar-condicionado), 4) Considere coworking ou local menor.',
                    'impacto_estimado': (diferenca / 100) * dre.receita_liquida
                })
        
        # ===== INSIGHT 7: Boa Performance Geral =====
        if (dre.margem_liquida_percent >= indices.margem_liquida_ideal_min and
            dre.margem_liquida_percent <= indices.margem_liquida_ideal_max and
            dre.status != "prejuizo"):
            insights.append({
                'tipo': 'recomendacao',
                'categoria': 'lucro',
                'titulo': '🎯 Performance Dentro do Ideal!',
                'descricao': f'Sua operação está saudável! Margem líquida de {dre.margem_liquida_percent:.1f}% dentro da faixa ideal do mercado pet.',
                'impacto': 'baixo',
                'acao_sugerida': 'Mantenha o foco: 1) Continue monitorando indicadores mensalmente, 2) Invista em crescimento (marketing, novos produtos), 3) Construa reserva de emergência (6 meses de despesas).',
                'impacto_estimado': 0
            })
        
        # Salvar insights
        for insight_data in insights:
            insight = DREInsight(
                dre_periodo_id=dre_periodo_id,
                usuario_id=usuario_id,
                **insight_data
            )
            self.db.add(insight)
        
        self.db.commit()
    
    # ==================== CONSULTAS ====================
    
    def obter_dre(self, dre_id: int, usuario_id: int) -> Optional[DREPeriodo]:
        """Obtém DRE por ID"""
        return (
            self.db.query(DREPeriodo)
            .filter(
                DREPeriodo.id == dre_id,
                DREPeriodo.usuario_id == usuario_id
            )
            .first()
        )
    
    def listar_dres(self, usuario_id: int, limit: int = 12) -> List[DREPeriodo]:
        """Lista DREs do usuário"""
        return (
            self.db.query(DREPeriodo)
            .filter(DREPeriodo.usuario_id == usuario_id)
            .order_by(desc(DREPeriodo.data_inicio))
            .limit(limit)
            .all()
        )
    
    def obter_produtos_rentabilidade(
        self,
        dre_periodo_id: int,
        usuario_id: int
    ) -> List[DREProduto]:
        """Obtém ranking de produtos por rentabilidade"""
        return (
            self.db.query(DREProduto)
            .filter(
                DREProduto.dre_periodo_id == dre_periodo_id,
                DREProduto.usuario_id == usuario_id
            )
            .order_by(DREProduto.ranking_rentabilidade)
            .all()
        )
    
    def obter_categorias_rentabilidade(
        self,
        dre_periodo_id: int,
        usuario_id: int
    ) -> List[DRECategoriaAnalise]:
        """Obtém análise por categoria"""
        return (
            self.db.query(DRECategoriaAnalise)
            .filter(
                DRECategoriaAnalise.dre_periodo_id == dre_periodo_id,
                DRECategoriaAnalise.usuario_id == usuario_id
            )
            .order_by(desc(DRECategoriaAnalise.receita_total))
            .all()
        )
    
    def obter_insights(
        self,
        dre_periodo_id: int,
        usuario_id: int
    ) -> List[DREInsight]:
        """Obtém insights do período"""
        return (
            self.db.query(DREInsight)
            .filter(
                DREInsight.dre_periodo_id == dre_periodo_id,
                DREInsight.usuario_id == usuario_id
            )
            .order_by(desc(DREInsight.criado_em))
            .all()
        )
    
    def comparar_periodos(
        self,
        usuario_id: int,
        dre1_id: int,
        dre2_id: int
    ) -> Dict[str, Any]:
        """Compara dois períodos"""
        dre1 = self.obter_dre(dre1_id, usuario_id)
        dre2 = self.obter_dre(dre2_id, usuario_id)
        
        if not dre1 or not dre2:
            return {}
        
        def calc_variacao(valor1, valor2):
            if valor2 == 0:
                return 0
            return ((valor1 - valor2) / valor2) * 100
        
        return {
            'periodo1': {
                'inicio': dre1.data_inicio.isoformat(),
                'fim': dre1.data_fim.isoformat(),
                'receita_liquida': float(dre1.receita_liquida),
                'lucro_liquido': float(dre1.lucro_liquido),
                'margem_liquida': float(dre1.margem_liquida_percent)
            },
            'periodo2': {
                'inicio': dre2.data_inicio.isoformat(),
                'fim': dre2.data_fim.isoformat(),
                'receita_liquida': float(dre2.receita_liquida),
                'lucro_liquido': float(dre2.lucro_liquido),
                'margem_liquida': float(dre2.margem_liquida_percent)
            },
            'variacoes': {
                'receita_percent': calc_variacao(dre1.receita_liquida, dre2.receita_liquida),
                'lucro_percent': calc_variacao(dre1.lucro_liquido, dre2.lucro_liquido),
                'margem_percent': calc_variacao(dre1.margem_liquida_percent, dre2.margem_liquida_percent)
            }
        }
