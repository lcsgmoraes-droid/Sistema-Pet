"""
ABA 7: DRE por Canal - Suporte para múltiplos canais de venda
Loja Física, Mercado Livre, Shopee, Amazon
"""

from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import date
import json

from app.ia.aba7_models import DREPeriodo
from app.ia.aba7_dre import DREService


class DRECanalService:
    """Serviço para cálculo de DRE por canal de venda"""
    
    CANAIS_DISPONIVEIS = {
        'loja_fisica': 'Loja Física (PDV)',
        'mercado_livre': 'Mercado Livre',
        'shopee': 'Shopee',
        'amazon': 'Amazon',
        'site': 'Site Próprio',
        'instagram': 'Instagram/WhatsApp'
    }
    
    def __init__(self, db: Session):
        self.db = db
        self.dre_service = DREService(db)
    
    def calcular_dre_por_canal(
        self,
        usuario_id: int,
        data_inicio: date,
        data_fim: date,
        canal: str
    ) -> DREPeriodo:
        """
        Calcula DRE de um canal específico
        
        Args:
            canal: 'loja_fisica', 'mercado_livre', 'shopee', 'amazon'
        """
        from app.models import Venda, VendaItem, Produto, LancamentoFluxoCaixa
        
        # 1. Filtrar vendas do canal
        vendas = (
            self.db.query(Venda)
            .filter(
                Venda.user_id == usuario_id,
                Venda.criado_em >= data_inicio,
                Venda.criado_em <= data_fim,
                Venda.status.in_(['finalizada', 'paga']),
                Venda.canal == canal  # ← Filtro por canal
            )
            .all()
        )
        
        # 2. Calcular métricas (igual ao DRE normal, mas filtrado por canal)
        receita_bruta = sum(v.valor_total or 0 for v in vendas)
        deducoes_receita = sum(v.desconto or 0 for v in vendas)
        receita_liquida = receita_bruta - deducoes_receita
        
        # 3. CMV
        custo_produtos = 0
        for venda in vendas:
            itens = self.db.query(VendaItem).filter(VendaItem.venda_id == venda.id).all()
            for item in itens:
                produto = self.db.query(Produto).filter(Produto.id == item.produto_id).first()
                if produto and produto.preco_custo:
                    custo_produtos += (produto.preco_custo * item.quantidade)
        
        lucro_bruto = receita_liquida - custo_produtos
        margem_bruta = (lucro_bruto / receita_liquida * 100) if receita_liquida > 0 else 0
        
        # 4. Despesas (proporcionais ao canal se necessário)
        # Por simplicidade, dividimos proporcionalmente à receita
        total_receita_periodo = self.db.query(
            func.sum(Venda.valor_total)
        ).filter(
            Venda.user_id == usuario_id,
            Venda.criado_em >= data_inicio,
            Venda.criado_em <= data_fim,
            Venda.status.in_(['finalizada', 'paga'])
        ).scalar() or 1
        
        proporcao_canal = receita_bruta / total_receita_periodo if total_receita_periodo > 0 else 0
        
        # Despesas totais do período
        despesas_vendas_total = self.db.query(func.sum(LancamentoFluxoCaixa.valor)).filter(
            LancamentoFluxoCaixa.user_id == usuario_id,
            LancamentoFluxoCaixa.data >= data_inicio,
            LancamentoFluxoCaixa.data <= data_fim,
            LancamentoFluxoCaixa.tipo == 'saida',
            LancamentoFluxoCaixa.categoria.in_(['Vendas', 'Marketing', 'Comissões'])
        ).scalar() or 0
        
        despesas_admin_total = self.db.query(func.sum(LancamentoFluxoCaixa.valor)).filter(
            LancamentoFluxoCaixa.user_id == usuario_id,
            LancamentoFluxoCaixa.data >= data_inicio,
            LancamentoFluxoCaixa.data <= data_fim,
            LancamentoFluxoCaixa.tipo == 'saida',
            LancamentoFluxoCaixa.categoria.in_(['Administrativo', 'Salários', 'Aluguel'])
        ).scalar() or 0
        
        despesas_financeiras_total = self.db.query(func.sum(LancamentoFluxoCaixa.valor)).filter(
            LancamentoFluxoCaixa.user_id == usuario_id,
            LancamentoFluxoCaixa.data >= data_inicio,
            LancamentoFluxoCaixa.data <= data_fim,
            LancamentoFluxoCaixa.tipo == 'saida',
            LancamentoFluxoCaixa.categoria.in_(['Financeiro', 'Juros', 'Taxas'])
        ).scalar() or 0
        
        outras_despesas_total = self.db.query(func.sum(LancamentoFluxoCaixa.valor)).filter(
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
        
        # Despesas proporcionais
        despesas_vendas = despesas_vendas_total * proporcao_canal
        despesas_administrativas = despesas_admin_total * proporcao_canal
        despesas_financeiras = despesas_financeiras_total * proporcao_canal
        outras_despesas = outras_despesas_total * proporcao_canal
        
        total_despesas = despesas_vendas + despesas_administrativas + despesas_financeiras + outras_despesas
        
        # 5. Resultado
        lucro_operacional = lucro_bruto - total_despesas
        margem_operacional = (lucro_operacional / receita_liquida * 100) if receita_liquida > 0 else 0
        
        # 6. Impostos
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
        
        # 7. Status
        if lucro_liquido > 0:
            status = "lucro"
        elif lucro_liquido < 0:
            status = "prejuizo"
        else:
            status = "equilibrio"
        
        # 8. Score
        score = 50
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
        
        # 9. Salvar ou atualizar
        dre_existente = (
            self.db.query(DREPeriodo)
            .filter(
                DREPeriodo.usuario_id == usuario_id,
                DREPeriodo.data_inicio == data_inicio,
                DREPeriodo.data_fim == data_fim,
                DREPeriodo.canal == canal
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
                ano=data_inicio.year,
                canal=canal,
                canais_incluidos=json.dumps([canal])
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
        
        self.db.commit()
        self.db.refresh(dre)
        
        return dre
    
    def calcular_dre_consolidado(
        self,
        usuario_id: int,
        data_inicio: date,
        data_fim: date,
        canais: List[str]
    ) -> DREPeriodo:
        """
        Calcula DRE consolidado de múltiplos canais
        
        Args:
            canais: ['loja_fisica', 'mercado_livre', 'shopee']
        """
        # 1. Calcular DRE individual de cada canal
        dres_individuais = []
        for canal in canais:
            dre_canal = self.calcular_dre_por_canal(
                usuario_id, data_inicio, data_fim, canal
            )
            dres_individuais.append(dre_canal)
        
        # 2. Somar todos os valores
        receita_bruta = sum(d.receita_bruta for d in dres_individuais)
        deducoes_receita = sum(d.deducoes_receita for d in dres_individuais)
        receita_liquida = sum(d.receita_liquida for d in dres_individuais)
        custo_produtos = sum(d.custo_produtos_vendidos for d in dres_individuais)
        lucro_bruto = sum(d.lucro_bruto for d in dres_individuais)
        despesas_vendas = sum(d.despesas_vendas for d in dres_individuais)
        despesas_admin = sum(d.despesas_administrativas for d in dres_individuais)
        despesas_financeiras = sum(d.despesas_financeiras for d in dres_individuais)
        outras_despesas = sum(d.outras_despesas for d in dres_individuais)
        total_despesas = sum(d.total_despesas_operacionais for d in dres_individuais)
        lucro_operacional = sum(d.lucro_operacional for d in dres_individuais)
        impostos = sum(d.impostos for d in dres_individuais)
        lucro_liquido = sum(d.lucro_liquido for d in dres_individuais)
        
        # 3. Recalcular margens
        margem_bruta = (lucro_bruto / receita_liquida * 100) if receita_liquida > 0 else 0
        margem_operacional = (lucro_operacional / receita_liquida * 100) if receita_liquida > 0 else 0
        margem_liquida = (lucro_liquido / receita_liquida * 100) if receita_liquida > 0 else 0
        aliquota_efetiva = (impostos / receita_bruta * 100) if receita_bruta > 0 else 0
        
        # 4. Status
        if lucro_liquido > 0:
            status = "lucro"
        elif lucro_liquido < 0:
            status = "prejuizo"
        else:
            status = "equilibrio"
        
        # 5. Score
        score = 50
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
        
        # 6. Salvar DRE consolidado
        canal_consolidado = "consolidado_" + "_".join(sorted(canais))
        
        dre_existente = (
            self.db.query(DREPeriodo)
            .filter(
                DREPeriodo.usuario_id == usuario_id,
                DREPeriodo.data_inicio == data_inicio,
                DREPeriodo.data_fim == data_fim,
                DREPeriodo.canal == canal_consolidado
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
                ano=data_inicio.year,
                canal=canal_consolidado,
                canais_incluidos=json.dumps(canais)
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
        dre.despesas_administrativas = despesas_admin
        dre.despesas_financeiras = despesas_financeiras
        dre.outras_despesas = outras_despesas
        dre.total_despesas_operacionais = total_despesas
        dre.lucro_operacional = lucro_operacional
        dre.margem_operacional_percent = margem_operacional
        dre.impostos = impostos
        dre.aliquota_efetiva_percent = aliquota_efetiva
        dre.lucro_liquido = lucro_liquido
        dre.margem_liquida_percent = margem_liquida
        dre.status = status
        dre.score_saude = score
        
        self.db.commit()
        self.db.refresh(dre)
        
        return dre
    
    def listar_canais_disponiveis(self) -> Dict[str, str]:
        """Retorna lista de canais suportados"""
        return self.CANAIS_DISPONIVEIS
    
    def listar_dres_por_canal(
        self,
        usuario_id: int,
        data_inicio: date,
        data_fim: date
    ) -> Dict[str, Optional[DREPeriodo]]:
        """
        Retorna DRE de todos os canais em um período
        
        Returns:
            {
                'loja_fisica': DREPeriodo(...),
                'mercado_livre': DREPeriodo(...),
                'shopee': None,  # Não calculado
                ...
            }
        """
        resultado = {}
        
        for canal_id, canal_nome in self.CANAIS_DISPONIVEIS.items():
            dre = (
                self.db.query(DREPeriodo)
                .filter(
                    DREPeriodo.usuario_id == usuario_id,
                    DREPeriodo.data_inicio == data_inicio,
                    DREPeriodo.data_fim == data_fim,
                    DREPeriodo.canal == canal_id
                )
                .first()
            )
            resultado[canal_id] = dre
        
        return resultado
