"""
Relatórios Analíticos de Comissões - VERSÃO SIMPLIFICADA
Usa SQL direto via db.execute(text()) com SQLAlchemy
"""

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from typing import Optional
from datetime import date, datetime
import csv
import io

from sqlalchemy import text
from ..db import SessionLocal

router = APIRouter(prefix="/relatorios-comissoes", tags=["Relatórios de Comissões"])


# ===== RELATÓRIO 1: MARGEM POR PRODUTO =====
@router.get("/margem-produto")
def relatorio_margem_produto(
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    produto_id: Optional[int] = None,
    categoria_id: Optional[int] = None
):
    """Margem líquida por produto: Venda - Custo - Comissão"""
    
    db = SessionLocal()
    try:
        query = '''
            SELECT 
                p.id as produto_id,
                p.nome as produto_nome,
                COALESCE(c.nome, 'Sem categoria') as categoria_nome,
                COUNT(ci.id) as quantidade_vendas,
                SUM(ci.valor_base_calculo) as total_venda,
                SUM(ci.valor_custo) as total_custo,
                SUM(ci.valor_comissao_gerada) as total_comissao
            FROM comissoes_itens ci
            JOIN produtos p ON ci.produto_id = p.id
            LEFT JOIN categorias c ON p.categoria_id = c.id
            WHERE 1=1
        '''
        
        params_dict = {}
        
        if data_inicio:
            query += ' AND ci.data_venda >= :data_inicio'
            params_dict['data_inicio'] = data_inicio.isoformat()
        
        if data_fim:
            query += ' AND ci.data_venda <= :data_fim'
            params_dict['data_fim'] = data_fim.isoformat()
        
        if produto_id:
            query += ' AND ci.produto_id = :produto_id'
            params_dict['produto_id'] = produto_id
        
        if categoria_id:
            query += ' AND p.categoria_id = :categoria_id'
            params_dict['categoria_id'] = categoria_id
        
        query += ' GROUP BY p.id, p.nome, c.nome ORDER BY total_venda DESC'
        
        result = db.execute(text(query), params_dict)
        resultados = result.fetchall()
        
        relatorio = []
        for row in resultados:
            venda = float(row[4] or 0)  # total_venda
            custo = float(row[5] or 0)  # total_custo
            comissao = float(row[6] or 0)  # total_comissao
            
            margem_bruta = venda - custo
            margem_liquida = venda - custo - comissao
            
            percentual_comissao = (comissao / venda * 100) if venda > 0 else 0
            percentual_margem = (margem_liquida / venda * 100) if venda > 0 else 0
            
            relatorio.append({
                'produto_id': row[0],
                'produto_nome': row[1],
                'categoria_nome': row[2],
                'quantidade_vendas': row[3],
                'valor_venda': venda,
                'valor_custo': custo,
                'valor_comissao': comissao,
                'margem_bruta': margem_bruta,
                'margem_liquida': margem_liquida,
                'percentual_comissao': round(percentual_comissao, 2),
                'percentual_margem': round(percentual_margem, 2),
                'alerta_margem_negativa': margem_liquida < 0
            })
    finally:
        db.close()
    
    return {
        'periodo': {
            'inicio': data_inicio.isoformat() if data_inicio else None,
            'fim': data_fim.isoformat() if data_fim else None
        },
        'total_produtos': len(relatorio),
        'produtos_com_alerta': sum(1 for p in relatorio if p['alerta_margem_negativa']),
        'dados': relatorio
    }


# ===== RELATÓRIO 2: PRODUTOS PREJUDICIAIS =====
@router.get("/produtos-prejudiciais")
def relatorio_produtos_prejudiciais(
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    limite: int = Query(default=20, ge=1, le=100)
):
    """Produtos onde a comissão compromete a margem"""
    
    dados_margem = relatorio_margem_produto(data_inicio, data_fim)
    produtos = dados_margem['dados']
    
    prejudiciais = []
    for produto in produtos:
        alertas = []
        nivel_gravidade = 0
        
        if produto['margem_liquida'] < 0:
            alertas.append('Margem líquida negativa')
            nivel_gravidade = 3
        
        elif produto['margem_bruta'] > 0:
            proporcao = (produto['valor_comissao'] / produto['margem_bruta']) * 100
            if proporcao > 50:
                alertas.append(f'Comissão consome {proporcao:.1f}% da margem bruta')
                nivel_gravidade = max(nivel_gravidade, 2)
        
        if produto['percentual_comissao'] > 20:
            alertas.append(f'Comissão de {produto["percentual_comissao"]:.1f}% sobre venda')
            nivel_gravidade = max(nivel_gravidade, 1)
        
        if 0 <= produto['percentual_margem'] < 5:
            alertas.append(f'Margem líquida de apenas {produto["percentual_margem"]:.1f}%')
            nivel_gravidade = max(nivel_gravidade, 1)
        
        if alertas:
            prejudiciais.append({
                **produto,
                'alertas': alertas,
                'nivel_gravidade': nivel_gravidade,
                'impacto_financeiro': abs(produto['margem_liquida']) if produto['margem_liquida'] < 0 else (produto['margem_bruta'] - produto['margem_liquida'])
            })
    
    prejudiciais.sort(key=lambda x: x['impacto_financeiro'], reverse=True)
    
    return {
        'periodo': dados_margem['periodo'],
        'total_produtos_analisados': len(produtos),
        'total_produtos_prejudiciais': len(prejudiciais),
        'produtos_criticos': sum(1 for p in prejudiciais if p['nivel_gravidade'] == 3),
        'dados': prejudiciais[:limite]
    }


# ===== RANKING 1: FUNCIONÁRIOS =====
@router.get("/ranking-funcionarios")
def ranking_funcionarios(
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    limite: int = Query(default=10, ge=1, le=50)
):
    """Ranking de comissões por funcionário"""
    
    db = SessionLocal()
    try:
        query = '''
            SELECT 
                f.id as funcionario_id,
                f.nome as funcionario_nome,
                SUM(ci.valor_comissao_gerada) as total_comissao,
                COUNT(ci.id) as quantidade_comissoes,
                AVG(ci.valor_comissao_gerada) as media_comissao
            FROM comissoes_itens ci
            JOIN clientes f ON ci.funcionario_id = f.id
            WHERE 1=1
        '''
        
        params_dict = {}
        
        if data_inicio:
            query += ' AND ci.data_venda >= :data_inicio'
            params_dict['data_inicio'] = data_inicio.isoformat()
        
        if data_fim:
            query += ' AND ci.data_venda <= :data_fim'
            params_dict['data_fim'] = data_fim.isoformat()
        
        query += ' GROUP BY f.id, f.nome ORDER BY total_comissao DESC LIMIT :limite'
        params_dict['limite'] = limite
        
        result = db.execute(text(query), params_dict)
        resultados = result.fetchall()
        
        ranking = [
            {
                'posicao': idx + 1,
                'funcionario_id': row[0],
                'funcionario_nome': row[1],
                'total_comissao': float(row[2] or 0),
                'quantidade_comissoes': row[3],
                'media_comissao': float(row[4] or 0)
            }
            for idx, row in enumerate(resultados)
        ]
    finally:
        db.close()
    
    return {
        'periodo': {
            'inicio': data_inicio.isoformat() if data_inicio else None,
            'fim': data_fim.isoformat() if data_fim else None
        },
        'ranking': ranking
    }


# ===== RANKING 2: PRODUTOS =====
@router.get("/ranking-produtos")
def ranking_produtos(
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    limite: int = Query(default=10, ge=1, le=50)
):
    """Ranking de produtos por volume de comissões"""
    
    db = SessionLocal()
    try:
        query = '''
            SELECT 
                p.id as produto_id,
                p.nome as produto_nome,
                COALESCE(c.nome, 'Sem categoria') as categoria_nome,
                SUM(ci.valor_comissao_gerada) as total_comissao,
                COUNT(ci.id) as quantidade_vendas,
                SUM(ci.valor_base_calculo) as total_venda
            FROM comissoes_itens ci
            JOIN produtos p ON ci.produto_id = p.id
            LEFT JOIN categorias c ON p.categoria_id = c.id
            WHERE 1=1
        '''
        
        params_dict = {}
        
        if data_inicio:
            query += ' AND ci.data_venda >= :data_inicio'
            params_dict['data_inicio'] = data_inicio.isoformat()
        
        if data_fim:
            query += ' AND ci.data_venda <= :data_fim'
            params_dict['data_fim'] = data_fim.isoformat()
        
        query += ' GROUP BY p.id, p.nome, c.nome ORDER BY total_comissao DESC LIMIT :limite'
        params_dict['limite'] = limite
        
        result = db.execute(text(query), params_dict)
        resultados = result.fetchall()
        
        ranking = [
            {
                'posicao': idx + 1,
                'produto_id': row[0],
                'produto_nome': row[1],
                'categoria_nome': row[2],
                'total_comissao': float(row[3] or 0),
                'quantidade_vendas': row[4],
                'total_venda': float(row[5] or 0)
            }
            for idx, row in enumerate(resultados)
        ]
    finally:
        db.close()
    
    return {
        'periodo': {
            'inicio': data_inicio.isoformat() if data_inicio else None,
            'fim': data_fim.isoformat() if data_fim else None
        },
        'ranking': ranking
    }


# ===== RANKING 3: CATEGORIAS =====
@router.get("/ranking-categorias")
def ranking_categorias(
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None
):
    """Ranking de categorias por volume de comissões"""
    
    db = SessionLocal()
    try:
        query = '''
            SELECT 
                c.id as categoria_id,
                c.nome as categoria_nome,
                SUM(ci.valor_comissao_gerada) as total_comissao,
                COUNT(ci.id) as quantidade_comissoes,
                SUM(ci.valor_base_calculo) as total_venda
            FROM comissoes_itens ci
            JOIN produtos p ON ci.produto_id = p.id
            JOIN categorias c ON p.categoria_id = c.id
            WHERE 1=1
        '''
        
        params_dict = {}
        
        if data_inicio:
            query += ' AND ci.data_venda >= :data_inicio'
            params_dict['data_inicio'] = data_inicio.isoformat()
        
        if data_fim:
            query += ' AND ci.data_venda <= :data_fim'
            params_dict['data_fim'] = data_fim.isoformat()
        
        query += ' GROUP BY c.id, c.nome ORDER BY total_comissao DESC'
        
        result = db.execute(text(query), params_dict)
        resultados = result.fetchall()
        
        total_geral = sum(float(row[2] or 0) for row in resultados)  # total_comissao
        
        ranking = [
            {
                'posicao': idx + 1,
                'categoria_id': row[0],
                'categoria_nome': row[1],
                'total_comissao': float(row[2] or 0),
                'quantidade_comissoes': row[3],
                'total_venda': float(row[4] or 0),
                'percentual_total': round((float(row[2] or 0) / total_geral * 100), 2) if total_geral > 0 else 0
            }
            for idx, row in enumerate(resultados)
        ]
    finally:
        db.close()
    
    return {
        'periodo': {
            'inicio': data_inicio.isoformat() if data_inicio else None,
            'fim': data_fim.isoformat() if data_fim else None
        },
        'total_geral_comissoes': total_geral,
        'ranking': ranking
    }


# ===== VISÃO DRE =====
@router.get("/visao-dre")
def visao_dre(
    ano: int = Query(default=2026),
    mes_inicio: Optional[int] = Query(default=1, ge=1, le=12),
    mes_fim: Optional[int] = Query(default=12, ge=1, le=12)
):
    """Visão DRE: Comissão como despesa operacional"""
    
    db = SessionLocal()
    try:
        query = '''
            SELECT 
                CAST(strftime('%m', ci.data_venda) AS INTEGER) as mes,
                SUM(ci.valor_base_calculo) as receita_bruta,
                SUM(ci.valor_custo) as custo_total,
                SUM(ci.valor_comissao_gerada) as despesa_comissao,
                COUNT(ci.id) as quantidade_operacoes
            FROM comissoes_itens ci
            WHERE CAST(strftime('%Y', ci.data_venda) AS INTEGER) = :ano
              AND CAST(strftime('%m', ci.data_venda) AS INTEGER) BETWEEN :mes_inicio AND :mes_fim
              AND ci.status IN ('pendente', 'paga')
            GROUP BY strftime('%m', ci.data_venda)
            ORDER BY mes
        '''
        
        result = db.execute(text(query), {'ano': ano, 'mes_inicio': mes_inicio, 'mes_fim': mes_fim})
        resultados = result.fetchall()
        
        meses_nomes = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                       'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
        
        dados_mensais = []
        total_ano = {'receita_bruta': 0, 'custo_total': 0, 'despesa_comissao': 0}
        
        for row in resultados:
            receita = float(row[1] or 0)  # receita_bruta
            custo = float(row[2] or 0)  # custo_total
            comissao = float(row[3] or 0)  # despesa_comissao
            
            margem_bruta = receita - custo
            margem_liquida = receita - custo - comissao
            
            dados_mensais.append({
                'mes': row[0],
                'mes_nome': meses_nomes[row[0]],
                'receita_bruta': receita,
                'custo_total': custo,
                'despesa_comissao': comissao,
                'margem_bruta': margem_bruta,
                'margem_liquida': margem_liquida,
                'percentual_comissao_sobre_receita': round((comissao / receita * 100), 2) if receita > 0 else 0,
                'percentual_margem_bruta': round((margem_bruta / receita * 100), 2) if receita > 0 else 0,
                'percentual_margem_liquida': round((margem_liquida / receita * 100), 2) if receita > 0 else 0,
                'quantidade_operacoes': row[4]
            })
            
            total_ano['receita_bruta'] += receita
            total_ano['custo_total'] += custo
            total_ano['despesa_comissao'] += comissao
        
        total_ano['margem_bruta'] = total_ano['receita_bruta'] - total_ano['custo_total']
        total_ano['margem_liquida'] = total_ano['receita_bruta'] - total_ano['custo_total'] - total_ano['despesa_comissao']
        total_ano['percentual_comissao'] = round(
            (total_ano['despesa_comissao'] / total_ano['receita_bruta'] * 100) if total_ano['receita_bruta'] > 0 else 0,
            2
        )
    finally:
        db.close()
    
    return {
        'ano': ano,
        'periodo': {'mes_inicio': mes_inicio, 'mes_fim': mes_fim},
        'dados_mensais': dados_mensais,
        'total_ano': total_ano
    }


# ===== EXPORTAÇÃO CSV =====
@router.get("/exportar-csv")
def exportar_csv(
    tipo: str = Query(..., pattern="^(margem-produto|produtos-prejudiciais|ranking-funcionarios|ranking-produtos)$"),
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None
):
    """Exporta relatórios em formato CSV"""
    
    if tipo == "margem-produto":
        dados = relatorio_margem_produto(data_inicio, data_fim)
        linhas = dados['dados']
        campos = ['produto_nome', 'categoria_nome', 'quantidade_vendas', 'valor_venda', 
                 'valor_custo', 'valor_comissao', 'margem_bruta', 'margem_liquida',
                 'percentual_comissao', 'percentual_margem', 'alerta_margem_negativa']
    
    elif tipo == "produtos-prejudiciais":
        dados = relatorio_produtos_prejudiciais(data_inicio, data_fim)
        linhas = dados['dados']
        campos = ['produto_nome', 'nivel_gravidade', 'margem_liquida', 'percentual_margem',
                 'valor_comissao', 'percentual_comissao', 'impacto_financeiro']
    
    elif tipo == "ranking-funcionarios":
        dados = ranking_funcionarios(data_inicio, data_fim)
        linhas = dados['ranking']
        campos = ['posicao', 'funcionario_nome', 'total_comissao', 'quantidade_comissoes', 'media_comissao']
    
    elif tipo == "ranking-produtos":
        dados = ranking_produtos(data_inicio, data_fim)
        linhas = dados['ranking']
        campos = ['posicao', 'produto_nome', 'categoria_nome', 'total_comissao', 'quantidade_vendas', 'total_venda']
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=campos, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(linhas)
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=relatorio_{tipo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        }
    )
