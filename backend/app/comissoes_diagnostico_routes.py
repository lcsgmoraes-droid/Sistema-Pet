"""
DIAGNÓSTICO E CORREÇÃO DE COMISSÕES

Endpoints para detectar e corrigir problemas no sistema de comissões:
- Vendas finalizadas sem comissão gerada
- Comissões geradas mas não provisionadas
- Configurações faltantes ou inativas

Criado em: 09/02/2026
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, Dict, List, Any
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel
import logging
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.utils.tenant_safe_sql import execute_tenant_safe
from app.tenancy.context import set_tenant_context, get_current_tenant_id

from app.db import get_session
from app.auth.dependencies import get_current_user_and_tenant
from app.models import User
from app.comissoes_provisao import provisionar_comissoes_venda
from app.comissoes_service import gerar_comissoes_venda

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/comissoes", tags=["Comissões - Diagnóstico"])


# ==================== SCHEMAS ====================

class VendaSemComissaoResponse(BaseModel):
    """Schema para vendas sem comissão"""
    venda_id: int
    numero_venda: str
    data_venda: date
    vendedor_id: Optional[int]
    funcionario_id: Optional[int]
    total: float
    status: str
    canal: str
    problema: str
    tem_configuracao: bool
    config_ativa: bool


class ReprovisionarRequest(BaseModel):
    """Schema para reprovisionar comissões"""
    vendas_ids: List[int]


# ==================== ENDPOINTS ====================

@router.get("/diagnostico", response_model=Dict[str, Any])
async def diagnosticar_comissoes(
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    funcionario_id: Optional[int] = None,
    limite: int = 100,
    db: Session = Depends(get_session),
    current_user_tenant: tuple[User, str] = Depends(get_current_user_and_tenant)
):
    """
    Detecta vendas finalizadas sem comissão que deveriam ter.
    
    Retorna:
    - vendas_sem_comissao: Vendas finalizadas sem registro em comissoes_itens
    - comissoes_nao_provisionadas: Comissões geradas mas não provisionadas
    - estatisticas: Resumo dos problemas encontrados
    """
    user, tenant_id = current_user_tenant
    set_tenant_context(tenant_id)
    
    logger.info(f"🔍 Diagnóstico de comissões para tenant {tenant_id}")
    
    try:
        # ============================================================
        # 1. VENDAS FINALIZADAS SEM COMISSÃO
        # ============================================================
        
        filtros_venda = []
        params = {'tenant_id': tenant_id, 'limite': limite}
        
        if data_inicio:
            filtros_venda.append("v.data_venda >= :data_inicio")
            params['data_inicio'] = data_inicio
        
        if data_fim:
            filtros_venda.append("v.data_venda <= :data_fim")
            params['data_fim'] = data_fim
            
        if funcionario_id:
            filtros_venda.append("v.funcionario_id = :funcionario_id")
            params['funcionario_id'] = funcionario_id
        
        where_vendas = " AND ".join(filtros_venda) if filtros_venda else "1=1"
        
        query_vendas_sem_comissao = f"""
            SELECT DISTINCT
                v.id,
                v.numero_venda,
                v.data_venda,
                v.vendedor_id,
                v.funcionario_id,
                v.total,
                v.status,
                v.canal,
                CASE 
                    WHEN NOT EXISTS (
                        SELECT 1 FROM comissoes_itens ci 
                        WHERE ci.venda_id = v.id 
                        AND ci.tenant_id = CAST(:tenant_id AS UUID)
                    ) THEN 'SEM_COMISSAO_GERADA'
                    ELSE 'OUTRO_PROBLEMA'
                END as problema,
                EXISTS (
                    SELECT 1 FROM comissoes_configuracao cc
                    WHERE (
                        (cc.tipo = 'funcionario' AND cc.referencia_id = v.funcionario_id)
                        OR cc.tipo = 'geral'
                    )
                    AND cc.tenant_id = CAST(:tenant_id AS UUID)
                ) as tem_configuracao,
                EXISTS (
                    SELECT 1 FROM comissoes_configuracao cc
                    WHERE (
                        (cc.tipo = 'funcionario' AND cc.referencia_id = v.funcionario_id)
                        OR cc.tipo = 'geral'
                    )
                    AND cc.ativo = true
                    AND cc.tenant_id = CAST(:tenant_id AS UUID)
                ) as config_ativa
            FROM vendas v
            WHERE v.status = 'finalizada'
              AND v.tenant_id = CAST(:tenant_id AS UUID)
              AND {where_vendas}
              AND NOT EXISTS (
                  SELECT 1 FROM comissoes_itens ci 
                  WHERE ci.venda_id = v.id 
                  AND ci.tenant_id = CAST(:tenant_id AS UUID)
              )
            ORDER BY v.data_venda DESC, v.id DESC
            LIMIT :limite
        """
        
        result_vendas = db.execute(text(query_vendas_sem_comissao), params)
        vendas_sem_comissao = []
        
        for row in result_vendas.fetchall():
            vendas_sem_comissao.append(VendaSemComissaoResponse(
                venda_id=row[0],
                numero_venda=row[1],
                data_venda=row[2],
                vendedor_id=row[3],
                funcionario_id=row[4],
                total=float(row[5]) if row[5] else 0.0,
                status=row[6],
                canal=row[7],
                problema=row[8],
                tem_configuracao=row[9],
                config_ativa=row[10]
            ))
        
        # ============================================================
        # 2. COMISSÕES GERADAS MAS NÃO PROVISIONADAS
        # ============================================================
        
        query_nao_provisionadas = """
            SELECT 
                ci.id,
                ci.venda_id,
                v.numero_venda,
                ci.funcionario_id,
                u.nome as funcionario_nome,
                ci.valor_comissao_gerada,
                v.data_venda,
                v.status as venda_status
            FROM comissoes_itens ci
            JOIN vendas v ON ci.venda_id = v.id
            LEFT JOIN users u ON ci.funcionario_id = u.id
            WHERE ci.comissao_provisionada = FALSE
              AND ci.valor_comissao_gerada > 0
              AND ci.status = 'pendente'
              AND v.status IN ('finalizada', 'baixa_parcial')
              AND ci.tenant_id = CAST(:tenant_id AS UUID)
              AND v.tenant_id = CAST(:tenant_id AS UUID)
            ORDER BY v.data_venda DESC, ci.id DESC
            LIMIT :limite
        """
        
        result_nao_prov = db.execute(
            text(query_nao_provisionadas), 
            {'tenant_id': tenant_id, 'limite': limite}
        )
        
        comissoes_nao_provisionadas = []
        for row in result_nao_prov.fetchall():
            comissoes_nao_provisionadas.append({
                'comissao_id': row[0],
                'venda_id': row[1],
                'numero_venda': row[2],
                'funcionario_id': row[3],
                'funcionario_nome': row[4],
                'valor_comissao': float(row[5]),
                'data_venda': row[6].isoformat() if row[6] else None,
                'venda_status': row[7]
            })
        
        # ============================================================
        # 3. ESTATÍSTICAS
        # ============================================================
        
        estatisticas = {
            'total_vendas_sem_comissao': len(vendas_sem_comissao),
            'total_comissoes_nao_provisionadas': len(comissoes_nao_provisionadas),
            'vendas_sem_config': sum(1 for v in vendas_sem_comissao if not v.tem_configuracao),
            'vendas_config_inativa': sum(1 for v in vendas_sem_comissao if v.tem_configuracao and not v.config_ativa),
            'valor_total_nao_provisionado': sum(c['valor_comissao'] for c in comissoes_nao_provisionadas)
        }
        
        logger.info(
            f"✅ Diagnóstico concluído: {estatisticas['total_vendas_sem_comissao']} vendas sem comissão, "
            f"{estatisticas['total_comissoes_nao_provisionadas']} comissões não provisionadas"
        )
        
        return {
            'success': True,
            'vendas_sem_comissao': [v.dict() for v in vendas_sem_comissao],
            'comissoes_nao_provisionadas': comissoes_nao_provisionadas,
            'estatisticas': estatisticas,
            'filtros_aplicados': {
                'data_inicio': data_inicio.isoformat() if data_inicio else None,
                'data_fim': data_fim.isoformat() if data_fim else None,
                'funcionario_id': funcionario_id,
                'limite': limite
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Erro no diagnóstico de comissões: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro no diagnóstico: {str(e)}")


@router.post("/diagnostico/gerar-comissoes", response_model=Dict[str, Any])
async def gerar_comissoes_faltantes(
    request: ReprovisionarRequest,
    db: Session = Depends(get_session),
    current_user_tenant: tuple[User, str] = Depends(get_current_user_and_tenant)
):
    """
    Gera comissões para vendas que não tiveram comissão gerada.
    
    IMPORTANTE: Só funciona se a venda tiver funcionario_id configurado.
    """
    user, tenant_id = current_user_tenant
    set_tenant_context(tenant_id)
    
    logger.info(f"🔧 Gerando comissões faltantes para {len(request.vendas_ids)} vendas")
    
    try:
        resultados = []
        
        for venda_id in request.vendas_ids:
            # Buscar venda
            result_venda = execute_tenant_safe(db, """
                SELECT id, numero_venda, funcionario_id, status
                FROM vendas
                WHERE id = :venda_id AND {tenant_filter}
            """, {'venda_id': venda_id})
            
            venda = result_venda.fetchone()
            
            if not venda:
                resultados.append({
                    'venda_id': venda_id,
                    'success': False,
                    'error': 'Venda não encontrada'
                })
                continue
            
            if not venda.funcionario_id:
                resultados.append({
                    'venda_id': venda_id,
                    'numero_venda': venda.numero_venda,
                    'success': False,
                    'error': 'Venda sem funcionário associado'
                })
                continue
            
            # Verificar se já tem comissão
            result_check = execute_tenant_safe(db, """
                SELECT COUNT(*) FROM comissoes_itens
                WHERE venda_id = :venda_id AND {tenant_filter}
            """, {'venda_id': venda_id})
            
            count = result_check.fetchone()[0]
            if count > 0:
                resultados.append({
                    'venda_id': venda_id,
                    'numero_venda': venda.numero_venda,
                    'success': False,
                    'error': 'Venda já possui comissões'
                })
                continue
            
            # Gerar comissões
            try:
                resultado_geracao = gerar_comissoes_venda(
                    venda_id=venda_id,
                    funcionario_id=venda.funcionario_id,
                    db=db
                )
                
                resultados.append({
                    'venda_id': venda_id,
                    'numero_venda': venda.numero_venda,
                    'success': resultado_geracao['success'],
                    'total_comissao': resultado_geracao.get('total_comissao', 0),
                    'itens_gerados': len(resultado_geracao.get('itens', [])),
                    'provisao': resultado_geracao.get('provisao', {})
                })
                
            except Exception as e:
                logger.error(f"Erro ao gerar comissão para venda {venda_id}: {str(e)}")
                resultados.append({
                    'venda_id': venda_id,
                    'numero_venda': venda.numero_venda,
                    'success': False,
                    'error': str(e)
                })
        
        sucesso_count = sum(1 for r in resultados if r['success'])
        
        logger.info(f"✅ Geração concluída: {sucesso_count}/{len(resultados)} vendas processadas com sucesso")
        
        return {
            'success': True,
            'resultados': resultados,
            'estatisticas': {
                'total_processado': len(resultados),
                'sucesso': sucesso_count,
                'erro': len(resultados) - sucesso_count
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao gerar comissões faltantes: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao gerar comissões: {str(e)}")


@router.post("/diagnostico/reprovisionar", response_model=Dict[str, Any])
async def reprovisionar_comissoes(
    request: ReprovisionarRequest,
    db: Session = Depends(get_session),
    current_user_tenant: tuple[User, str] = Depends(get_current_user_and_tenant)
):
    """
    Reprovisiona comissões já geradas mas não provisionadas.
    
    Usa a função provisionar_comissoes_venda para criar:
    - Contas a Pagar
    - Lançamentos DRE
    """
    user, tenant_id = current_user_tenant
    set_tenant_context(tenant_id)
    
    logger.info(f"🔧 Reprovisionando comissões para {len(request.vendas_ids)} vendas")
    
    try:
        resultados = []
        
        for venda_id in request.vendas_ids:
            try:
                resultado_provisao = provisionar_comissoes_venda(
                    venda_id=venda_id,
                    tenant_id=tenant_id,
                    db=db
                )
                
                resultados.append({
                    'venda_id': venda_id,
                    'success': resultado_provisao['success'],
                    'comissoes_provisionadas': resultado_provisao['comissoes_provisionadas'],
                    'valor_total': resultado_provisao['valor_total'],
                    'contas_criadas': resultado_provisao.get('contas_criadas', []),
                    'message': resultado_provisao.get('message', '')
                })
                
            except Exception as e:
                logger.error(f"Erro ao reprovisionar venda {venda_id}: {str(e)}")
                resultados.append({
                    'venda_id': venda_id,
                    'success': False,
                    'error': str(e),
                    'comissoes_provisionadas': 0,
                    'valor_total': 0.0
                })
        
        sucesso_count = sum(1 for r in resultados if r['success'])
        valor_total_provisionado = sum(r.get('valor_total', 0) for r in resultados if r['success'])
        
        logger.info(
            f"✅ Reprovisionamento concluído: {sucesso_count}/{len(resultados)} vendas, "
            f"Total: R$ {valor_total_provisionado:.2f}"
        )
        
        return {
            'success': True,
            'resultados': resultados,
            'estatisticas': {
                'total_processado': len(resultados),
                'sucesso': sucesso_count,
                'erro': len(resultados) - sucesso_count,
                'valor_total_provisionado': valor_total_provisionado
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao reprovisionar comissões: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao reprovisionar: {str(e)}")


@router.get("/diagnostico/venda/{venda_id}", response_model=Dict[str, Any])
async def diagnosticar_venda_especifica(
    venda_id: int,
    db: Session = Depends(get_session),
    current_user_tenant: tuple[User, str] = Depends(get_current_user_and_tenant)
):
    """
    Diagnóstico completo de uma venda específica:
    - Dados da venda
    - Comissões geradas
    - Configurações aplicáveis
    - Problemas identificados
    - Ações sugeridas
    """
    user, tenant_id = current_user_tenant
    set_tenant_context(tenant_id)
    
    logger.info(f"🔍 Diagnóstico detalhado da venda {venda_id}")
    
    # 1. Buscar venda
    result_venda = execute_tenant_safe(db, """
        SELECT 
            v.id, v.numero_venda, v.status, v.total, v.subtotal,
            v.funcionario_id, v.data_venda, v.data_finalizacao,
            u.nome as funcionario_nome
        FROM vendas v
        LEFT JOIN users u ON v.funcionario_id = u.id
        WHERE v.id = :venda_id AND {tenant_filter}
    """, {'venda_id': venda_id})
    
    venda = result_venda.fetchone()
    if not venda:
        raise HTTPException(status_code=404, detail="Venda não encontrada")
    
    venda_info = {
        'id': venda[0],
        'numero_venda': venda[1],
        'status': venda[2],
        'total': float(venda[3]),
        'subtotal': float(venda[4]) if venda[4] else 0,
        'funcionario_id': venda[5],
        'data_venda': venda[6].isoformat() if venda[6] else None,
        'data_finalizacao': venda[7].isoformat() if venda[7] else None,
        'funcionario_nome': venda[8]
    }
    
    # 2. Buscar comissões geradas
    result_comissoes = execute_tenant_safe(db, """
        SELECT 
            ci.id, ci.tipo_comissao, ci.percentual_comissao,
            ci.valor_base, ci.valor_comissao, ci.status,
            ci.produto_nome, ci.preco_custo_snapshot
        FROM comissoes_itens ci
        WHERE ci.venda_id = :venda_id AND {tenant_filter}
    """, {'venda_id': venda_id})
    
    comissoes = []
    total_comissao = 0
    for row in result_comissoes.fetchall():
        comissao = {
            'id': row[0],
            'tipo': row[1],
            'percentual': float(row[2]),
            'valor_base': float(row[3]),
            'valor_comissao': float(row[4]),
            'status': row[5],
            'produto_nome': row[6],
            'preco_custo_snapshot': float(row[7]) if row[7] else None
        }
        comissoes.append(comissao)
        total_comissao += comissao['valor_comissao']
    
    # 3. Buscar configurações de comissão
    configuracoes = []
    if venda_info['funcionario_id']:
        result_config = execute_tenant_safe(db, """
            SELECT 
                cc.id, cc.tipo, cc.referencia_id, cc.percentual, cc.ativo,
                CASE 
                    WHEN cc.tipo = 'produto' THEN p.nome
                    WHEN cc.tipo = 'categoria' THEN c.nome
                    ELSE 'Global'
                END as referencia_nome
            FROM comissoes_configuracao cc
            LEFT JOIN produtos p ON cc.tipo = 'produto' AND cc.referencia_id = p.id
            LEFT JOIN categorias c ON cc.tipo = 'categoria' AND cc.referencia_id = c.id
            WHERE cc.funcionario_id = :func_id AND {tenant_filter}
        """, {'func_id': venda_info['funcionario_id']})
        
        for row in result_config.fetchall():
            configuracoes.append({
                'id': row[0],
                'tipo': row[1],
                'referencia_id': row[2],
                'percentual': float(row[3]),
                'ativo': row[4],
                'referencia_nome': row[5]
            })
    
    # 4. Buscar itens da venda
    result_itens = execute_tenant_safe(db, """
        SELECT 
            vi.produto_id, vi.quantidade, vi.preco_unitario, vi.subtotal,
            p.nome, p.preco_custo
        FROM venda_itens vi
        LEFT JOIN produtos p ON vi.produto_id = p.id
        WHERE vi.venda_id = :venda_id AND {tenant_filter}
    """, {'venda_id': venda_id})
    
    itens = []
    for row in result_itens.fetchall():
        itens.append({
            'produto_id': row[0],
            'quantidade': float(row[1]),
            'preco_unitario': float(row[2]),
            'subtotal': float(row[3]),
            'produto_nome': row[4],
            'preco_custo': float(row[5]) if row[5] else None
        })
    
    # 5. Buscar pagamentos
    result_pagamentos = execute_tenant_safe(db, """
        SELECT COUNT(*), COALESCE(SUM(valor), 0)
        FROM venda_pagamentos
        WHERE venda_id = :venda_id AND {tenant_filter}
    """, {'venda_id': venda_id})
    
    pag = result_pagamentos.fetchone()
    pagamentos_info = {
        'count': pag[0],
        'total_pago': float(pag[1])
    }
    
    # 6. DIAGNÓSTICO
    problemas = []
    acoes = []
    
    # Verificar se deveria ter comissão
    if venda_info['status'] not in ['finalizada', 'baixa_parcial']:
        problemas.append({
            'tipo': 'info',
            'mensagem': f"Venda com status '{venda_info['status']}' não gera comissões automaticamente"
        })
    
    if not venda_info['funcionario_id']:
        problemas.append({
            'tipo': 'error',
            'mensagem': "Venda sem funcionário/veterinário - não pode gerar comissões"
        })
    
    if venda_info['funcionario_id'] and len(configuracoes) == 0:
        problemas.append({
            'tipo': 'warning',
            'mensagem': f"Funcionário '{venda_info['funcionario_nome']}' não possui configurações de comissão"
        })
    
    if venda_info['status'] in ['finalizada', 'baixa_parcial'] and venda_info['funcionario_id'] and len(comissoes) == 0:
        problemas.append({
            'tipo': 'error',
            'mensagem': "🚨 PROBLEMA: Venda finalizada com funcionário mas SEM comissões geradas"
        })
        
        if len(configuracoes) > 0:
            acoes.append({
                'endpoint': f'POST /comissoes/diagnostico/gerar-comissoes',
                'body': {'vendas_ids': [venda_id]},
                'descricao': 'Gerar comissões faltantes'
            })
    
    return {
        'venda': venda_info,
        'comissoes': {
            'total': len(comissoes),
            'valor_total_comissao': total_comissao,
            'itens': comissoes
        },
        'configuracoes': configuracoes,
        'itens_venda': itens,
        'pagamentos': pagamentos_info,
        'diagnostico': {
            'tem_problema': any(p['tipo'] == 'error' for p in problemas),
            'problemas': problemas,
            'acoes_sugeridas': acoes
        }
    }


@router.get("/diagnostico/listar-vendas-sem-comissoes", response_model=Dict[str, Any])
async def listar_vendas_sem_comissoes_rapido(
    limite: int = 50,
    db: Session = Depends(get_session),
    current_user_tenant: tuple[User, str] = Depends(get_current_user_and_tenant)
):
    """
    Lista rapidamente vendas finalizadas com funcionário mas sem comissões.
    Útil para identificar problemas em massa.
    """
    user, tenant_id = current_user_tenant
    set_tenant_context(tenant_id)
    
    logger.info(f"🔍 Listando vendas sem comissões (limite: {limite})")
    
    result = execute_tenant_safe(db, """
        SELECT 
            v.id, v.numero_venda, v.status, v.total,
            v.data_venda, v.data_finalizacao,
            v.funcionario_id, u.nome as funcionario_nome
        FROM vendas v
        LEFT JOIN users u ON v.funcionario_id = u.id
        WHERE {tenant_filter}
        AND v.status IN ('finalizada', 'baixa_parcial')
        AND v.funcionario_id IS NOT NULL
        AND NOT EXISTS (
            SELECT 1 FROM comissoes_itens ci
            WHERE ci.venda_id = v.id
        )
        ORDER BY v.data_venda DESC
        LIMIT :limite
    """, {'limite': limite})
    
    vendas = []
    for row in result.fetchall():
        vendas.append({
            'id': row[0],
            'numero_venda': row[1],
            'status': row[2],
            'total': float(row[3]),
            'data_venda': row[4].isoformat() if row[4] else None,
            'data_finalizacao': row[5].isoformat() if row[5] else None,
            'funcionario_id': row[6],
            'funcionario_nome': row[7]
        })
    
    return {
        'total_encontrado': len(vendas),
        'limite_consulta': limite,
        'vendas': vendas,
        'acao_sugerida': {
            'endpoint': 'POST /comissoes/diagnostico/gerar-comissoes',
            'descricao': 'Enviar array de vendas_ids para gerar comissões em lote'
        }
    }
