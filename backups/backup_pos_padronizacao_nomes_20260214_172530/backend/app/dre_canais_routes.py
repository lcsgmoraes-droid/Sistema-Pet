"""
Endpoint DRE por Canal - Retorna dados estruturados com nome e cor por canal
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, extract
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
from app.financeiro_models import ContaPagar
from app.dre_plano_contas_models import DRESubcategoria

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
                'receita_produtos': Decimal('0'),  # subtotal (só produtos)
                'taxa_entrega': Decimal('0'),  # frete cobrado do cliente
                'descontos': Decimal('0'),
                'cmv': Decimal('0'),
                'vendas': []
            }
        
        # Receita de Produtos (apenas subtotal, sem frete)
        dados_por_canal[canal]['receita_produtos'] += venda.subtotal
        
        # Taxa de Frete (o que o cliente pagou)
        if venda.taxa_entrega:
            dados_por_canal[canal]['taxa_entrega'] += venda.taxa_entrega
        
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


def obter_despesas_operacionais(db: Session, mes: int, ano: int, tenant_id: str) -> Decimal:
    """
    Calcula o total de despesas operacionais do período
    Inclui: TODAS as despesas operacionais (salários, fretes, comissões, administrativas, etc.)
    Exclui: Apenas compras de mercadorias (que vão para CMV)
    """
    from app.produtos_models import NotaEntrada
    
    # Buscar contas a pagar do período (TODAS, exceto compras de mercadorias)
    # ✅ USA DATA_EMISSAO (regime de competência)
    contas_pagar = db.query(ContaPagar).filter(
        and_(
            ContaPagar.tenant_id == tenant_id,
            extract('month', ContaPagar.data_emissao) == mes,  # ✅ Competência
            extract('year', ContaPagar.data_emissao) == ano,
            ContaPagar.nota_entrada_id.is_(None)  # Exclui compras de mercadorias (CMV)
        )
    ).all()
    
    total_despesas = Decimal('0')
    for conta in contas_pagar:
        total_despesas += conta.valor_original
    
    # Adicionar fretes de notas de entrada (despesa operacional, não CMV)
    notas = db.query(NotaEntrada).filter(
        and_(
            NotaEntrada.tenant_id == tenant_id,
            extract('month', NotaEntrada.data_emissao) == mes,
            extract('year', NotaEntrada.data_emissao) == ano
        )
    ).all()
    
    for nota in notas:
        if nota.valor_frete:
            total_despesas += Decimal(str(nota.valor_frete))
    
    return total_despesas


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
                'receita_produtos': Decimal('0'),
                'taxa_entrega': Decimal('0'),
                'descontos': Decimal('0'),
                'cmv': Decimal('0'),
                'vendas': []
            }
    
    # Usar apenas os canais filtrados
    dados_canais = dados_canais_filtrados
    
    # Calcular totais
    receita_produtos_total = sum(d['receita_produtos'] for d in dados_canais.values())
    taxa_entrega_total = sum(d['taxa_entrega'] for d in dados_canais.values())
    receita_bruta_total = receita_produtos_total + taxa_entrega_total
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
    
    # Linhas por canal - Vendas de Produtos (apenas subtotal, sem frete)
    for canal, dados in sorted(dados_canais.items()):
        config = CANAIS_CONFIG.get(canal, CANAIS_CONFIG['loja_fisica'])
        receita_produtos = float(dados['receita_produtos'])
        percentual = (receita_produtos / float(receita_bruta_total) * 100) if receita_bruta_total > 0 else 0
        
        linhas.append(LinhaCanal(
            descricao=f"Vendas de Produtos {config['nome']}",
            valor=receita_produtos,
            percentual=round(percentual, 2),
            cor=config['cor'],
            cor_bg="#ffffff",
            canal=canal,
            canal_nome=config['nome'],
            nivel=1,
            tipo="receita"
        ))
    
    # ========== TAXA DE FRETE (RECEITA) POR CANAL ==========
    # Taxa de frete paga pelo cliente, entra como receita
    # Vem diretamente do campo taxa_entrega das vendas
    
    from app.dre_plano_contas_models import DRESubcategoria
    
    for canal in sorted(dados_canais.keys()):
        config = CANAIS_CONFIG.get(canal, CANAIS_CONFIG['loja_fisica'])
        taxa_frete_canal = float(dados_canais[canal]['taxa_entrega'])
        
        if taxa_frete_canal > 0:
            percentual = (taxa_frete_canal / float(receita_bruta_total) * 100) if receita_bruta_total > 0 else 0
            
            linhas.append(LinhaCanal(
                descricao=f"Taxa de Frete {config['nome']}",
                valor=taxa_frete_canal,
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
    
    # ========== FRETES SOBRE COMPRAS (CMV) ==========
    # Frete pago na compra de mercadorias
    
    subcategoria_frete_compras = db.query(DRESubcategoria).filter(
        DRESubcategoria.tenant_id == tenant_id,
        DRESubcategoria.nome == "Fretes sobre Compras"
    ).first()
    
    if subcategoria_frete_compras:
        contas_frete_compras = db.query(ContaPagar).filter(
            and_(
                ContaPagar.tenant_id == tenant_id,
                extract('month', ContaPagar.data_emissao) == mes,  # ✅ Competência
                extract('year', ContaPagar.data_emissao) == ano,
                ContaPagar.dre_subcategoria_id == subcategoria_frete_compras.id
            )
        ).all()
        
        total_frete_compras = sum(conta.valor_original for conta in contas_frete_compras)
        
        if total_frete_compras > 0:
            cmv_total += total_frete_compras
            percentual = (float(total_frete_compras) / float(receita_bruta_total) * 100) if receita_bruta_total > 0 else 0
            
            linhas.append(LinhaCanal(
                descricao="   Fretes sobre Compras",
                valor=float(total_frete_compras),
                percentual=round(percentual, 2),
                cor="#6b7280",
                cor_bg="#ffffff",
                canal="total",
                canal_nome="Total",
                nivel=1,
                tipo="custo"
            ))
    
    # Recalcular lucro bruto com frete de compras
    lucro_bruto_total = receita_liquida_total - cmv_total
    
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
    # Primeiro, buscar subcategoria antiga "Fretes sobre Vendas" para contas legadas
    subcategoria_antiga = db.query(DRESubcategoria).filter(
        DRESubcategoria.tenant_id == tenant_id,
        DRESubcategoria.nome.like('Fretes sobre Vendas%')
    ).first()
    
    # Calcular Frete Operacional por canal
    total_frete_op_geral = Decimal('0')
    detalhes_frete_op = []
    
    for canal in sorted(dados_canais.keys()):
            config = CANAIS_CONFIG.get(canal, CANAIS_CONFIG['loja_fisica'])
            total_frete_op_canal = Decimal('0')
            
            # Buscar subcategoria específica do canal (nova, sem acentos)
            nome_canal = config['nome'].replace('í', 'i')
            subcategoria_frete_op = db.query(DRESubcategoria).filter(
                DRESubcategoria.tenant_id == tenant_id,
                DRESubcategoria.nome == f"Frete Operacional - {nome_canal}"
            ).first()
            
            # Buscar contas com a subcategoria nova
            if subcategoria_frete_op:
                contas_frete_op = db.query(ContaPagar).filter(
                    and_(
                        ContaPagar.tenant_id == tenant_id,
                        extract('month', ContaPagar.data_emissao) == mes,  # ✅ Competência
                        extract('year', ContaPagar.data_emissao) == ano,
                        ContaPagar.dre_subcategoria_id == subcategoria_frete_op.id,
                        ContaPagar.canal == canal
                    )
                ).all()
                total_frete_op_canal += sum(conta.valor_original for conta in contas_frete_op)
            
            # ✅ INCLUIR contas antigas com "Fretes sobre Vendas" que sejam "Custo fixo entrega"
            # (apenas no canal loja_fisica, pois vendas antigas não tinham campo canal preenchido)
            if subcategoria_antiga and canal == 'loja_fisica':
                contas_antigas_frete = db.query(ContaPagar).filter(
                    and_(
                        ContaPagar.tenant_id == tenant_id,
                        extract('month', ContaPagar.data_emissao) == mes,  # ✅ Competência
                        extract('year', ContaPagar.data_emissao) == ano,
                        ContaPagar.dre_subcategoria_id == subcategoria_antiga.id,
                        or_(
                            ContaPagar.descricao.like('Custo fixo entrega%'),
                            ContaPagar.descricao.like('Controla RH entrega%')
                        ),
                        ContaPagar.canal.is_(None)  # Apenas contas sem canal (antigas)
                    )
                ).all()
                total_frete_op_canal += sum(conta.valor_original for conta in contas_antigas_frete)
            
            total_frete_op_geral += total_frete_op_canal
            
            if total_frete_op_canal > 0:
                percentual = (float(total_frete_op_canal) / float(receita_bruta_total) * 100) if receita_bruta_total > 0 else 0
                
                detalhes_frete_op.append(LinhaCanal(
                    descricao=f"   Frete Operacional {config['nome']}",
                    valor=float(total_frete_op_canal),
                    percentual=round(percentual, 2),
                    cor=config['cor'],
                    cor_bg="#ffffff",
                    canal=canal,
                    canal_nome=config['nome'],
                    nivel=1,
                    tipo="despesa"
                ))
    
    # Calcular Comissão Entregador por canal
    total_comissao_geral = Decimal('0')
    detalhes_comissao = []
    
    for canal in sorted(dados_canais.keys()):
            config = CANAIS_CONFIG.get(canal, CANAIS_CONFIG['loja_fisica'])
            total_comissao_canal = Decimal('0')
            
            # Buscar subcategoria específica do canal (nova, sem acentos)
            nome_canal = config['nome'].replace('í', 'i')
            subcategoria_comissao = db.query(DRESubcategoria).filter(
                DRESubcategoria.tenant_id == tenant_id,
                DRESubcategoria.nome == f"Comissao Entregador - {nome_canal}"
            ).first()
            
            # Buscar contas com a subcategoria nova
            if subcategoria_comissao:
                contas_comissao = db.query(ContaPagar).filter(
                    and_(
                        ContaPagar.tenant_id == tenant_id,
                        extract('month', ContaPagar.data_emissao) == mes,  # ✅ Competência
                        extract('year', ContaPagar.data_emissao) == ano,
                        ContaPagar.dre_subcategoria_id == subcategoria_comissao.id,
                        ContaPagar.canal == canal
                    )
                ).all()
                total_comissao_canal += sum(conta.valor_original for conta in contas_comissao)
            
            # ✅ INCLUIR contas antigas com "Fretes sobre Vendas" que sejam "Taxa de entrega"
            # (apenas no canal loja_fisica, pois vendas antigas não tinham campo canal preenchido)
            if subcategoria_antiga and canal == 'loja_fisica':
                contas_antigas_comissao = db.query(ContaPagar).filter(
                    and_(
                        ContaPagar.tenant_id == tenant_id,
                        extract('month', ContaPagar.data_emissao) == mes,  # ✅ Competência
                        extract('year', ContaPagar.data_emissao) == ano,
                        ContaPagar.dre_subcategoria_id == subcategoria_antiga.id,
                        ContaPagar.descricao.like('Taxa de entrega%'),
                        ContaPagar.canal.is_(None)  # Apenas contas sem canal (antigas)
                    )
                ).all()
                total_comissao_canal += sum(conta.valor_original for conta in contas_antigas_comissao)
            
            total_comissao_geral += total_comissao_canal
            
            if total_comissao_canal > 0:
                percentual = (float(total_comissao_canal) / float(receita_bruta_total) * 100) if receita_bruta_total > 0 else 0
                
                detalhes_comissao.append(LinhaCanal(
                    descricao=f"   Comissão Entregador {config['nome']}",
                    valor=float(total_comissao_canal),
                    percentual=round(percentual, 2),
                    cor=config['cor'],
                    cor_bg="#ffffff",
                    canal=canal,
                    canal_nome=config['nome'],
                    nivel=1,
                    tipo="despesa"
                ))
    
    # Calcular Comissões de Vendas - Vendedores por canal
    total_comissao_vendedores_geral = Decimal('0')
    detalhes_comissao_vendedores = []
    
    for canal in sorted(dados_canais.keys()):
        config = CANAIS_CONFIG.get(canal, CANAIS_CONFIG['loja_fisica'])
        total_comissao_vendedores_canal = Decimal('0')
        
        # Buscar subcategoria "Comissões de Vendas - Vendedores"
        subcategoria_comissao_vendedores = db.query(DRESubcategoria).filter(
            DRESubcategoria.tenant_id == tenant_id,
            DRESubcategoria.nome.like('Comiss%es de Vendas - Vendedores')
        ).first()
        
        # Buscar contas
        if subcategoria_comissao_vendedores:
            contas_comissao_vendedores = db.query(ContaPagar).filter(
                and_(
                    ContaPagar.tenant_id == tenant_id,
                    extract('month', ContaPagar.data_emissao) == mes,  # ✅ Competência (data da venda)
                    extract('year', ContaPagar.data_emissao) == ano,
                    ContaPagar.dre_subcategoria_id == subcategoria_comissao_vendedores.id,
                    or_(ContaPagar.canal == canal, ContaPagar.canal.is_(None))
                )
            ).all()
            total_comissao_vendedores_canal += sum(conta.valor_original for conta in contas_comissao_vendedores)
        
        total_comissao_vendedores_geral += total_comissao_vendedores_canal
        
        if total_comissao_vendedores_canal > 0:
            percentual = (float(total_comissao_vendedores_canal) / float(receita_bruta_total) * 100) if receita_bruta_total > 0 else 0
            
            detalhes_comissao_vendedores.append(LinhaCanal(
                descricao=f"   Comissões de Vendas {config['nome']}",
                valor=float(total_comissao_vendedores_canal),
                percentual=round(percentual, 2),
                cor=config['cor'],
                cor_bg="#ffffff",
                canal=canal,
                canal_nome=config['nome'],
                nivel=1,
                tipo="despesa"
            ))
    
    # Calcular Taxas de Cartao/PIX por canal e tipo
    total_taxas_cartao_geral = Decimal('0')
    detalhes_taxas_cartao = []

    tipos_taxas = [
        ("Taxas de Cartão de Crédito", "Taxas de Cartão de Crédito"),
        ("Taxas de Cartão de Débito", "Taxas de Cartão de Débito"),
        ("Taxa de PIX", "Taxa de PIX")
    ]

    for canal in sorted(dados_canais.keys()):
        config = CANAIS_CONFIG.get(canal, CANAIS_CONFIG['loja_fisica'])

        for nome_base, label in tipos_taxas:
            total_taxa_tipo = Decimal('0')

            nomes_taxas = [
                f"{nome_base} - {config['nome']}",
                nome_base
            ]

            subcategorias_taxas = db.query(DRESubcategoria).filter(
                and_(
                    DRESubcategoria.tenant_id == tenant_id,
                    DRESubcategoria.nome.in_(nomes_taxas)
                )
            ).all()

            if subcategorias_taxas:
                ids_taxas = [s.id for s in subcategorias_taxas]
                contas_taxas = db.query(ContaPagar).filter(
                    and_(
                        ContaPagar.tenant_id == tenant_id,
                        extract('month', ContaPagar.data_emissao) == mes,
                        extract('year', ContaPagar.data_emissao) == ano,
                        ContaPagar.dre_subcategoria_id.in_(ids_taxas),
                        or_(ContaPagar.canal == canal, ContaPagar.canal.is_(None))
                    )
                ).all()
                total_taxa_tipo += sum(conta.valor_original for conta in contas_taxas)

            if total_taxa_tipo > 0:
                total_taxas_cartao_geral += total_taxa_tipo
                percentual = (float(total_taxa_tipo) / float(receita_bruta_total) * 100) if receita_bruta_total > 0 else 0
                detalhes_taxas_cartao.append(LinhaCanal(
                    descricao=f"   {label} {config['nome']}",
                    valor=float(total_taxa_tipo),
                    percentual=round(percentual, 2),
                    cor=config['cor'],
                    cor_bg="#ffffff",
                    canal=canal,
                    canal_nome=config['nome'],
                    nivel=1,
                    tipo="despesa"
                ))

    # Calcular total de despesas operacionais (soma dos detalhes)
    despesas_operacionais_total = (
        total_frete_op_geral +
        total_comissao_geral +
        total_comissao_vendedores_geral +
        total_taxas_cartao_geral
    )
    
    # Calcular resultado operacional e lucro líquido
    resultado_operacional_total = lucro_bruto_total - despesas_operacionais_total
    lucro_liquido_total = resultado_operacional_total  # Por enquanto, sem resultado financeiro
    
    # Inserir linha principal de DESPESAS OPERACIONAIS
    if despesas_operacionais_total > 0:
        linhas.append(LinhaCanal(
            descricao="(-) DESPESAS OPERACIONAIS",
            valor=float(despesas_operacionais_total),
            percentual=round((float(despesas_operacionais_total) / float(receita_bruta_total) * 100) if receita_bruta_total > 0 else 0, 2),
            cor="#dc2626",
            cor_bg="#fef2f2",
            canal="total",
            canal_nome="Total",
            nivel=0,
            tipo="despesa"
        ))
        
        # Adicionar detalhes de Frete Operacional
        for detalhe in detalhes_frete_op:
            linhas.append(detalhe)
        
        # Adicionar detalhes de Comissão Entregador
        for detalhe in detalhes_comissao:
            linhas.append(detalhe)
        
        # Adicionar detalhes de Comissões de Vendas - Vendedores
        for detalhe in detalhes_comissao_vendedores:
            linhas.append(detalhe)

        # Adicionar detalhes de Taxas de Cartao
        for detalhe in detalhes_taxas_cartao:
            linhas.append(detalhe)
    
    # ========== RESULTADO OPERACIONAL ==========
    linhas.append(LinhaCanal(
        descricao="(=) RESULTADO OPERACIONAL",
        valor=float(resultado_operacional_total),
        percentual=round((float(resultado_operacional_total) / float(receita_bruta_total) * 100) if receita_bruta_total > 0 else 0, 2),
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
        valor=float(lucro_liquido_total),
        percentual=round((float(lucro_liquido_total) / float(receita_bruta_total) * 100) if receita_bruta_total > 0 else 0, 2),
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
        'despesas_operacionais': float(despesas_operacionais_total),
        'resultado_operacional': float(resultado_operacional_total),
        'resultado_financeiro': 0.0,
        'lucro_liquido': float(lucro_liquido_total),
        'margem_bruta': round((float(lucro_bruto_total) / float(receita_liquida_total) * 100) if receita_liquida_total > 0 else 0, 2),
        'margem_liquida': round((float(lucro_liquido_total) / float(receita_liquida_total) * 100) if receita_liquida_total > 0 else 0, 2)
    }
    
    return DREPorCanalResponse(
        periodo=periodo,
        mes=mes,
        ano=ano,
        linhas=linhas,
        totais=totais,
        canais_encontrados=list(dados_canais.keys())
    )
