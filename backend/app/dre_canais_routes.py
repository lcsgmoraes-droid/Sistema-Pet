"""
Endpoint DRE por Canal - Retorna dados estruturados com nome e cor por canal
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, extract
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict
from pydantic import BaseModel

from app.db import get_session
from app.auth import get_current_user
from app.auth.dependencies import get_current_user_and_tenant
from app.models import User
from app.vendas_models import Venda, VendaItem
from app.produtos_models import Produto

router = APIRouter(prefix="/financeiro/dre/canais", tags=["DRE por Canal"])


# ==================== CONFIGURAÇÃO DE CANAIS ====================

CANAIS_CONFIG = {
    'loja_fisica': {
        'nome': 'Loja Física',
        'cor': '#3b82f6',  # Azul
        'cor_bg': '#eff6ff'
    },
    'mercado_livre': {
        'nome': 'Mercado Livre',
        'cor': '#fbbf24',  # Amarelo
        'cor_bg': '#fef3c7'
    },
    'shopee': {
        'nome': 'Shopee',
        'cor': '#f97316',  # Laranja
        'cor_bg': '#ffedd5'
    },
    'amazon': {
        'nome': 'Amazon',
        'cor': '#16a34a',  # Verde
        'cor_bg': '#dcfce7'
    }
}


# ==================== SCHEMAS ====================

class LinhaCanal(BaseModel):
    """Uma linha da DRE de um canal específico"""
    descricao: str  # Ex: "Faturamento Mercado Livre"
    valor: float
    percentual: float
    cor: str  # Cor do canal
    cor_bg: str  # Cor de fundo
    canal: str  # ID do canal
    canal_nome: str  # Nome do canal
    nivel: int  # 0=seção, 1=linha normal, 2=total
    tipo: str  # 'receita', 'deducao', 'custo', 'despesa', 'lucro'


class DREPorCanalResponse(BaseModel):
    """DRE completa com linhas separadas por canal"""
    periodo: str
    mes: int
    ano: int
    linhas: List[LinhaCanal]
    totais: Dict
    canais_encontrados: List[str]


# ==================== FUNÇÕES AUXILIARES ====================

def obter_vendas_por_canal(db: Session, mes: int, ano: int, user_id: int) -> Dict:
    """Retorna vendas agrupadas por canal"""
    vendas = db.query(Venda).filter(
        and_(
            Venda.user_id == user_id,
            extract('month', Venda.data_venda) == mes,
            extract('year', Venda.data_venda) == ano,
            Venda.status.in_(['finalizada', 'pago_nf', 'baixa_parcial'])
        )
    ).all()
    
    # Agrupar por canal
    dados_por_canal = {}
    
    for venda in vendas:
        canal = venda.canal or 'loja_fisica'  # Default para loja física
        
        if canal not in dados_por_canal:
            dados_por_canal[canal] = {
                'receita_bruta': Decimal('0'),
                'descontos': Decimal('0'),
                'cmv': Decimal('0'),
                'vendas': []
            }
        
        # Receita
        receita = venda.subtotal + (venda.taxa_entrega or 0)
        dados_por_canal[canal]['receita_bruta'] += receita
        dados_por_canal[canal]['descontos'] += (venda.desconto_valor or 0)
        dados_por_canal[canal]['vendas'].append(venda)
        
        # CMV
        itens = db.query(VendaItem).filter(VendaItem.venda_id == venda.id).all()
        for item in itens:
            produto = db.query(Produto).filter(Produto.id == item.produto_id).first()
            if produto and produto.preco_custo:
                custo = Decimal(str(produto.preco_custo)) * item.quantidade
                dados_por_canal[canal]['cmv'] += custo
    
    return dados_por_canal


# ==================== ENDPOINT PRINCIPAL ====================

@router.get("", response_model=DREPorCanalResponse)
def gerar_dre_por_canais(
    ano: int = Query(..., description="Ano do DRE"),
    mes: int = Query(..., description="Mês do DRE (1-12)"),
    canais: str = Query("loja_fisica", description="Canais selecionados separados por vírgula (ex: loja_fisica,mercado_livre)"),
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    Gera DRE com cada canal em linhas separadas
    
    Cada linha terá:
    - Nome do canal na descrição (ex: "Descontos Concedidos Loja Física")
    - Cor específica do canal
    - Valores individuais
    """
    
    if mes < 1 or mes > 12:
        raise HTTPException(status_code=400, detail="Mês deve estar entre 1 e 12")
    
    # Processar canais selecionados
    canais_selecionados = [c.strip() for c in canais.split(',') if c.strip()]
    if not canais_selecionados:
        canais_selecionados = ['loja_fisica']
    
    meses = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
             'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    periodo = f"{meses[mes]}/{ano}"
    
    # Extrair user e tenant
    user, tenant_id = user_and_tenant
    
    # Obter dados por canal
    dados_canais = obter_vendas_por_canal(db, mes, ano, user.id)
    
    # Filtrar apenas os canais selecionados e garantir que existam
    dados_canais_filtrados = {}
    for canal_id in canais_selecionados:
        if canal_id in dados_canais:
            dados_canais_filtrados[canal_id] = dados_canais[canal_id]
        else:
            # Canal selecionado mas sem vendas - adicionar com valores zerados
            dados_canais_filtrados[canal_id] = {
                'receita_bruta': Decimal('0'),
                'descontos': Decimal('0'),
                'cmv': Decimal('0'),
                'vendas': []
            }
    
    # Usar apenas os canais filtrados
    dados_canais = dados_canais_filtrados
    
    # Calcular totais
    receita_bruta_total = sum(d['receita_bruta'] for d in dados_canais.values())
    descontos_total = sum(d['descontos'] for d in dados_canais.values())
    cmv_total = sum(d['cmv'] for d in dados_canais.values())
    receita_liquida_total = receita_bruta_total - descontos_total
    lucro_bruto_total = receita_liquida_total - cmv_total
    
    # Montar linhas
    linhas = []
    
    # ========== RECEITA BRUTA ==========
    linhas.append(LinhaCanal(
        descricao="(+) RECEITA BRUTA",
        valor=float(receita_bruta_total),
        percentual=100.0,
        cor="#000000",
        cor_bg="#f3f4f6",
        canal="total",
        canal_nome="Total",
        nivel=0,
        tipo="receita"
    ))
    
    # Linhas por canal - Vendas de Produtos
    for canal, dados in sorted(dados_canais.items()):
        config = CANAIS_CONFIG.get(canal, CANAIS_CONFIG['loja_fisica'])
        receita = float(dados['receita_bruta'])
        percentual = (receita / float(receita_bruta_total) * 100) if receita_bruta_total > 0 else 0
        
        linhas.append(LinhaCanal(
            descricao=f"Vendas de Produtos {config['nome']}",  # ← Nome do canal na descrição
            valor=receita,
            percentual=round(percentual, 2),
            cor=config['cor'],
            cor_bg="#ffffff",
            canal=canal,
            canal_nome=config['nome'],
            nivel=1,
            tipo="receita"
        ))
    
    # Vendas de Serviços por canal (REMOVIDO - será adicionado apenas se houver valores reais)
    
    # ========== DEDUÇÕES ==========
    linhas.append(LinhaCanal(
        descricao="(-) DEDUÇÕES DA RECEITA",
        valor=float(descontos_total),
        percentual=round((float(descontos_total) / float(receita_bruta_total) * 100) if receita_bruta_total > 0 else 0, 2),
        cor="#dc2626",
        cor_bg="#fef2f2",
        canal="total",
        canal_nome="Total",
        nivel=0,
        tipo="deducao"
    ))
    
    # Descontos por canal
    for canal, dados in sorted(dados_canais.items()):
        config = CANAIS_CONFIG.get(canal, CANAIS_CONFIG['loja_fisica'])
        desconto = float(dados['descontos'])
        percentual = (desconto / float(receita_bruta_total) * 100) if receita_bruta_total > 0 else 0
        
        linhas.append(LinhaCanal(
            descricao=f"Descontos Concedidos {config['nome']}",  # ← Nome do canal na descrição
            valor=desconto,
            percentual=round(percentual, 2),
            cor=config['cor'],
            cor_bg="#ffffff",
            canal=canal,
            canal_nome=config['nome'],
            nivel=1,
            tipo="deducao"
        ))
    
    # Devoluções por canal (REMOVIDO - será adicionado apenas se houver valores reais)
    
    # ========== RECEITA LÍQUIDA ==========
    linhas.append(LinhaCanal(
        descricao="(=) RECEITA LÍQUIDA",
        valor=float(receita_liquida_total),
        percentual=round((float(receita_liquida_total) / float(receita_bruta_total) * 100) if receita_bruta_total > 0 else 0, 2),
        cor="#059669",
        cor_bg="#d1fae5",
        canal="total",
        canal_nome="Total",
        nivel=0,
        tipo="receita"
    ))
    
    # ========== CMV ==========
    linhas.append(LinhaCanal(
        descricao="(-) CUSTO DAS MERCADORIAS VENDIDAS (CMV)",
        valor=float(cmv_total),
        percentual=round((float(cmv_total) / float(receita_bruta_total) * 100) if receita_bruta_total > 0 else 0, 2),
        cor="#dc2626",
        cor_bg="#fef2f2",
        canal="total",
        canal_nome="Total",
        nivel=0,
        tipo="custo"
    ))
    
    # CMV por canal
    for canal, dados in sorted(dados_canais.items()):
        config = CANAIS_CONFIG.get(canal, CANAIS_CONFIG['loja_fisica'])
        cmv = float(dados['cmv'])
        percentual = (cmv / float(receita_bruta_total) * 100) if receita_bruta_total > 0 else 0
        
        linhas.append(LinhaCanal(
            descricao=f"CMV {config['nome']}",  # ← Nome do canal na descrição
            valor=cmv,
            percentual=round(percentual, 2),
            cor=config['cor'],
            cor_bg="#ffffff",
            canal=canal,
            canal_nome=config['nome'],
            nivel=1,
            tipo="custo"
        ))
    
    # ========== LUCRO BRUTO ==========
    linhas.append(LinhaCanal(
        descricao="(=) LUCRO BRUTO",
        valor=float(lucro_bruto_total),
        percentual=round((float(lucro_bruto_total) / float(receita_bruta_total) * 100) if receita_bruta_total > 0 else 0, 2),
        cor="#059669",
        cor_bg="#d1fae5",
        canal="total",
        canal_nome="Total",
        nivel=0,
        tipo="lucro"
    ))
    
    # ========== DESPESAS OPERACIONAIS ==========
    # TODO: Buscar despesas reais de contas_pagar vinculadas às subcategorias DRE
    # Por enquanto, não exibir seção se não houver despesas
    
    # ========== RESULTADO OPERACIONAL ==========
    linhas.append(LinhaCanal(
        descricao="(=) RESULTADO OPERACIONAL",
        valor=float(lucro_bruto_total),
        percentual=round((float(lucro_bruto_total) / float(receita_bruta_total) * 100) if receita_bruta_total > 0 else 0, 2),
        cor="#059669",
        cor_bg="#d1fae5",
        canal="total",
        canal_nome="Total",
        nivel=0,
        tipo="lucro"
    ))
    
    # ========== RESULTADO FINANCEIRO ==========
    # TODO: Buscar receitas/despesas financeiras de contas_receber/pagar
    # Por enquanto, não exibir seção se não houver valores
    
    # ========== LUCRO LÍQUIDO ==========
    linhas.append(LinhaCanal(
        descricao="(=) LUCRO/PREJUÍZO LÍQUIDO",
        valor=float(lucro_bruto_total),
        percentual=round((float(lucro_bruto_total) / float(receita_bruta_total) * 100) if receita_bruta_total > 0 else 0, 2),
        cor="#059669",
        cor_bg="#d1fae5",
        canal="total",
        canal_nome="Total",
        nivel=0,
        tipo="lucro"
    ))
    
    # Totais
    totais = {
        'receita_bruta': float(receita_bruta_total),
        'descontos': float(descontos_total),
        'receita_liquida': float(receita_liquida_total),
        'cmv': float(cmv_total),
        'lucro_bruto': float(lucro_bruto_total),
        'despesas_operacionais': 0.0,
        'resultado_operacional': float(lucro_bruto_total),
        'resultado_financeiro': 0.0,
        'lucro_liquido': float(lucro_bruto_total),
        'margem_bruta': round((float(lucro_bruto_total) / float(receita_liquida_total) * 100) if receita_liquida_total > 0 else 0, 2),
        'margem_liquida': round((float(lucro_bruto_total) / float(receita_liquida_total) * 100) if receita_liquida_total > 0 else 0, 2)
    }
    
    return DREPorCanalResponse(
        periodo=periodo,
        mes=mes,
        ano=ano,
        linhas=linhas,
        totais=totais,
        canais_encontrados=list(dados_canais.keys())
    )
