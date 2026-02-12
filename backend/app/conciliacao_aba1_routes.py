"""
API Routes para ABA 1: Conciliação de Vendas (PDV vs Stone)

Arquitetura de Duas Colunas:
- Esquerda: Vendas PDV com cartão (sempre carregadas)
- Direita: NSUs da planilha Stone importada
- Match automático + confirmação manual
"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy import and_, or_, func
from typing import Optional, List
from datetime import date, datetime
from pydantic import BaseModel
import logging

from .db import get_session
from .auth.dependencies import get_current_user_and_tenant
from .vendas_models import Venda, VendaPagamento
from .conciliacao_models import ConciliacaoImportacao, ArquivoEvidencia
from .conciliacao_helpers import serialize_for_json, calcular_hash_arquivo, aplicar_template_csv
from .conciliacao_models import AdquirenteTemplate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/conciliacao/aba1", tags=["Conciliação Vendas - Aba 1"])


# ==============================================================================
# SCHEMAS
# ==============================================================================

class ConfirmarMatchRequest(BaseModel):
    """Confirmar match entre venda PDV e NSU Stone"""
    venda_id: int
    nsu_stone: str
    aplicar_correcoes: bool = False  # Se True, atualiza dados do PDV com dados da Stone


class CorrigirDivergenciaRequest(BaseModel):
    """Corrigir divergência manualmente"""
    venda_id: int
    nsu_stone: str
    campo: str  # "parcelas", "bandeira", "valor"
    novo_valor: str
    motivo: str


# ==============================================================================
# ENDPOINT: Listar Vendas PDV Pendentes (Coluna Esquerda)
# ==============================================================================

@router.get("/vendas-pdv")
async def listar_vendas_pdv(
    status: str = Query("pendentes", description="pendentes, todas, conciliadas"),
    operadora_id: Optional[str] = None,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    auth = Depends(get_current_user_and_tenant)
):
    """
    **Coluna Esquerda: Vendas do PDV com cartão**
    
    Retorna vendas com pagamento em cartão (débito/crédito).
    
    Filtros:
    - status: "pendentes" (sem NSU ou não conciliadas), "todas", "conciliadas"
    - operadora_id: Filtrar por operadora (número) ou "legacy" (sem operadora)
    - data_inicio/fim: Período
    - Paginação: page, limit
    
    Retorna dados compactos por padrão (número venda + NSU se tiver).
    """
    user, tenant_id = auth
    db = next(get_session())
    
    try:
        # Query base: vendas finalizadas com pagamento cartão (débito/crédito apenas, sem PIX)
        query = db.query(Venda).join(VendaPagamento).filter(
            Venda.tenant_id == tenant_id,
            Venda.status == 'finalizada',
            or_(
                VendaPagamento.forma_pagamento.ilike('%débito%'),
                VendaPagamento.forma_pagamento.ilike('%crédito%'),
                VendaPagamento.forma_pagamento.ilike('%cartão%')
            )
        )
        
        # Filtro por status
        if status == "pendentes":
            # Apenas não conciliadas (independente de ter NSU ou não)
            query = query.filter(VendaPagamento.status_conciliacao == 'nao_conciliado')
            logger.info(f"[Vendas PDV] Filtro: status_conciliacao = 'nao_conciliado'")
        elif status == "com_nsu":
            # Vendas que já têm NSU
            query = query.filter(VendaPagamento.nsu_cartao.isnot(None))
        elif status == "conciliadas":
            # Vendas já conciliadas
            query = query.filter(VendaPagamento.status_conciliacao == 'conciliado')
            logger.info(f"[Vendas PDV] Filtro: status_conciliacao = 'conciliado'")
        # Se status == "todas", não aplica filtro de NSU
        
        # Filtro por operadora
        if operadora_id:
            if operadora_id.lower() == "legacy":
                # Vendas sem operadora (Legacy)
                query = query.filter(VendaPagamento.operadora_id.is_(None))
            else:
                # Operadora específica
                query = query.filter(VendaPagamento.operadora_id == int(operadora_id))
        
        # Filtro por data
        if data_inicio:
            query = query.filter(Venda.data_venda >= datetime.fromisoformat(data_inicio).date())
        if data_fim:
            query = query.filter(Venda.data_venda <= datetime.fromisoformat(data_fim).date())
        
        # Count total
        total = query.distinct(Venda.id).count()
        
        # Paginação
        vendas = query.distinct().offset((page - 1) * limit).limit(limit).all()
        
        # Serializar vendas (modo compacto)
        resultado = []
        for venda in vendas:
            # Pegar primeiro pagamento cartão (aceita variações de escrita)
            def is_cartao(forma):
                if not forma:
                    return False
                forma_lower = forma.lower()
                return any(keyword in forma_lower for keyword in ['débito', 'debito', 'crédito', 'credito', 'pix', 'cartão', 'cartao'])
            
            pagamento_cartao = next((p for p in venda.pagamentos if is_cartao(p.forma_pagamento)), None)
            
            if not pagamento_cartao:
                continue
            
            venda_dict = {
                'id': venda.id,
                'numero_venda': venda.numero_venda,
                'data_venda': venda.data_venda.isoformat() if venda.data_venda else None,
                'total': float(venda.total),
                'conciliado': venda.conciliado_vendas,
                
                # Dados compactos do pagamento
                'pagamento': {
                    'id': pagamento_cartao.id,
                    'nsu': pagamento_cartao.nsu_cartao,
                    'forma': pagamento_cartao.forma_pagamento,
                    'bandeira': pagamento_cartao.bandeira,
                    'parcelas': pagamento_cartao.numero_parcelas,
                    'valor': float(pagamento_cartao.valor),
                    'operadora_id': pagamento_cartao.operadora_id,
                    'status_conciliacao': pagamento_cartao.status_conciliacao
                }
            }
            
            resultado.append(venda_dict)
        
        return JSONResponse(content=serialize_for_json({
            'success': True,
            'vendas': resultado,
            'total': total,
            'page': page,
            'limit': limit,
            'total_pages': (total + limit - 1) // limit
        }))
    
    except Exception as e:
        logger.error(f"Erro ao listar vendas PDV: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        db.close()


# ==============================================================================
# ENDPOINT: Listar NSUs Stone Não Conciliados (Coluna Direita)
# ==============================================================================

@router.get("/stone-nao-conciliadas")
async def listar_stone_nao_conciliadas(
    importacao_id: Optional[int] = None,
    operadora_id: Optional[int] = None,  # FILTRO por operadora
    status: str = Query('pendentes', regex='^(pendentes|todas|conciliadas)$'),  # FILTRO por status
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    auth = Depends(get_current_user_and_tenant)
):
    """
    **Coluna Direita: NSUs da planilha não conciliados**
    
    Retorna NSUs importados que ainda não foram vinculados a vendas PDV.
    
    Se importacao_id for fornecido, retorna apenas dessa importação.
    Se operadora_id for fornecido, filtra apenas importações dessa operadora.
    Senão, retorna todos NSUs não conciliados.
    """
    user, tenant_id = auth
    db = next(get_session())
    
    try:
        # Buscar última importação (com filtro opcional de operadora)
        if not importacao_id:
            query_filtros = [
                ConciliacaoImportacao.tenant_id == tenant_id,
                ConciliacaoImportacao.tipo_importacao == 'vendas',
                ConciliacaoImportacao.status_importacao == 'processada'
            ]
            
            # Quando filtro = "pendentes", buscar apenas importações não totalmente conciliadas
            if status == 'pendentes':
                query_filtros.append(
                    or_(
                        ConciliacaoImportacao.resumo['conciliado'].astext == 'false',
                        ConciliacaoImportacao.resumo['conciliado'].is_(None)
                    )
                )
            # Quando filtro = "conciliadas" ou "todas", buscar última importação independente do status
            
            # FILTRO POR OPERADORA (se fornecido)
            if operadora_id:
                query_filtros.append(
                    ConciliacaoImportacao.resumo['operadora_id'].astext == str(operadora_id)
                )
            
            ultima_importacao = db.query(ConciliacaoImportacao).filter(
                *query_filtros
            ).order_by(ConciliacaoImportacao.criado_em.desc()).first()
            
            if not ultima_importacao:
                return JSONResponse(content={'success': True, 'nsus': [], 'total': 0})
            
            importacao_id = ultima_importacao.id
        
        # Buscar importação
        importacao = db.query(ConciliacaoImportacao).filter(
            ConciliacaoImportacao.id == importacao_id,
            ConciliacaoImportacao.tenant_id == tenant_id
        ).first()
        
        if not importacao:
            raise HTTPException(status_code=404, detail="Importação não encontrada")
        
        # Buscar dados parseados do resumo da importação
        if not importacao.resumo or 'dados_parseados' not in importacao.resumo:
            return JSONResponse(content={
                'success': True,
                'nsus': [],
                'total': 0,
                'mensagem': 'Nenhum dado encontrado nesta importação'
            })
        
        dados_parseados = importacao.resumo.get('dados_parseados', [])
        
        # DEBUG: Contar status de cada NSU
        total_nsus = len(dados_parseados)
        conciliados = sum(1 for n in dados_parseados if n.get('status_conciliacao') == 'conciliado')
        nao_conciliados = sum(1 for n in dados_parseados if n.get('status_conciliacao', 'nao_conciliado') == 'nao_conciliado')
        sem_status = sum(1 for n in dados_parseados if 'status_conciliacao' not in n)
        
        logger.info(f"[Stone NSUs DEBUG] Total NSUs: {total_nsus} | Conciliados: {conciliados} | Não conciliados: {nao_conciliados} | Sem status: {sem_status}")
        
        # Filtrar NSUs por status
        if status == "pendentes":
            # Apenas NÃO conciliados
            nsus_filtrados = [
                nsu for nsu in dados_parseados 
                if nsu.get('status_conciliacao', 'nao_conciliado') == 'nao_conciliado'
            ]
            logger.info(f"[Stone NSUs] Filtro: status_conciliacao = 'nao_conciliado' → {len(nsus_filtrados)} NSUs")
        elif status == "conciliadas":
            # Apenas conciliados
            nsus_filtrados = [
                nsu for nsu in dados_parseados 
                if nsu.get('status_conciliacao') == 'conciliado'
            ]
            logger.info(f"[Stone NSUs] Filtro: status_conciliacao = 'conciliado' → {len(nsus_filtrados)} NSUs")
        else:  # status == "todas"
            # Mostrar todos os NSUs
            nsus_filtrados = dados_parseados
            logger.info(f"[Stone NSUs] Filtro: Todos os NSUs → {len(nsus_filtrados)} NSUs")
        
        # Paginar NSUs
        total = len(nsus_filtrados)
        inicio = (page - 1) * limit
        fim = inicio + limit
        nsus_pagina = nsus_filtrados[inicio:fim]
        
        # Formatar NSUs para exibição
        nsus_formatados = []
        for idx, linha in enumerate(nsus_pagina):
            nsu_dict = {
                'id': inicio + idx,
                'nsu': linha.get('nsu'),
                'data_venda': linha.get('data_venda'),
                'bandeira': linha.get('bandeira'),
                'parcelas': linha.get('parcelas'),
                'valor_bruto': linha.get('valor_bruto'),
                'valor_liquido': linha.get('valor_liquido'),
                'operadora_id': importacao.resumo.get('operadora_id')
            }
            nsus_formatados.append(nsu_dict)
        
        return JSONResponse(content=serialize_for_json({
            'success': True,
            'nsus': nsus_formatados,
            'total': total,
            'importacao_id': importacao_id,
            'page': page,
            'limit': limit,
            'total_pages': (total + limit - 1) // limit,
            'operadora_id': importacao.resumo.get('operadora_id')
        }))
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao listar Stone não conciliadas: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        db.close()


# ==============================================================================
# ENDPOINT: Processar Matches Automáticos
# ==============================================================================

@router.post("/processar-matches")
async def processar_matches(
    importacao_id: Optional[int] = None,
    auth = Depends(get_current_user_and_tenant)
):
    """
    **Processar matches automáticos entre PDV e Stone**
    
    Busca NSUs na planilha Stone que batem com vendas PDV.
    Retorna lista de matches sugeridos para confirmação do usuário.
    
    Não altera dados - apenas sugere matches.
    """
    user, tenant_id = auth
    db = next(get_session())
    
    try:
        from .conciliacao_services import conciliar_vendas_stone
        
        # Buscar última importação se não especificada
        if not importacao_id:
            ultima_importacao = db.query(ConciliacaoImportacao).filter(
                ConciliacaoImportacao.tenant_id == tenant_id,
                ConciliacaoImportacao.tipo_importacao == 'vendas',
                ConciliacaoImportacao.status_importacao == 'processada'
            ).order_by(ConciliacaoImportacao.criado_em.desc()).first()
            
            if not ultima_importacao:
                raise HTTPException(status_code=404, detail="Nenhuma importação Stone encontrada")
            
            importacao_id = ultima_importacao.id
        
        # Buscar importação
        importacao = db.query(ConciliacaoImportacao).filter(
            ConciliacaoImportacao.id == importacao_id,
            ConciliacaoImportacao.tenant_id == tenant_id
        ).first()
        
        if not importacao:
            raise HTTPException(status_code=404, detail="Importação não encontrada")
        
        # Buscar dados parseados
        if not importacao.resumo or 'dados_parseados' not in importacao.resumo:
            raise HTTPException(status_code=400, detail="Dados parseados não encontrados")
        
        dados_parseados = importacao.resumo.get('dados_parseados', [])
        operadora_id = importacao.resumo.get('operadora_id')
        
        if not dados_parseados:
            raise HTTPException(status_code=400, detail="Nenhum NSU encontrado para processar")
        
        # Filtrar apenas NSUs NÃO conciliados
        nsus_pendentes = [
            nsu for nsu in dados_parseados 
            if nsu.get('status_conciliacao', 'nao_conciliado') == 'nao_conciliado'
        ]
        
        if not nsus_pendentes:
            raise HTTPException(status_code=400, detail="Nenhum NSU pendente para processar. Todos já foram conciliados.")
        
        logger.info(f"[Processar Matches] {len(nsus_pendentes)} NSUs pendentes para conciliar (de {len(dados_parseados)} totais)")
        
        # Processar conciliação agora (apenas com NSUs pendentes)
        resultado = conciliar_vendas_stone(
            db=db,
            tenant_id=tenant_id,
            vendas_stone=nsus_pendentes,  # Usar apenas pendentes
            user_id=user.id,
            operadora_id=operadora_id
        )
        
        if not resultado.get('success'):
            raise HTTPException(status_code=400, detail=resultado.get('error'))
        
        # NÃO salvar ainda - apenas retornar matches para visualização
        # Será salvo apenas após usuário confirmar
        
        logger.info(f"[Processar Matches] Encontrados: {resultado.get('conferidas')} OK, {resultado.get('orfaos')} órfãos")
        
        # Retornar matches estruturados para visualização
        return JSONResponse(content=serialize_for_json({
            'success': True,
            'matches': resultado.get('matches', []),  # Array detalhado de matches
            'conferidas': resultado.get('conferidas', 0),
            'corrigidas': resultado.get('corrigidas', 0),
            'sem_nsu': resultado.get('sem_nsu', 0),
            'orfaos': resultado.get('orfaos', 0),
            'divergencias': resultado.get('divergencias', [])
        }))
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao processar matches: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        db.close()


# ==============================================================================
# ENDPOINT: Confirmar Matches (Salvar no Histórico)
# ==============================================================================

class ConfirmarMatchesRequest(BaseModel):
    importacao_id: int
    matches_confirmados: List[dict]

@router.post("/confirmar-matches")
async def confirmar_matches(
    request: ConfirmarMatchesRequest,
    auth = Depends(get_current_user_and_tenant)
):
    """
    Confirma matches após visualização do usuário.
    Salva no histórico APENAS matches OK (sem divergências).
    """
    user, tenant_id = auth
    db = next(get_session())
    
    importacao_id = request.importacao_id
    matches_confirmados = request.matches_confirmados
    
    try:
        # Buscar importação
        importacao = db.query(ConciliacaoImportacao).filter(
            ConciliacaoImportacao.id == importacao_id,
            ConciliacaoImportacao.tenant_id == tenant_id
        ).first()
        
        if not importacao:
            raise HTTPException(status_code=404, detail="Importação não encontrada")
        
        # APENAS matches OK vão para o histórico (filtrar outros)
        matches_ok = [m for m in matches_confirmados if m.get('status') == 'ok']
        
        if not matches_ok:
            raise HTTPException(status_code=400, detail="Nenhum match OK para salvar")
        
        # PREVENIR confirmar vendas JÁ conciliadas
        from .vendas_models import Venda, VendaPagamento
        vendas_ja_conciliadas = []
        
        for match in matches_ok:
            if not match.get('venda_pdv'):
                continue
            
            venda_id = match['venda_pdv'].get('id')
            if not venda_id:
                continue
            
            # Verificar se venda já está conciliada
            venda = db.query(Venda).filter(
                Venda.id == venda_id,
                Venda.tenant_id == tenant_id
            ).first()
            
            if venda:
                for pagamento in venda.pagamentos:
                    if pagamento.status_conciliacao == 'conciliado':
                        vendas_ja_conciliadas.append(f"Venda #{venda.numero_venda}")
                        break
        
        if vendas_ja_conciliadas:
            raise HTTPException(
                status_code=400, 
                detail=f"As seguintes vendas já estão conciliadas: {', '.join(vendas_ja_conciliadas)}"
            )
        
        # REMOVER NSUs conciliados do dados_parseados
        # Extrair NSUs que foram matcheados com sucesso
        nsus_conciliados = set()
        for match in matches_ok:
            if match.get('venda_stone') and match['venda_stone'].get('nsu'):
                nsus_conciliados.add(match['venda_stone']['nsu'])
        
        # APLICAR CONCILIAÇÕES: Atualizar NSUs nas vendas do PDV
        vendas_atualizadas = 0
        for match in matches_ok:
            if not match.get('venda_pdv') or not match.get('venda_stone'):
                continue
            
            venda_id = match['venda_pdv'].get('id')
            nsu_stone = match['venda_stone'].get('nsu')
            
            if not venda_id or not nsu_stone:
                continue
            
            # Buscar venda e seus pagamentos
            venda = db.query(Venda).filter(
                Venda.id == venda_id,
                Venda.tenant_id == tenant_id
            ).first()
            
            if venda:
                # Encontrar pagamento com cartão (qualquer um, com ou sem NSU)
                for pagamento in venda.pagamentos:
                    forma_lower = (pagamento.forma_pagamento or '').lower()
                    is_cartao = any(keyword in forma_lower for keyword in ['débito', 'debito', 'crédito', 'credito', 'cartão', 'cartao'])
                    
                    if is_cartao:
                        # Atualizar NSU se não tiver
                        if not pagamento.nsu_cartao:
                            pagamento.nsu_cartao = nsu_stone
                        # SEMPRE marcar como conciliado ao confirmar match
                        pagamento.status_conciliacao = 'conciliado'
                        vendas_atualizadas += 1
                        logger.info(f"[Confirmar Matches] Venda #{venda.numero_venda} ({pagamento.forma_pagamento}) marcada como CONCILIADA (NSU: {nsu_stone})")
                        break  # Apenas um pagamento por venda
        
        logger.info(f"[Confirmar Matches] {vendas_atualizadas} vendas atualizadas com NSU")
        
        # Marcar NSUs como conciliados em dados_parseados (em vez de remover)
        dados_parseados_original = importacao.resumo.get('dados_parseados', [])
        nsus_nao_conciliados = 0
        nsus_marcados = 0
        
        logger.info(f"[Confirmar Matches] ANTES: Total de NSUs na importação: {len(dados_parseados_original)}")
        logger.info(f"[Confirmar Matches] NSUs a marcar como conciliados: {nsus_conciliados}")
        
        for nsu_data in dados_parseados_original:
            nsu_atual = nsu_data.get('nsu')
            status_antes = nsu_data.get('status_conciliacao', 'nao_definido')
            
            if nsu_atual in nsus_conciliados:
                # Marcar como conciliado
                nsu_data['status_conciliacao'] = 'conciliado'
                nsus_marcados += 1
                logger.info(f"[Confirmar Matches] ✅ NSU {nsu_atual} marcado: {status_antes} → conciliado")
            else:
                # Garantir que tem status (para NSUs antigos)
                if 'status_conciliacao' not in nsu_data:
                    nsu_data['status_conciliacao'] = 'nao_conciliado'
                
                if nsu_data.get('status_conciliacao') == 'nao_conciliado':
                    nsus_nao_conciliados += 1
        
        logger.info(f"[Confirmar Matches] ✅ {nsus_marcados} NSUs marcados como conciliados")
        logger.info(f"[Confirmar Matches] ⏳ {nsus_nao_conciliados} NSUs ainda não conciliados")
        
        # CRIAR NOVO DICIONÁRIO para forçar detecção de mudança
        novo_resumo = dict(importacao.resumo)  # Cópia
        novo_resumo['dados_parseados'] = dados_parseados_original
        novo_resumo['conciliado'] = nsus_nao_conciliados == 0
        novo_resumo['conferidas'] = len(matches_ok)
        novo_resumo['matches_confirmados'] = matches_ok
        
        # Atualizar com novo objeto
        importacao.resumo = novo_resumo
        
        # FORÇAR detecção de mudança no campo JSONB
        flag_modified(importacao, 'resumo')
        
        logger.info(f"[Confirmar Matches] 💾 Salvando mudanças no banco...")
        
        # COMMIT
        db.commit()
        
        # Verificar se salvou (re-buscar do banco)
        db.refresh(importacao)
        nsus_conciliados_apos = sum(1 for n in importacao.resumo.get('dados_parseados', []) if n.get('status_conciliacao') == 'conciliado')
        logger.info(f"[Confirmar Matches] ✅ VERIFICAÇÃO PÓS-COMMIT: {nsus_conciliados_apos} NSUs conciliados no banco")
        
        logger.info(f"[Confirmar Matches] ✅ COMMIT REALIZADO - {vendas_atualizadas} vendas marcadas como CONCILIADAS")
        logger.info(f"[Confirmar Matches] Salvos no histórico: {len(matches_ok)} matches OK")
        
        return JSONResponse(content={
            'success': True,
            'message': f'{len(matches_ok)} matches OK salvos no histórico',
            'vendas_conciliadas': vendas_atualizadas
        })
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao confirmar matches: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        db.close()


# ==============================================================================
# ENDPOINT: Histórico de Conciliações
# ==============================================================================

@router.get("/historico")
async def listar_historico(
    operadora_id: Optional[int] = None,  # FILTRO por operadora
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    auth = Depends(get_current_user_and_tenant)
):
    """
    Lista histórico de conciliações confirmadas.
    Retorna importações que tiveram matches confirmados.
    Pode filtrar por operadora_id.
    """
    user, tenant_id = auth
    db = next(get_session())
    
    try:
        # Buscar importações com matches confirmados
        query_filtros = [
            ConciliacaoImportacao.tenant_id == tenant_id,
            ConciliacaoImportacao.tipo_importacao == 'vendas',
            ConciliacaoImportacao.status_importacao == 'processada',
            ConciliacaoImportacao.resumo['matches_confirmados'].isnot(None)
        ]
        
        # FILTRO POR OPERADORA (opcional)
        if operadora_id:
            query_filtros.append(
                ConciliacaoImportacao.resumo['operadora_id'].astext == str(operadora_id)
            )
        
        query = db.query(ConciliacaoImportacao).filter(
            *query_filtros
        ).order_by(ConciliacaoImportacao.criado_em.desc())
        
        total = query.count()
        importacoes = query.offset((page - 1) * limit).limit(limit).all()
        
        # Formatar histórico
        historico = []
        for imp in importacoes:
            matches_confirmados = imp.resumo.get('matches_confirmados', [])
            historico.append({
                'id': imp.id,
                'data_importacao': imp.criado_em.isoformat() if imp.criado_em else None,
                'operadora_id': imp.resumo.get('operadora_id'),
                'total_matches': len(matches_confirmados),
                'conferidas': imp.resumo.get('conferidas', 0),
                'matches': matches_confirmados  # Detalhes completos
            })
        
        return JSONResponse(content=serialize_for_json({
            'success': True,
            'historico': historico,
            'total': total,
            'page': page,
            'limit': limit,
            'total_pages': (total + limit - 1) // limit if total > 0 else 0
        }))
    
    except Exception as e:
        logger.error(f"Erro ao listar histórico: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        db.close()


# ==============================================================================
# ENDPOINT: Confirmar Match
# ==============================================================================

@router.post("/confirmar-match")
async def confirmar_match(
    request: ConfirmarMatchRequest,
    auth = Depends(get_current_user_and_tenant)
):
    """
    **Confirmar match entre venda PDV e NSU Stone**
    
    Vincula NSU da Stone à venda do PDV.
    Se aplicar_correcoes=True, atualiza dados do PDV com dados da Stone.
    
    Move para histórico após confirmação.
    """
    user, tenant_id = auth
    db = next(get_session())
    
    try:
        # Buscar venda
        venda = db.query(Venda).filter(
            Venda.id == request.venda_id,
            Venda.tenant_id == tenant_id
        ).first()
        
        if not venda:
            raise HTTPException(status_code=404, detail="Venda não encontrada")
        
        # Buscar pagamento cartão da venda
        pagamento = next((p for p in venda.pagamentos if p.forma_pagamento in ['debito', 'credito']), None)
        
        if not pagamento:
            raise HTTPException(status_code=400, detail="Venda não possui pagamento em cartão")
        
        # Vincular NSU
        pagamento.nsu_cartao = request.nsu_stone
        
        # Marcar como conciliada
        venda.conciliado_vendas = True
        venda.conciliado_vendas_em = datetime.utcnow()
        
        db.commit()
        
        return JSONResponse(content=serialize_for_json({
            'success': True,
            'venda_id': venda.id,
            'numero_venda': venda.numero_venda,
            'nsu': request.nsu_stone,
            'conciliado': True
        }))
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao confirmar match: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        db.close()


# ==============================================================================
# ENDPOINT: Upload Planilha Stone
# ==============================================================================

@router.post("/upload-stone")
async def upload_planilha_stone(
    arquivo: UploadFile = File(...),
    operadora_id: Optional[int] = Form(None),
    auth = Depends(get_current_user_and_tenant)
):
    """
    **Upload planilha Stone**
    
    Salva planilha e detecta duplicação.
    Parseia e armazena NSUs para matching posterior.
    """
    user, tenant_id = auth
    db = next(get_session())
    
    try:
        from .conciliacao_services import processar_upload_conciliacao_vendas
        
        # Ler arquivo
        conteudo = await arquivo.read()
        
        # Processar com salvamento
        resultado = processar_upload_conciliacao_vendas(
            db=db,
            tenant_id=str(tenant_id),
            arquivo_bytes=conteudo,
            nome_arquivo=arquivo.filename,
            operadora_id=operadora_id,
            user_id=user.id
        )
        
        if not resultado['success']:
            raise HTTPException(status_code=400, detail=resultado.get('error'))
        
        return JSONResponse(content=serialize_for_json(resultado))
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao upload Stone: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        db.close()


# ==============================================================================
# ENDPOINT: Atualizar Operadora de Pagamento
# ==============================================================================

class AtualizarOperadoraRequest(BaseModel):
    pagamento_id: int
    operadora_id: int

@router.put("/atualizar-operadora")
async def atualizar_operadora(
    request: AtualizarOperadoraRequest,
    auth = Depends(get_current_user_and_tenant)
):
    """
    Atualiza a operadora de um pagamento.
    Usado para vendas Legacy (sem operadora) para associá-las a uma operadora.
    """
    user, tenant_id = auth
    db = next(get_session())
    
    try:
        from .vendas_models import VendaPagamento
        
        # Buscar pagamento
        pagamento = db.query(VendaPagamento).filter(
            VendaPagamento.id == request.pagamento_id,
            VendaPagamento.tenant_id == tenant_id
        ).first()
        
        if not pagamento:
            raise HTTPException(status_code=404, detail="Pagamento não encontrado")
        
        # Verificar se operadora existe
        operadora = db.query(OperadoraCartao).filter(
            OperadoraCartao.id == request.operadora_id,
            OperadoraCartao.tenant_id == tenant_id
        ).first()
        
        if not operadora:
            raise HTTPException(status_code=404, detail="Operadora não encontrada")
        
        # Atualizar operadora
        pagamento.operadora_id = request.operadora_id
        db.commit()
        
        logger.info(f"[Atualizar Operadora] Pagamento #{pagamento.id} atualizado para operadora {operadora.nome}")
        
        return JSONResponse(content=serialize_for_json({
            'success': True,
            'message': f'Operadora atualizada para {operadora.nome}',
            'pagamento_id': pagamento.id,
            'operadora_id': operadora.id,
            'operadora_nome': operadora.nome
        }))
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao atualizar operadora: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        db.close()
