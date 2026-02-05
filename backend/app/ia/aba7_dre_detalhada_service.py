"""
ABA 7: DRE Detalhada por Canal - Serviço
Calcula cada canal separadamente e permite consolidação customizada
"""

from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
import json

from app.ia.aba7_dre_detalhada_models import DREDetalheCanal, DREConsolidado, AlocacaoDespesaCanal
from app.ia.aba7_tributacao import CalculadoraTributaria
from app.vendas_models import Venda, VendaItem
from app.produtos_models import Produto
from app.financeiro_models import LancamentoManual


class DREDetalhadaService:
    """Calcula DRE detalhada por canal"""
    
    CANAIS = {
        'loja_fisica': 'Loja Física',
        'mercado_livre': 'Mercado Livre',
        'shopee': 'Shopee',
        'amazon': 'Amazon',
        'site': 'Site Próprio',
        'instagram': 'Instagram/WhatsApp'
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def calcular_dre_por_canal(
        self,
        usuario_id: int,
        data_inicio: date,
        data_fim: date,
        canal: str
    ) -> DREDetalheCanal:
        """
        Calcula DRE de UM CANAL específico
        Receitas vêm das vendas do canal
        Despesas de vendas (taxas, comissões) são específicas do canal
        """
        # 1. Receitas do canal
        vendas_canal = self.db.query(Venda).filter(
            Venda.user_id == usuario_id,
            Venda.data_venda >= data_inicio,
            Venda.data_venda <= data_fim,
            Venda.status.in_(['finalizada', 'cancelada']),
            Venda.canal == canal
        ).all()
        
        receita_bruta = sum(v.total or 0 for v in vendas_canal)
        # Deduções específicas do canal
        deducoes = sum(v.desconto_valor or 0 for v in vendas_canal)
        receita_liquida = receita_bruta - deducoes
        
        # 2. CMV do canal
        custo_produtos = 0
        for venda in vendas_canal:
            itens = self.db.query(VendaItem).filter(VendaItem.venda_id == venda.id).all()
            for item in itens:
                produto = self.db.query(Produto).filter(Produto.id == item.produto_id).first()
                if produto and produto.preco_custo:
                    custo_produtos += (produto.preco_custo * item.quantidade)
        
        lucro_bruto = receita_liquida - custo_produtos
        margem_bruta = (lucro_bruto / receita_liquida * 100) if receita_liquida > 0 else 0
        
        # 3. Despesas específicas do canal - ORGANIZAÇÃO CORRETA
        # RECEITA BRUTA: Faturamento
        # DEDUÇÕES: Custos, Impostos, Frete, Tarifa, Cancelamento, Cupom, Comissão
        # DESPESAS OPERACIONAIS: Campanhas Ads, Pessoal, Administrativas
        
        # 3.1 Despesas de Vendas específicas do canal
        # Taxas ML/Shopee, Comissões, Fretes pagos, Cancelamentos, Cupons
        despesas_vendas_especificas = self.db.query(func.sum(LancamentoManual.valor)).filter(
            LancamentoManual.usuario_id == usuario_id,
            LancamentoManual.data >= data_inicio,
            LancamentoManual.data <= data_fim,
            LancamentoManual.tipo == 'saida',
            LancamentoManual.categoria.ilike(f'%{canal}%')  # Categorias que mencionam o canal
        ).scalar() or 0
        
        # 3.2 Campanhas Ads específicas do canal
        campanhas_ads = self.db.query(func.sum(LancamentoManual.valor)).filter(
            LancamentoManual.usuario_id == usuario_id,
            LancamentoManual.data >= data_inicio,
            LancamentoManual.data <= data_fim,
            LancamentoManual.tipo == 'saida',
            LancamentoManual.categoria.ilike('%campanha%'),
            LancamentoManual.descricao.ilike(f'%{canal}%')
        ).scalar() or 0
        
        despesas_vendas = despesas_vendas_especificas + campanhas_ads
        
        # 4. Despesas alocadas manualmente (proporcional ou fixo)
        alocacoes = self.db.query(AlocacaoDespesaCanal).filter(
            AlocacaoDespesaCanal.usuario_id == usuario_id,
            AlocacaoDespesaCanal.data_inicio == data_inicio,
            AlocacaoDespesaCanal.data_fim == data_fim
        ).all()
        
        despesas_pessoal = 0  # Salários, encargos
        despesas_admin = 0    # Água, luz, internet, telefone, aluguel
        despesas_financeiras = 0  # Juros, taxas bancárias
        outras_despesas = 0   # Outras categorias
        
        for alocacao in alocacoes:
            if alocacao.modo_alocacao == 'manual' and alocacao.alocacao_manual:
                manual = json.loads(alocacao.alocacao_manual)
                if canal in manual:
                    valor_canal = manual[canal].get('valor', 0)
                    # Categorizar corretamente cada tipo de despesa
                    if alocacao.categoria_despesa.lower() in ['salario', 'salário', 'folha', 'pessoal', 'funcionario', 'funcionário', 'inss', 'fgts']:
                        despesas_pessoal += valor_canal
                    elif alocacao.categoria_despesa.lower() in ['aluguel', 'luz', 'água', 'agua', 'internet', 'telefone', 'administrativo', 'limpeza', 'material']:
                        despesas_admin += valor_canal
                    elif alocacao.categoria_despesa.lower() in ['juros', 'taxa bancaria', 'taxa bancária', 'financeiro']:
                        despesas_financeiras += valor_canal
                    else:
                        outras_despesas += valor_canal
            elif alocacao.modo_alocacao == 'proporcional' and canal in json.loads(alocacao.canais_afetados or '[]'):
                # Ratear proporcionalmente ao faturamento deste canal
                if receita_bruta > 0 and alocacao.usar_faturamento:
                    # Pega total de receita de todos os canais no período
                    total_receita = self.db.query(func.sum(Venda.total)).filter(
                        Venda.user_id == usuario_id,
                        Venda.data_venda >= data_inicio,
                        Venda.data_venda <= data_fim,
                        Venda.status.in_(['finalizada', 'cancelada'])
                    ).scalar() or 1
                    
                    proporcao = receita_bruta / total_receita
                    valor_alocado = alocacao.valor_total * proporcao
                    
                    # Categorizar corretamente
                    if alocacao.categoria_despesa.lower() in ['salario', 'salário', 'folha', 'pessoal', 'funcionario', 'funcionário', 'inss', 'fgts']:
                        despesas_pessoal += valor_alocado
                    elif alocacao.categoria_despesa.lower() in ['aluguel', 'luz', 'água', 'agua', 'internet', 'telefone', 'administrativo', 'limpeza', 'material']:
                        despesas_admin += valor_alocado
                    elif alocacao.categoria_despesa.lower() in ['juros', 'taxa bancaria', 'taxa bancária', 'financeiro']:
                        despesas_financeiras += valor_alocado
                    else:
                        outras_despesas += valor_alocado
        
        total_despesas = despesas_vendas + despesas_pessoal + despesas_admin + despesas_financeiras + outras_despesas
        
        # 5. Resultado
        lucro_operacional = lucro_bruto - total_despesas
        margem_operacional = (lucro_operacional / receita_liquida * 100) if receita_liquida > 0 else 0
        
        # 6. Impostos
        calculadora = CalculadoraTributaria(self.db)
        resultado_impostos = calculadora.calcular_impostos(
            usuario_id=usuario_id,
            receita_bruta=receita_bruta,
            receita_liquida=receita_liquida,
            lucro_operacional=lucro_operacional
        )
        
        impostos = resultado_impostos['impostos']
        lucro_liquido = lucro_operacional - impostos
        margem_liquida = (lucro_liquido / receita_liquida * 100) if receita_liquida > 0 else 0
        
        # 7. Status
        if lucro_liquido > 0:
            status = "lucro"
        elif lucro_liquido < 0:
            status = "prejuizo"
        else:
            status = "equilibrio"
        
        score = 50
        if margem_liquida > 20:
            score += 30
        elif margem_liquida > 10:
            score += 20
        score = max(0, min(100, score))
        
        # 8. Salvar
        dre_existente = self.db.query(DREDetalheCanal).filter(
            DREDetalheCanal.usuario_id == usuario_id,
            DREDetalheCanal.data_inicio == data_inicio,
            DREDetalheCanal.data_fim == data_fim,
            DREDetalheCanal.canal == canal
        ).first()
        
        if dre_existente:
            dre = dre_existente
        else:
            dre = DREDetalheCanal(
                usuario_id=usuario_id,
                data_inicio=data_inicio,
                data_fim=data_fim,
                mes=data_inicio.month,
                ano=data_inicio.year,
                canal=canal
            )
            self.db.add(dre)
        
        dre.receita_bruta = receita_bruta
        dre.deducoes_receita = deducoes
        dre.receita_liquida = receita_liquida
        dre.custo_produtos_vendidos = custo_produtos
        dre.lucro_bruto = lucro_bruto
        dre.margem_bruta_percent = margem_bruta
        dre.despesas_vendas = despesas_vendas
        dre.despesas_pessoal = despesas_pessoal
        dre.despesas_administrativas = despesas_admin
        dre.despesas_financeiras = despesas_financeiras
        dre.outras_despesas = outras_despesas
        dre.total_despesas_operacionais = total_despesas
        dre.lucro_operacional = lucro_operacional
        dre.margem_operacional_percent = margem_operacional
        dre.impostos = impostos
        dre.impostos_detalhamento = json.dumps(resultado_impostos['detalhamento'])
        dre.aliquota_efetiva_percent = resultado_impostos['aliquota_efetiva']
        dre.regime_tributario = resultado_impostos['regime']
        dre.lucro_liquido = lucro_liquido
        dre.margem_liquida_percent = margem_liquida
        dre.status = status
        dre.score_saude = score
        
        self.db.commit()
        self.db.refresh(dre)
        
        return dre
    
    def calcular_dre_consolidado(
        self,
        usuario_id: int,
        data_inicio: date,
        data_fim: date,
        canais: List[str]
    ) -> Dict:
        """
        Consolidação com DETALHAMENTO por canal
        Retorna cada linha de receita e despesa separada por canal
        
        Returns:
            {
                'receitas': [
                    {'canal': 'loja_fisica', 'receita_bruta': 10000, 'deducoes': 500, 'liquida': 9500},
                    {'canal': 'mercado_livre', 'receita_bruta': 5000, 'deducoes': 250, 'liquida': 4750}
                ],
                'custos': [...],
                'despesas': [...],
                'consolidado': {...}
            }
        """
        # 1. Calcular cada canal
        dres_canais = {}
        for canal in canais:
            dre = self.calcular_dre_por_canal(usuario_id, data_inicio, data_fim, canal)
            dres_canais[canal] = dre
        
        # 2. Estruturar resposta detalhada
        receitas_detalhadas = []
        custos_detalhados = []
        despesas_detalhadas = []
        
        receita_total_bruta = 0
        receita_total_liquida = 0
        custo_total = 0
        despesa_total = 0
        lucro_bruto_total = 0
        
        for canal in canais:
            dre = dres_canais[canal]
            
            # Receita
            receitas_detalhadas.append({
                'canal': canal,
                'canal_nome': self.CANAIS.get(canal, canal),
                'receita_bruta': float(dre.receita_bruta),
                'deducoes': float(dre.deducoes_receita),
                'receita_liquida': float(dre.receita_liquida),
                'margem_percent': round(dre.margem_bruta_percent, 2)
            })
            
            # Custo
            custos_detalhados.append({
                'canal': canal,
                'canal_nome': self.CANAIS.get(canal, canal),
                'cmv': float(dre.custo_produtos_vendidos),
                'lucro_bruto': float(dre.lucro_bruto)
            })
            
            # Despesas (TODAS as categorias)
            despesas_detalhadas.append({
                'canal': canal,
                'canal_nome': self.CANAIS.get(canal, canal),
                'vendas': float(dre.despesas_vendas),
                'pessoal': float(dre.despesas_pessoal),
                'administrativas': float(dre.despesas_administrativas),
                'financeiras': float(dre.despesas_financeiras),
                'outras': float(dre.outras_despesas),
                'total': float(dre.total_despesas_operacionais)
            })
            
            receita_total_bruta += dre.receita_bruta
            receita_total_liquida += dre.receita_liquida
            custo_total += dre.custo_produtos_vendidos
            despesa_total += dre.total_despesas_operacionais
            lucro_bruto_total += dre.lucro_bruto
        
        # 3. Consolidado
        lucro_operacional_total = lucro_bruto_total - despesa_total
        impostos_total = sum(dres_canais[c].impostos for c in canais)
        lucro_liquido_total = lucro_operacional_total - impostos_total
        
        margem_bruta_consolidada = (lucro_bruto_total / receita_total_liquida * 100) if receita_total_liquida > 0 else 0
        margem_operacional_consolidada = (lucro_operacional_total / receita_total_liquida * 100) if receita_total_liquida > 0 else 0
        margem_liquida_consolidada = (lucro_liquido_total / receita_total_liquida * 100) if receita_total_liquida > 0 else 0
        
        return {
            'periodo': {
                'data_inicio': data_inicio.isoformat(),
                'data_fim': data_fim.isoformat()
            },
            'canais_selecionados': canais,
            'receitas': {
                'detalhado': receitas_detalhadas,
                'totais': {
                    'receita_bruta': float(receita_total_bruta),
                    'deducoes': sum(r['deducoes'] for r in receitas_detalhadas),
                    'receita_liquida': float(receita_total_liquida),
                    'margem_percent': round(margem_bruta_consolidada, 2)
                }
            },
            'custos': {
                'detalhado': custos_detalhados,
                'totais': {
                    'cmv': float(custo_total),
                    'lucro_bruto': float(lucro_bruto_total)
                }
            },
            'despesas': {
                'detalhado': despesas_detalhadas,
                'totais': {
                    'vendas': sum(d['vendas'] for d in despesas_detalhadas),
                    'pessoal': sum(d['pessoal'] for d in despesas_detalhadas),
                    'administrativas': sum(d['administrativas'] for d in despesas_detalhadas),
                    'financeiras': sum(d['financeiras'] for d in despesas_detalhadas),
                    'outras': sum(d['outras'] for d in despesas_detalhadas),
                    'total': float(despesa_total)
                }
            },
            'consolidado': {
                'lucro_operacional': float(lucro_operacional_total),
                'margem_operacional_percent': round(margem_operacional_consolidada, 2),
                'impostos': float(impostos_total),
                'lucro_liquido': float(lucro_liquido_total),
                'margem_liquida_percent': round(margem_liquida_consolidada, 2),
                'status': 'lucro' if lucro_liquido_total > 0 else 'prejuizo' if lucro_liquido_total < 0 else 'equilibrio'
            }
        }
    
    def salvar_alocacao_despesa(
        self,
        usuario_id: int,
        data_inicio: date,
        data_fim: date,
        categoria: str,
        valor_total: float,
        modo: str,  # 'proporcional' ou 'manual'
        canais: List[str],
        alocacao_manual: Optional[Dict] = None,  # Se modo='manual': {canal: {valor, percentual}}
        usar_faturamento: bool = True
    ) -> AlocacaoDespesaCanal:
        """
        Salva como uma despesa será alocada aos canais
        
        Exemplo proporcional:
            categoria='aluguel', valor_total=7000, modo='proporcional', canais=['loja_fisica', 'mercado_livre']
            - Será dividido proporcionalmente ao faturamento de cada canal
        
        Exemplo manual:
            categoria='aluguel', valor_total=7000, modo='manual', canais=['loja_fisica', 'mercado_livre']
            alocacao_manual={
                'loja_fisica': {'valor': 5000, 'percentual': 71.43},
                'mercado_livre': {'valor': 2000, 'percentual': 28.57}
            }
        """
        alocacao = AlocacaoDespesaCanal(
            usuario_id=usuario_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            categoria_despesa=categoria,
            valor_total=valor_total,
            modo_alocacao=modo,
            canais_afetados=json.dumps(canais),
            usar_faturamento=usar_faturamento
        )
        
        if alocacao_manual:
            alocacao.alocacao_manual = json.dumps(alocacao_manual)
        
        self.db.add(alocacao)
        self.db.commit()
        self.db.refresh(alocacao)
        
        return alocacao
