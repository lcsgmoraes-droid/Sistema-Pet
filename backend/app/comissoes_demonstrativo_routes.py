"""
DEMONSTRATIVO DE COMISSÕES - ROTAS (SOMENTE LEITURA)

⚠️ PRINCÍPIO FUNDAMENTAL:
Estas rotas servem EXCLUSIVAMENTE para CONSULTA de snapshots imutáveis.
NÃO recalculam, NÃO atualizam, NÃO modificam dados.
Apenas LEEM a tabela comissoes_itens.

Criado em: 22/01/2026
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, Dict, List, Any
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel
import logging
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.utils.tenant_safe_sql import execute_tenant_safe

from app.utils.logger import StructuredLogger
from app.db import get_session, SessionLocal
from app.auth import get_current_user
from app.auth.dependencies import get_current_user_and_tenant
from app.models import User, Cliente
from app.financeiro_models import (
    ContaPagar, LancamentoManual, CategoriaFinanceira, MovimentacaoFinanceira, ContaBancaria
)

# Logger padrão para logs simples
logger = logging.getLogger(__name__)

# Logger estruturado para eventos
struct_logger = StructuredLogger(__name__)

# Router com prefixo /comissoes
router = APIRouter(prefix="/comissoes", tags=["Comissões - Demonstrativo"])


# ==================== SCHEMAS ====================

class FecharComissoesRequest(BaseModel):
    """Schema para fechamento de comissões"""
    comissoes_ids: List[int]
    data_pagamento: date
    observacao: Optional[str] = None


# ==================== HELPERS ====================

def decimal_to_float(value: Any) -> float:
    """Converte Decimal para float de forma segura"""
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


# ==================== ENDPOINTS DE LEITURA ====================

@router.get("", summary="Listar comissões (histórico)")
async def listar_comissoes(
    funcionario_id: Optional[int] = Query(None, description="Filtrar por funcionário"),
    data_inicio: Optional[date] = Query(None, description="Data inicial (YYYY-MM-DD)"),
    data_fim: Optional[date] = Query(None, description="Data final (YYYY-MM-DD)"),
    status: Optional[str] = Query(None, description="Status: pendente, pago ou estornado"),
    venda_id: Optional[int] = Query(None, description="Filtrar por venda específica"),
    user_and_tenant = Depends(get_current_user_and_tenant)
) -> Dict[str, Any]:
    """
    Lista comissões com filtros opcionais.
    
    🔒 SNAPSHOT IMUTÁVEL:
    - Retorna dados direto de comissoes_itens
    - NÃO recalcula valores
    - NÃO consulta outras tabelas
    
    Retorna:
    - lista: Array de comissões
    - total: Total de registros
    - filtros_aplicados: Resumo dos filtros
    """
    
    # Log estruturado
    struct_logger.info(
        "COMMISSION_LIST_REQUEST",
        "Consulta de histórico de comissões",
        funcionario_id=funcionario_id,
        data_inicio=str(data_inicio) if data_inicio else None,
        data_fim=str(data_fim) if data_fim else None,
        status=status,
        venda_id=venda_id
    )
    
    try:
        from app.tenancy.context import set_tenant_context
        from app.db import SessionLocal
        
        # Configurar tenant context
        current_user, tenant_id = user_and_tenant
        set_tenant_context(tenant_id)
        
        db = SessionLocal()
        # Construir query dinâmica
        query = """
            SELECT 
                ci.id,
                ci.venda_id,
                v.numero_venda,
                ci.data_venda,
                ci.funcionario_id,
                ci.produto_id,
                ci.parcela_numero,
                ci.valor_base_calculo,
                ci.percentual_comissao,
                ci.valor_comissao_gerada,
                ci.status,
                ci.data_estorno,
                ci.motivo_estorno,
                ci.tipo_calculo,
                ci.quantidade
            FROM comissoes_itens ci
            INNER JOIN vendas v ON v.id = ci.venda_id AND v.tenant_id = ci.tenant_id
            WHERE ci.{tenant_filter}
        """
        
        params = {}
        
        # Aplicar filtros
        if funcionario_id is not None:
            query += " AND funcionario_id = :funcionario_id"
            params['funcionario_id'] = funcionario_id
        
        if data_inicio:
            query += " AND data_venda >= :data_inicio"
            params['data_inicio'] = data_inicio
        
        if data_fim:
            query += " AND data_venda <= :data_fim"
            params['data_fim'] = data_fim
        
        if status:
            query += " AND status = :status"
            params['status'] = status.lower()
        
        if venda_id is not None:
            query += " AND venda_id = :venda_id"
            params['venda_id'] = venda_id
        
        # Ordenar por mais recente
        query += " ORDER BY data_venda DESC, id DESC"
        
        result = execute_tenant_safe(db, query, params)
        rows = result.fetchall()
        
        # Converter para lista de dicts
        comissoes = []
        for row in rows:
            comissoes.append({
                'id': row[0],
                'venda_id': row[1],
                'numero_venda': row[2],
                'data_venda': str(row[3]) if row[3] else None,
                'funcionario_id': row[4],
                'produto_id': row[5],
                'parcela_numero': row[6],
                'valor_base_calculo': decimal_to_float(row[7]),
                'percentual_comissao': decimal_to_float(row[8]),
                'valor_comissao_gerada': decimal_to_float(row[9]),
                'status': row[10],
                'data_estorno': str(row[11]) if row[11] else None,
                'motivo_estorno': row[12],
                'tipo_calculo': row[13],
                'quantidade': decimal_to_float(row[14])
            })
        
        logger.info(f"Retornando {len(comissoes)} comissões")
        
        return {
            'success': True,
            'lista': comissoes,
            'total': len(comissoes),
            'filtros_aplicados': {
                'funcionario_id': funcionario_id,
                'data_inicio': str(data_inicio) if data_inicio else None,
                'data_fim': str(data_fim) if data_fim else None,
                'status': status,
                'venda_id': venda_id
            }
        }
        
    except Exception as e:
        logger.error(f"Erro ao listar comissões: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao consultar comissões: {str(e)}")


@router.get("/resumo", summary="Resumo financeiro de comissões")
async def resumo_comissoes(
    funcionario_id: int = Query(..., description="ID do funcionário (obrigatório)"),
    data_inicio: Optional[date] = Query(None, description="Data inicial (YYYY-MM-DD)"),
    data_fim: Optional[date] = Query(None, description="Data final (YYYY-MM-DD)"),
    user_and_tenant = Depends(get_current_user_and_tenant)
) -> Dict[str, Any]:
    """
    Retorna resumo financeiro das comissões (totalizadores para cards).
    
    🔒 SNAPSHOT IMUTÁVEL:
    - Usa SUM() direto em comissoes_itens
    - NÃO recalcula valores
    
    Retorna:
    - total_gerado: Soma de todas comissões (exceto estornadas)
    - total_pago: Soma de comissões com status=pago
    - total_pendente: Soma de comissões com status=pendente
    - total_estornado: Soma de comissões estornadas
    - saldo_a_pagar: total_pendente
    """
    
    struct_logger.info(
        "COMMISSION_SUMMARY_REQUEST",
        "Consulta de resumo financeiro de comissões",
        funcionario_id=funcionario_id,
        data_inicio=str(data_inicio) if data_inicio else None,
        data_fim=str(data_fim) if data_fim else None
    )
    
    try:
        from app.tenancy.context import set_tenant_context
        from app.db import SessionLocal
        
        # Configurar tenant context
        current_user, tenant_id = user_and_tenant
        set_tenant_context(tenant_id)
        
        db = SessionLocal()
        
        # Query base para filtros de data
        where_clause = "WHERE funcionario_id = :funcionario_id AND {tenant_filter}"
        params = {'funcionario_id': funcionario_id}
        
        if data_inicio:
            where_clause += " AND data_venda >= :data_inicio"
            params['data_inicio'] = data_inicio
        
        if data_fim:
            where_clause += " AND data_venda <= :data_fim"
            params['data_fim'] = data_fim
        
        # Total gerado (pendente + pago, excluindo estornado)
        result = execute_tenant_safe(db, f"""
            SELECT COALESCE(SUM(valor_comissao_gerada), 0) as total
            FROM comissoes_itens
            {where_clause} AND status != 'estornado'
        """, params)
        total_gerado = decimal_to_float(result.scalar())
        
        # Total pago
        result = execute_tenant_safe(db, f"""
            SELECT COALESCE(SUM(valor_comissao_gerada), 0) as total
            FROM comissoes_itens
            {where_clause} AND status = 'pago'
        """, params)
        total_pago = decimal_to_float(result.scalar())
        
        # Total pendente
        result = execute_tenant_safe(db, f"""
            SELECT COALESCE(SUM(valor_comissao_gerada), 0) as total
            FROM comissoes_itens
            {where_clause} AND status = 'pendente'
        """, params)
        total_pendente = decimal_to_float(result.scalar())
        
        # Total estornado
        result = execute_tenant_safe(db, f"""
            SELECT COALESCE(SUM(valor_comissao_gerada), 0) as total
            FROM comissoes_itens
            {where_clause} AND status = 'estornado'
        """, params)
        total_estornado = decimal_to_float(result.scalar())
        
        # Quantidade de comissões
        result = execute_tenant_safe(db, f"""
            SELECT COUNT(*) as total
            FROM comissoes_itens
            {where_clause}
        """, params)
        quantidade_comissoes = result.scalar()
        
        # Saldo a pagar = total pendente
        saldo_a_pagar = total_pendente
        
        logger.info(f"Resumo: funcionario={funcionario_id}, gerado={total_gerado}, pago={total_pago}, pendente={total_pendente}")
        
        return {
            'success': True,
            'funcionario_id': funcionario_id,
            'resumo': {
                'total_gerado': total_gerado,
                'total_pago': total_pago,
                'total_pendente': total_pendente,
                'total_estornado': total_estornado,
                'saldo_a_pagar': saldo_a_pagar,
                'quantidade_comissoes': quantidade_comissoes
            },
            'periodo': {
                'data_inicio': str(data_inicio) if data_inicio else None,
                'data_fim': str(data_fim) if data_fim else None
            }
        }
        
    except Exception as e:
        logger.error(f"Erro ao calcular resumo: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao calcular resumo: {str(e)}")


# ==================== ENDPOINT: COMISSÕES EM ABERTO ====================

@router.get("/abertas", summary="Listar funcionários com comissões pendentes")
def listar_comissoes_abertas(
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    SPRINT 6 - PASSO 1/5: COMISSÕES EM ABERTO
    
    Lista funcionários que possuem comissões pendentes com resumo financeiro.
    
    Regras:
    - Usa EXCLUSIVAMENTE a tabela comissoes_itens
    - Considera apenas status='pendente'
    - NÃO recalcula valores
    - Agrupa por funcionario_id
    
    Retorna:
    - funcionario_id
    - nome_funcionario
    - total_pendente (soma dos valores)
    - quantidade_comissoes
    - data_ultima_venda
    
    Ordenação: total_pendente DESC
    """
    try:
        # Extrair tenant_id e configurar contexto
        from app.tenancy.context import set_tenant_context
        current_user, tenant_id = user_and_tenant
        set_tenant_context(tenant_id)
        
        struct_logger.info(
            "COMMISSION_OPEN_LIST",
            "Consultando funcionários com comissões em aberto"
        )
        
        db = SessionLocal()
        
        try:
            # Query agrupada por funcionário (APENAS LEITURA)
            # CORRIGIDO: funcionario_id refere-se à tabela clientes, não users
            query = """
                SELECT 
                    ci.funcionario_id,
                    c.nome as nome_funcionario,
                    SUM(ci.valor_comissao_gerada) as total_pendente,
                    COUNT(ci.id) as quantidade_comissoes,
                    MAX(ci.data_venda) as data_ultima_venda
                FROM comissoes_itens ci
                LEFT JOIN clientes c ON ci.funcionario_id = c.id AND c.{tenant_filter}
                WHERE ci.{tenant_filter} AND ci.status = 'pendente'
                GROUP BY ci.funcionario_id, c.nome
                ORDER BY total_pendente DESC
            """
            
            result = execute_tenant_safe(db, query, {})
            rows = result.fetchall()
            
            # Converter para lista de dicionários
            funcionarios = []
            for row in rows:
                funcionarios.append({
                    'funcionario_id': row[0],
                    'nome_funcionario': row[1] or 'Funcionário não encontrado',
                    'total_pendente': float(row[2]) if row[2] else 0.0,
                    'quantidade_comissoes': row[3],
                    'data_ultima_venda': row[4]
            })
            
            struct_logger.info(
                "COMMISSION_OPEN_LIST_SUCCESS",
                f"{len(funcionarios)} funcionário(s) com comissões pendentes",
                extra={'total_funcionarios': len(funcionarios)}
            )
            
            return {
                'success': True,
                'total_funcionarios': len(funcionarios),
                'funcionarios': funcionarios
            }
        finally:
            db.close()
        
    except Exception as e:
        logger.error(f"Erro ao listar comissões abertas: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao listar comissões abertas: {str(e)}")


# ==================== ENDPOINT: CONFERÊNCIA POR FUNCIONÁRIO ====================

@router.get("/fechamento/{funcionario_id}", summary="Comissões pendentes de um funcionário para conferência")
def listar_comissoes_funcionario_para_fechamento(
    funcionario_id: int,
    data_inicio: Optional[date] = Query(None, description="Data inicial do filtro"),
    data_fim: Optional[date] = Query(None, description="Data final do filtro"),
    _user_and_tenant=Depends(get_current_user_and_tenant),
):
    """
    SPRINT 6 - PASSO 2/5: CONFERÊNCIA POR FUNCIONÁRIO
    
    Lista todas as comissões pendentes de um funcionário específico.
    
    Regras:
    - Usa EXCLUSIVAMENTE a tabela comissoes_itens
    - Considera apenas status='pendente'
    - NÃO recalcula valores
    - Permite filtro por período
    
    Retorna:
    - Dados completos de cada comissão
    - Informações de venda, produto, cliente
    - Valores de base de cálculo e comissão
    
    Ordenação: data_venda ASC
    """
    try:
        struct_logger.info(
            "COMMISSION_EMPLOYEE_LIST",
            f"Consultando comissões pendentes do funcionário {funcionario_id}",
            extra={'funcionario_id': funcionario_id}
        )
        
        db = SessionLocal()
        
        try:
            # Buscar nome do funcionário (CORRIGIDO: busca na tabela clientes)
            result = execute_tenant_safe(db, "SELECT nome FROM clientes WHERE id = :id AND {tenant_filter}", {"id": funcionario_id})
            funcionario_row = result.fetchone()
        
            if not funcionario_row:
                raise HTTPException(status_code=404, detail=f"Funcionário {funcionario_id} não encontrado")
            
            nome_funcionario = funcionario_row[0]
        
            # Query para listar comissões (APENAS LEITURA)
            query = """
                SELECT 
                    ci.id,
                    ci.venda_id,
                    ci.data_venda,
                    ci.produto_id,
                    ci.quantidade,
                    ci.valor_base_calculo,
                    ci.percentual_comissao,
                    ci.valor_comissao_gerada,
                    ci.tipo_calculo,
                    ci.parcela_numero,
                    p.nome as nome_produto,
                    v.cliente_id
                FROM comissoes_itens ci
                LEFT JOIN produtos p ON ci.produto_id = p.id AND {tenant_filter_p}
                LEFT JOIN vendas v ON ci.venda_id = v.id AND {tenant_filter_v}
                WHERE {tenant_filter_ci} AND ci.funcionario_id = :funcionario_id AND ci.status = 'pendente'
            """
            
            params = {"funcionario_id": funcionario_id}
            
            # Aplicar filtros de data
            if data_inicio:
                query += " AND DATE(ci.data_venda) >= :data_inicio"
                params["data_inicio"] = str(data_inicio)
            
            if data_fim:
                query += " AND DATE(ci.data_venda) <= :data_fim"
                params["data_fim"] = str(data_fim)
            
            query += " ORDER BY ci.data_venda ASC, ci.id ASC"
            
            result = execute_tenant_safe(db, query, params)
            rows = result.fetchall()
        
            # Buscar nomes dos clientes (se houver)
            cliente_ids = list(set([row[11] for row in rows if row[11]]))
            clientes_map = {}
            
            if cliente_ids:
                from sqlalchemy import bindparam
                stmt = text("SELECT id, nome FROM clientes WHERE id IN :ids AND {tenant_filter}").bindparams(bindparam("ids", expanding=True))
                result = execute_tenant_safe(db, stmt, {"ids": tuple(cliente_ids)})
                for cliente in result.fetchall():
                    clientes_map[cliente[0]] = cliente[1]
        
            # Converter para lista de dicionários
            comissoes = []
            total_geral = 0.0
            
            for row in rows:
                cliente_nome = clientes_map.get(row[11], 'Cliente não identificado') if row[11] else 'Venda sem cliente'
                
                comissao = {
                    'id': row[0],
                    'venda_id': row[1],
                    'data_venda': row[2],
                    'produto_id': row[3],
                    'nome_produto': row[10] or f'Produto #{row[3]}',
                    'cliente_nome': cliente_nome,
                    'quantidade': float(row[4]) if row[4] else 0.0,
                    'valor_base_calculo': float(row[5]) if row[5] else 0.0,
                    'percentual_comissao': float(row[6]) if row[6] else 0.0,
                    'valor_comissao_gerada': float(row[7]) if row[7] else 0.0,
                    'tipo_calculo': row[8],
                    'parcela_numero': row[9]
                }
                
                comissoes.append(comissao)
                total_geral += comissao['valor_comissao_gerada']
        
            struct_logger.info(
                "COMMISSION_EMPLOYEE_LIST_SUCCESS",
                f"{len(comissoes)} comissão(ões) encontrada(s) para funcionário {funcionario_id}",
                extra={
                    'funcionario_id': funcionario_id,
                    'total_comissoes': len(comissoes),
                    'valor_total': total_geral
                }
            )
            
            return {
                'success': True,
                'funcionario': {
                    'id': funcionario_id,
                    'nome': nome_funcionario
                },
                'filtros': {
                    'data_inicio': str(data_inicio) if data_inicio else None,
                    'data_fim': str(data_fim) if data_fim else None
                },
                'total_comissoes': len(comissoes),
                'valor_total': total_geral,
                'comissoes': comissoes
            }
        finally:
            db.close()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao listar comissões do funcionário {funcionario_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao listar comissões: {str(e)}")


@router.get("/comissao/{comissao_id}", summary="Detalhe completo de uma comissão (transparência total)")
async def detalhe_comissao(
    comissao_id: int,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
) -> Dict[str, Any]:
    """
    Retorna TODOS os campos financeiros do snapshot de uma comissão específica.
    
    🔒 SNAPSHOT IMUTÁVEL:
    - Mostra exatamente como a comissão foi calculada
    - Valores refletem o momento da venda
    - NÃO recalcula nada
    
    Use este endpoint para responder:
    "Como essa comissão foi calculada?"
    
    Retorna todos os campos:
    - Valores financeiros (venda, custo, base de cálculo)
    - Divisões proporcionais (desconto, taxas, impostos)
    - Cálculo da comissão (tipo, percentual, valor gerado)
    - Status e controle
    """
    
    # Extrair tenant_id e configurar contexto
    from app.tenancy.context import set_tenant_context
    current_user, tenant_id = user_and_tenant
    set_tenant_context(tenant_id)
    
    struct_logger.info(
        "COMMISSION_DETAIL_REQUEST",
        "Consulta de detalhes de comissão específica",
        comissao_id=comissao_id
    )
    
    try:
        # Buscar TODOS os campos do snapshot usando SQLAlchemy
        result = execute_tenant_safe(db, """
            SELECT 
                ci.id,
                ci.venda_id,
                v.numero_venda,
                v.total as total_venda,
                ci.data_venda,
                ci.funcionario_id,
                ci.produto_id,
                ci.quantidade,
                ci.parcela_numero,
                -- Valores financeiros
                ci.valor_venda,
                ci.valor_custo,
                ci.valor_base_original,
                ci.valor_base_comissionada,
                -- Cálculo da comissão
                ci.tipo_calculo,
                ci.valor_base_calculo,
                ci.percentual_comissao,
                ci.percentual_aplicado,
                ci.valor_comissao,
                ci.valor_comissao_gerada,
                -- Controle de pagamento
                ci.percentual_pago,
                ci.valor_pago_referencia,
                ci.valor_pago,
                ci.saldo_restante,
                ci.data_pagamento,
                ci.forma_pagamento,
                -- Status
                ci.status,
                ci.data_estorno,
                ci.motivo_estorno,
                ci.observacao_pagamento,
                -- Informações da forma de pagamento (para mostrar "Taxa Cartão 3x", etc)
                vp.forma_pagamento as forma_pagamento_venda,
                vp.numero_parcelas,
                fp.taxa_percentual,
                fp.taxas_por_parcela,
                -- Deduções detalhadas (snapshot)
                ci.taxa_cartao_item,
                ci.impostos_item,
                ci.taxa_entregador_item,
                ci.custo_operacional_item,
                ci.receita_taxa_entrega_item,
                ci.percentual_impostos
            FROM comissoes_itens ci
            INNER JOIN vendas v ON v.id = ci.venda_id
            LEFT JOIN venda_pagamentos vp ON vp.venda_id = v.id
            LEFT JOIN formas_pagamento fp ON fp.nome = vp.forma_pagamento
            WHERE ci.{tenant_filter}
            AND ci.id = :comissao_id
            LIMIT 1
        """, {"comissao_id": comissao_id})
        
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail=f"Comissão {comissao_id} não encontrada")
        
        # Converter para dict com todos os campos (usar _mapping para acesso por nome)
        r = row._mapping
        
        # Calcular as deduções para mostrar a origem da base de cálculo
        valor_venda = decimal_to_float(r['valor_venda']) or 0.0
        valor_base_calculo = decimal_to_float(r['valor_base_calculo']) or 0.0
        total_deducoes = valor_venda - valor_base_calculo
        
        detalhe = {
            'id': r['id'],
            'venda_id': r['venda_id'],
            'numero_venda': r['numero_venda'],
            'total_venda': decimal_to_float(r['total_venda']),  # ✅ Valor total da venda (produtos)
            'data_venda': str(r['data_venda']) if r['data_venda'] else None,
            'funcionario_id': r['funcionario_id'],
            'produto_id': r['produto_id'],
            'quantidade': decimal_to_float(r['quantidade']),
            'parcela_numero': r['parcela_numero'],
            
            # Valores financeiros (snapshot do momento da venda)
            'valores_financeiros': {
                'valor_venda': valor_venda,
                'valor_custo': decimal_to_float(r['valor_custo']),
                'valor_base_original': decimal_to_float(r['valor_base_original']),
                'valor_base_comissionada': decimal_to_float(r['valor_base_comissionada'])
            },
            
            # EXPLICAÇÃO DO CÁLCULO DA BASE
            'origem_base_calculo': {
                'valor_inicial': valor_venda,
                'deducoes_aplicadas': total_deducoes,
                'valor_final': valor_base_calculo,
                'explicacao': f'Base de cálculo = Valor de Venda (R$ {valor_venda:.2f}) - Deduções (R$ {total_deducoes:.2f}) = R$ {valor_base_calculo:.2f}'
            },
            
            # DEDUÇÕES DETALHADAS (breakdown completo do cálculo)
            'deducoes': {
                'taxa_cartao': decimal_to_float(r.get('taxa_cartao_item')) if r.get('taxa_cartao_item') else 0.0,
                'imposto': decimal_to_float(r.get('impostos_item')) if r.get('impostos_item') else 0.0,
                'taxa_entregador': decimal_to_float(r.get('taxa_entregador_item')) if r.get('taxa_entregador_item') else 0.0,
                'custo_operacional': decimal_to_float(r.get('custo_operacional_item')) if r.get('custo_operacional_item') else 0.0,
                'receita_taxa_entrega': decimal_to_float(r.get('receita_taxa_entrega_item')) if r.get('receita_taxa_entrega_item') else 0.0,
                'percentual_impostos': decimal_to_float(r.get('percentual_impostos')) if r.get('percentual_impostos') else 0.0,
                'forma_pagamento': r.get('forma_pagamento'),  # ✅ Usar forma_pagamento da comissao
                'numero_parcelas': r.get('numero_parcelas'),
                'taxa_percentual': decimal_to_float(r.get('taxa_percentual')) if r.get('taxa_percentual') else None,
                'taxas_por_parcela': r.get('taxas_por_parcela')
            },
            
            # Cálculo da comissão
            'calculo': {
                'tipo_calculo': r['tipo_calculo'],
                'valor_base_calculo': valor_base_calculo,
                'percentual_comissao': decimal_to_float(r['percentual_comissao']),
                'percentual_aplicado': decimal_to_float(r['percentual_aplicado']),
                'valor_comissao': decimal_to_float(r['valor_comissao']),
                'valor_comissao_gerada': decimal_to_float(r['valor_comissao_gerada'])
            },
            
            # Controle de pagamento (vendas parciais)
            'pagamento': {
                'percentual_pago': decimal_to_float(r['percentual_pago']),
                'valor_pago_referencia': decimal_to_float(r['valor_pago_referencia']),
                'valor_pago': decimal_to_float(r['valor_pago']),
                'saldo_restante': decimal_to_float(r['saldo_restante']),
                'data_pagamento': str(r['data_pagamento']) if r['data_pagamento'] else None,
                'forma_pagamento': r['forma_pagamento']
            },
            
            # Status e controle
            'status': {
                'status': r['status'],
                'data_estorno': str(r['data_estorno']) if r['data_estorno'] else None,
                'motivo_estorno': r['motivo_estorno'],
                'observacao_pagamento': r['observacao_pagamento']
            }
        }
        
        logger.info(f"Detalhes da comissão {comissao_id} retornados com sucesso")
        
        return {
            'success': True,
            'comissao': detalhe,
            'snapshot_imutavel': True,
            'mensagem': 'Estes valores refletem o momento exato da venda e NÃO podem ser alterados'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar detalhes da comissão {comissao_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao consultar comissão: {str(e)}")


@router.get("/funcionarios", summary="Listar funcionários com comissões")
async def listar_funcionarios_comissoes(
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
) -> Dict[str, Any]:
    """
    Retorna lista de funcionários que possuem comissões registradas.
    
    🔒 SNAPSHOT IMUTÁVEL:
    - Busca APENAS funcionários que aparecem em comissoes_itens
    - NÃO recalcula valores
    - NÃO faz joins desnecessários
    
    Retorna:
    - lista: Array com id e nome dos funcionários
    - total: Quantidade de funcionários
    
    Critério: Funcionário possui registros em comissoes_itens OU
              possui configuração em comissoes_configuracao
    """
    
    struct_logger.info(
        "COMMISSION_EMPLOYEES_LIST",
        "Consulta de funcionários com comissões"
    )
    
    try:
        # Buscar funcionários que aparecem em comissoes_itens
        # Assumindo que funcionarios estão na tabela 'clientes' (conforme padrão do sistema)
        result = execute_tenant_safe(db, """
            SELECT DISTINCT 
                c.id,
                c.nome
            FROM clientes c
            WHERE c.id IN (
                SELECT DISTINCT funcionario_id 
                FROM comissoes_itens
                WHERE funcionario_id IS NOT NULL
                AND {tenant_filter}
            )
            AND {tenant_filter}
            ORDER BY c.nome ASC
        """, {})
        rows = result.fetchall()
        
        # Converter para lista de dicts
        funcionarios = []
        for row in rows:
            funcionarios.append({
                'id': row[0],
                'nome': row[1]
            })
        
        logger.info(f"Retornando {len(funcionarios)} funcionários com comissões")
        
        return {
            'success': True,
            'lista': funcionarios,
            'total': len(funcionarios)
        }
        
    except Exception as e:
        logger.error(f"Erro ao listar funcionários com comissões: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao consultar funcionários: {str(e)}")


# ==================== ENDPOINTS DE ESCRITA ====================

@router.post("/fechar", summary="Fechar comissões (alterar status para pago)")
async def fechar_comissoes(
    request: FecharComissoesRequest,
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant)
) -> Dict[str, Any]:
    """
    Fecha comissões alterando status para 'pago'.
    
    ⚠️ IMPORTANTE:
    - NÃO recalcula valores (snapshot imutável)
    - Altera APENAS: status, data_pagamento, observacao_pagamento
    - Só processa comissões com status='pendente'
    - Ignora silenciosamente comissões já pagas/estornadas
    
    Regras:
    - Comissões já pagas: ignoradas
    - Comissões estornadas: ignoradas
    - Apenas status='pendente' são fechadas
    - Operação em transação única
    
    Returns:
    - total_processadas: Quantidade fechada com sucesso
    - total_ignoradas: Quantidade já paga/estornada
    - comissoes_fechadas: IDs das comissões processadas
    - comissoes_ignoradas: IDs ignorados
    """
    
    struct_logger.info(
        "COMMISSION_CLOSE_START",
        f"Iniciando fechamento de {len(request.comissoes_ids)} comissões",
        extra={
            'ids_count': len(request.comissoes_ids),
            'data_pagamento': str(request.data_pagamento),
            'has_observacao': bool(request.observacao)
        }
    )
    
    try:
        db = SessionLocal()
        
        try:
            # 1. Verificar quais comissões podem ser fechadas (status=pendente)
            from sqlalchemy import bindparam
            stmt = text("""
                SELECT id, status, valor_comissao_gerada
                FROM comissoes_itens
                WHERE id IN :ids
                AND {tenant_filter}
            """).bindparams(bindparam("ids", expanding=True))
            
            result = execute_tenant_safe(db, stmt, {"ids": tuple(request.comissoes_ids)})
            rows = result.fetchall()
        
            # Separar comissões pendentes das ignoradas
            ids_pendentes = []
            ids_ignorados = []
            valor_total_fechamento = 0.0
            
            for row in rows:
                if row[1] == 'pendente':
                    ids_pendentes.append(row[0])
                    valor_total_fechamento += decimal_to_float(row[2])
                else:
                    ids_ignorados.append(row[0])
            
            logger.info(f"Pendentes: {len(ids_pendentes)}, Ignorados: {len(ids_ignorados)}")
            
            # 2. Atualizar comissões pendentes
            comissoes_fechadas = []
            
            if ids_pendentes:
                data_agora = datetime.now().isoformat()
                
                for comissao_id in ids_pendentes:
                    execute_tenant_safe(db, """
                        UPDATE comissoes_itens
                        SET 
                            status = 'paga',
                            data_pagamento = :data_pagamento,
                            observacao_pagamento = :observacao,
                            data_atualizacao = :data_atualizacao
                        WHERE id = :comissao_id
                        AND {tenant_filter}
                    """, {
                        "data_pagamento": str(request.data_pagamento),
                        "observacao": request.observacao,
                        "data_atualizacao": data_agora,
                        "comissao_id": comissao_id
                    })
                    
                    comissoes_fechadas.append(comissao_id)
                    
                    struct_logger.info(
                        "COMMISSION_CLOSED",
                        f"Comissão {comissao_id} fechada",
                        extra={
                            'comissao_id': comissao_id,
                            'data_pagamento': str(request.data_pagamento)
                        }
                    )
                
                db.commit()
                logger.info(f"✅ {len(comissoes_fechadas)} comissões fechadas com sucesso")
                
                # ========================================
                # GERAR CONTA A PAGAR E LANÇAMENTO PREVISTO
                # ========================================
                
                # Buscar informações do funcionário (primeira comissão)
                result = execute_tenant_safe(db,
                    "SELECT funcionario_id FROM comissoes_itens WHERE id = :id AND {tenant_filter}",
                    {"id": ids_pendentes[0]}
                )
                funcionario_row = result.fetchone()
                funcionario_id = funcionario_row[0] if funcionario_row else None
                
                # Buscar nome do funcionário
                funcionario_nome = "Funcionário"
                if funcionario_id:
                    funcionario = db.query(Cliente).filter(Cliente.id == funcionario_id).first()
                    if funcionario:
                        funcionario_nome = funcionario.nome
                
                # Buscar categoria de comissão
                categoria_comissao = db.query(CategoriaFinanceira).filter(
                    CategoriaFinanceira.nome.ilike('%comis%')
                ).first()
                
                if not categoria_comissao:
                    # Criar categoria se não existir
                    current_user = user_and_tenant[0]
                    categoria_comissao = CategoriaFinanceira(
                        nome="Comissões",
                        tipo="despesa",
                        descricao="Comissões de vendas",
                        user_id=current_user.id
                    )
                    db.add(categoria_comissao)
                    db.flush()
                
                # 1. CRIAR CONTA A PAGAR
                current_user = user_and_tenant[0]
                periodo = f"{request.data_pagamento.strftime('%m/%Y')}"
                conta_pagar = ContaPagar(
                    descricao=f"Comissão - {funcionario_nome} - {periodo}",
                    fornecedor_id=funcionario_id,
                    categoria_id=categoria_comissao.id,
                    valor_original=Decimal(str(valor_total_fechamento)),
                    valor_final=Decimal(str(valor_total_fechamento)),
                    data_emissao=request.data_pagamento,
                    data_vencimento=request.data_pagamento,
                    status='pendente',
                    observacoes=f"Gerado automaticamente pelo fechamento de comissão. {request.observacao or ''}",
                    user_id=current_user.id
                )
                db.add(conta_pagar)
                db.flush()  # Para obter o ID
                
                # 2. CRIAR LANÇAMENTO MANUAL PREVISTO (FLUXO DE CAIXA)
                lancamento = LancamentoManual(
                    tipo='saida',
                    valor=Decimal(str(valor_total_fechamento)),
                    descricao=f"Pagamento de comissão - {funcionario_nome}",
                    data_lancamento=request.data_pagamento,
                    status='previsto',
                    categoria_id=categoria_comissao.id,
                    gerado_automaticamente=True,
                    observacoes=f"Previsto gerado no fechamento de comissão (Conta a Pagar #{conta_pagar.id})",
                    user_id=current_user.id
                )
                db.add(lancamento)
                db.commit()
                
                logger.info(
                    f"💰 Conta a pagar criada automaticamente: #{conta_pagar.id} - "
                    f"R$ {valor_total_fechamento:.2f} - {funcionario_nome}"
                )
                logger.info(
                    f"📊 Lançamento previsto criado: #{lancamento.id} - "
                    f"R$ {valor_total_fechamento:.2f}"
                )
        finally:
            db.close()
        
        return {
            'success': True,
            'total_processadas': len(comissoes_fechadas),
            'total_ignoradas': len(ids_ignorados),
            'comissoes_fechadas': comissoes_fechadas,
            'comissoes_ignoradas': ids_ignorados,
            'valor_total_fechamento': valor_total_fechamento,
            'data_pagamento': str(request.data_pagamento),
            'message': f'{len(comissoes_fechadas)} comissão(ões) fechada(s) com sucesso'
        }
        
    except Exception as e:
        logger.error(f"Erro ao fechar comissões: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao fechar comissões: {str(e)}")


# ==================== ENDPOINT: HISTÓRICO DE FECHAMENTOS ====================

@router.get("/fechamentos", summary="Histórico de fechamentos de comissões (auditoria)")
def listar_historico_fechamentos(
    data_inicio: Optional[date] = Query(None, description="Data inicial do filtro (data_pagamento)"),
    data_fim: Optional[date] = Query(None, description="Data final do filtro (data_pagamento)"),
    funcionario_id: Optional[int] = Query(None, description="Filtrar por funcionário específico"),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    SPRINT 6 - PASSO 4/5: HISTÓRICO DE FECHAMENTOS
    
    Lista histórico de fechamentos realizados, agrupados por funcionário e data de pagamento.
    
    ⚠️ SOMENTE LEITURA - AUDITORIA:
    - Não permite alterações
    - Não recalcula valores
    - Snapshot imutável
    - Rastreabilidade completa
    
    Regras:
    - Agrupa comissões com status='paga'
    - Agrupa por funcionario_id + data_pagamento + observacao_pagamento
    - Retorna resumo de cada fechamento
    - Ordenação: data_pagamento DESC
    
    Retorna:
    - Lista de fechamentos com resumo financeiro
    - Cada fechamento pode ser expandido para ver detalhes
    """
    try:
        struct_logger.info(
            "COMMISSION_HISTORY_LIST",
            "Consultando histórico de fechamentos",
            extra={
                'data_inicio': str(data_inicio) if data_inicio else None,
                'data_fim': str(data_fim) if data_fim else None,
                'funcionario_id': funcionario_id
            }
        )
        
        from app.tenancy.context import set_tenant_context
        
        # Configurar tenant context
        current_user, tenant_id = user_and_tenant
        set_tenant_context(tenant_id)
        
        db = SessionLocal()
        
        # Query para agrupar fechamentos
        # CORRIGIDO: funcionario_id refere-se à tabela clientes, não users
        query = """
            SELECT 
                ci.funcionario_id,
                c.nome as nome_funcionario,
                ci.data_pagamento,
                ci.observacao_pagamento,
                COUNT(ci.id) as quantidade_comissoes,
                SUM(ci.valor_comissao_gerada) as valor_total,
                MIN(ci.data_venda) as data_venda_mais_antiga,
                MAX(ci.data_venda) as data_venda_mais_recente,
                MIN(ci.data_atualizacao) as data_fechamento
            FROM comissoes_itens ci
            LEFT JOIN clientes c ON ci.funcionario_id = c.id AND c.{tenant_filter}
            WHERE ci.{tenant_filter} AND ci.status = 'paga'
        """
        
        params = {}
        
        # Aplicar filtros
        if data_inicio:
            query += " AND DATE(ci.data_pagamento) >= :data_inicio"
            params["data_inicio"] = str(data_inicio)
        
        if data_fim:
            query += " AND DATE(ci.data_pagamento) <= :data_fim"
            params["data_fim"] = str(data_fim)
        
        if funcionario_id is not None:
            query += " AND ci.funcionario_id = :funcionario_id"
            params["funcionario_id"] = funcionario_id
        
        # Agrupar por funcionário + data_pagamento + observação
        query += """
            GROUP BY ci.funcionario_id, c.nome, ci.data_pagamento, ci.observacao_pagamento
            ORDER BY ci.data_pagamento DESC, ci.funcionario_id ASC
        """
        
        result = execute_tenant_safe(db, query, params)
        rows = result.fetchall()
        
        try:
            # Converter para lista de dicionários
            fechamentos = []
            valor_total_geral = 0.0
            quantidade_total_geral = 0
            
            for row in rows:
                fechamento = {
                    'funcionario_id': row[0],
                    'nome_funcionario': row[1] or 'Funcionário não encontrado',
                    'data_pagamento': row[2],
                    'data_fechamento': row[8],
                    'observacao': row[3],
                    'quantidade_comissoes': row[4],
                    'valor_total': float(row[5]) if row[5] else 0.0,
                    'periodo_vendas': {
                        'data_inicio': row[6],
                        'data_fim': row[7]
                    },
                    # Identificador único do fechamento (para navegação)
                    'fechamento_id': f"{row[0]}_{row[2]}"
                }
                
                fechamentos.append(fechamento)
                valor_total_geral += fechamento['valor_total']
                quantidade_total_geral += fechamento['quantidade_comissoes']
        finally:
            db.close()
        
        struct_logger.info(
            "COMMISSION_HISTORY_LIST_SUCCESS",
            f"{len(fechamentos)} fechamento(s) encontrado(s)",
            extra={
                'total_fechamentos': len(fechamentos),
                'valor_total': valor_total_geral,
                'quantidade_total': quantidade_total_geral
            }
        )
        
        return {
            'success': True,
            'filtros': {
                'data_inicio': str(data_inicio) if data_inicio else None,
                'data_fim': str(data_fim) if data_fim else None,
                'funcionario_id': funcionario_id
            },
            'resumo': {
                'total_fechamentos': len(fechamentos),
                'valor_total_geral': valor_total_geral,
                'quantidade_total_geral': quantidade_total_geral
            },
            'fechamentos': fechamentos
        }
        
    except Exception as e:
        logger.error(f"Erro ao listar histórico de fechamentos: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao listar histórico: {str(e)}")


@router.get("/fechamentos/detalhe", summary="Detalhes de um fechamento específico (auditoria)")
def detalhe_fechamento(
    funcionario_id: int = Query(..., description="ID do funcionário"),
    data_pagamento: date = Query(..., description="Data do pagamento"),
    user_and_tenant = Depends(get_current_user_and_tenant)
):
    """
    SPRINT 6 - PASSO 4/5: DETALHE DE UM FECHAMENTO
    
    Retorna todas as comissões incluídas em um fechamento específico.
    
    ⚠️ SOMENTE LEITURA - AUDITORIA:
    - Não permite alterações
    - Todas as informações são read-only
    - Snapshot imutável
    
    Identificação do fechamento:
    - funcionario_id + data_pagamento (chave composta)
    
    Retorna:
    - Dados do funcionário
    - Informações do fechamento
    - Lista completa de comissões incluídas
    """
    try:
        struct_logger.info(
            "COMMISSION_CLOSURE_DETAIL",
            f"Consultando detalhes do fechamento: funcionário {funcionario_id}, data {data_pagamento}",
            extra={
                'funcionario_id': funcionario_id,
                'data_pagamento': str(data_pagamento)
            }
        )
        
        from app.tenancy.context import set_tenant_context
        
        # Configurar tenant context
        current_user, tenant_id = user_and_tenant
        set_tenant_context(tenant_id)
        
        db = SessionLocal()
        
        try:
            # Buscar dados do funcionário (CORRIGIDO: busca em clientes)
            result = execute_tenant_safe(db, "SELECT nome FROM clientes WHERE id = :id AND {tenant_filter}", {"id": funcionario_id})
            funcionario_row = result.fetchone()
            
            if not funcionario_row:
                raise HTTPException(status_code=404, detail="Funcionário não encontrado")
            
            nome_funcionario = funcionario_row[0]
        
            # Buscar comissões deste fechamento
            query = """
                SELECT 
                    ci.id,
                    ci.venda_id,
                    ci.data_venda,
                    ci.produto_id,
                    ci.quantidade,
                    ci.valor_base_calculo,
                    ci.percentual_comissao,
                    ci.valor_comissao_gerada,
                    ci.tipo_calculo,
                    ci.data_pagamento,
                    ci.observacao_pagamento,
                    ci.data_atualizacao,
                    p.nome as nome_produto,
                    v.cliente_id
                FROM comissoes_itens ci
                LEFT JOIN produtos p ON ci.produto_id = p.id AND {tenant_filter_p}
                LEFT JOIN vendas v ON ci.venda_id = v.id AND {tenant_filter_v}
                WHERE {tenant_filter_ci} 
                  AND ci.funcionario_id = :funcionario_id 
                  AND ci.data_pagamento = :data_pagamento
                  AND ci.status = 'paga'
                ORDER BY ci.data_venda ASC, ci.id ASC
            """
            
            result = execute_tenant_safe(db, query, {"funcionario_id": funcionario_id, "data_pagamento": str(data_pagamento)})
            rows = result.fetchall()
        
            if not rows:
                raise HTTPException(
                    status_code=404, 
                    detail="Fechamento não encontrado (sem comissões pagas nesta data)"
                )
            
            # Buscar nomes dos clientes
            cliente_ids = list(set([row[13] for row in rows if row[13]]))
            clientes_map = {}
            
            if cliente_ids:
                from sqlalchemy import bindparam
                stmt = text("SELECT id, nome FROM clientes WHERE {tenant_filter} AND id IN :ids").bindparams(bindparam("ids", expanding=True))
                result = execute_tenant_safe(db, stmt, {"ids": tuple(cliente_ids)})
                for cliente in result.fetchall():
                    clientes_map[cliente[0]] = cliente[1]
        
            # Converter para lista de dicionários
            comissoes = []
            valor_total = 0.0
            observacao = None
            data_fechamento = None
            
            for row in rows:
                if not observacao:
                    observacao = row[10]
                if not data_fechamento:
                    data_fechamento = row[11]
                
                cliente_nome = clientes_map.get(row[13], 'Cliente não identificado') if row[13] else 'Venda sem cliente'
                
                comissao = {
                    'id': row[0],
                    'venda_id': row[1],
                    'data_venda': row[2],
                    'produto_id': row[3],
                    'nome_produto': row[12] or f'Produto #{row[3]}',
                    'cliente_nome': cliente_nome,
                    'quantidade': float(row[4]) if row[4] else 0.0,
                    'valor_base_calculo': float(row[5]) if row[5] else 0.0,
                    'percentual_comissao': float(row[6]) if row[6] else 0.0,
                    'valor_comissao_gerada': float(row[7]) if row[7] else 0.0,
                    'tipo_calculo': row[8]
                }
                
                comissoes.append(comissao)
                valor_total += comissao['valor_comissao_gerada']
            
            struct_logger.info(
                "COMMISSION_CLOSURE_DETAIL_SUCCESS",
                f"Detalhes carregados: {len(comissoes)} comissão(ões)",
                extra={
                    'funcionario_id': funcionario_id,
                    'data_pagamento': str(data_pagamento),
                    'total_comissoes': len(comissoes),
                    'valor_total': valor_total
                }
            )
            
            return {
                'success': True,
                'fechamento': {
                    'funcionario_id': funcionario_id,
                    'nome_funcionario': nome_funcionario,
                    'data_pagamento': str(data_pagamento),
                    'data_fechamento': data_fechamento,
                    'observacao': observacao,
                    'quantidade_comissoes': len(comissoes),
                    'valor_total': valor_total
                },
                'comissoes': comissoes
            }
        finally:
            db.close()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar detalhes do fechamento: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao buscar detalhes: {str(e)}")
