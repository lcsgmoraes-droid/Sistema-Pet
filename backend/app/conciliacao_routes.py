"""
API Routes para Conciliação de Cartões - FASE 2

Endpoints para gerenciar importação e validação de arquivos de conciliação.

PRINCÍPIOS (RISCOS_E_MITIGACOES_CONCILIACAO.md):
- ✅ Tudo em transação
- ✅ Rollback obrigatório
- ✅ Nenhuma mudança sem log
- ✅ Nunca confiar 100% no arquivo  
- ✅ Sempre permitir reversão
"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date
from pydantic import BaseModel, Field

from .db import get_session
from .auth.dependencies import get_current_user_and_tenant
from .conciliacao_services import (
    importar_arquivo_operadora,
    validar_importacao_cascata,
    processar_conciliacao,
    reverter_conciliacao
)
from .conciliacao_models import (
    AdquirenteTemplate,
    ConciliacaoValidacao,
    ConciliacaoLog,
    ConciliacaoImportacao
)


router = APIRouter(prefix="/conciliacao-vendas", tags=["Conciliação de Cartões"])


# ==============================================================================
# SCHEMAS PYDANTIC
# ==============================================================================

class ImportarArquivoRequest(BaseModel):
    """Schema para importação de arquivo"""
    adquirente_template_id: int = Field(..., description="ID do template para parsear arquivo")
    tipo_importacao: str = Field(
        default="recebimentos_detalhados",
        description="Tipo: recebimentos_detalhados ou pagamentos_lotes"
    )


class ValidarCascataRequest(BaseModel):
    """Schema para validação em cascata"""
    importacao_pagamentos_id: Optional[int] = Field(None, description="ID da importação de pagamentos")
    importacao_recebimentos_id: Optional[int] = Field(None, description="ID da importação de recebimentos")
    data_referencia: date = Field(..., description="Data para validar (AAAA-MM-DD)")
    adquirente: str = Field(..., description="Nome da operadora (Stone, Cielo, etc)")


class ProcessarConciliacaoRequest(BaseModel):
    """Schema para processar conciliação"""
    confirmacao_usuario: bool = Field(
        default=False,
        description="Se True, usuário confirma explicitamente (requerido para confiança MEDIA/BAIXA)"
    )
    justificativa: Optional[str] = Field(
        None,
        description="Justificativa (obrigatória para confiança BAIXA)"
    )


class ReverterConciliacaoRequest(BaseModel):
    """Schema para reverter conciliação"""
    motivo: str = Field(..., description="Motivo da reversão (obrigatório)")


# ==============================================================================
# ENDPOINTS - IMPORTAÇÃO
# ==============================================================================

@router.post("/upload-operadora")
async def upload_arquivo_operadora(
    arquivo: UploadFile = File(..., description="Arquivo CSV da operadora"),
    adquirente_template_id: int = Query(..., description="ID do template"),
    tipo_importacao: str = Query(
        default="recebimentos_detalhados",
        description="Tipo de importação"
    ),
    auth = Depends(get_current_user_and_tenant)
):
    """
    **Importa arquivo CSV da operadora (Stone, Cielo, Rede, etc).**
    
    ⚠️ **IMPORTANTE**: Esta função **APENAS IMPORTA** dados.
    - NÃO altera status de ContaReceber para 'recebido'
    - NÃO cria movimentações bancárias
    - NÃO realiza financeiramente
    
    Apenas atualiza campos `*_real` e `status_conciliacao`.
    
    **Validações aplicadas:**
    - ✅ Detecta arquivo duplicado (hash MD5)
    - ✅ Valida cada linha do CSV
    - ✅ Detecta NSU duplicado
    - ✅ Valida datas e valores
    - ✅ Cria log completo de auditoria
    
    **Retorna:**
    ```json
    {
        "success": true,
        "importacao_id": 123,
        "arquivo_evidencia_id": 456,
        "total_linhas": 150,
        "parcelas_confirmadas": 140,
        "parcelas_orfas": 10,
        "erros": [...],
        "periodo": {
            "inicio": "2026-02-01",
            "fim": "2026-02-28"
        }
    }
    ```
    """
    user, tenant_id = auth
    db = next(get_session())
    
    try:
        # Ler arquivo
        conteudo = await arquivo.read()
        
        if not conteudo:
            raise HTTPException(status_code=400, detail="Arquivo vazio")
        
        # Importar
        resultado = importar_arquivo_operadora(
            db=db,
            arquivo_bytes=conteudo,
            nome_arquivo=arquivo.filename,
            adquirente_template_id=adquirente_template_id,
            tenant_id=str(tenant_id),
            user_id=user.id,
            tipo_importacao=tipo_importacao
        )
        
        if not resultado['success']:
            raise HTTPException(status_code=400, detail=resultado.get('error'))
        
        return JSONResponse(content=resultado, status_code=201)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar arquivo: {str(e)}")
    finally:
        db.close()


# ==============================================================================
# ENDPOINTS - VALIDAÇÃO
# ==============================================================================

@router.post("/validar")
async def validar_cascata(
    request: ValidarCascataRequest,
    auth = Depends(get_current_user_and_tenant)
):
    """
    **Valida importação em cascata: OFX → Pagamentos → Recebimentos.**
    
    Compara totais de 3 fontes:
    1. **OFX** (extrato bancário) - opcional
    2. **Pagamentos** (arquivo da operadora)
    3. **Recebimentos** (ContaReceber do PDV)
    
    **Sistema NUNCA bloqueia:**
    - Confiança ALTA → Processa automaticamente
    - Confiança MEDIA → Requer confirmação simples
    - Confiança BAIXA → Requer confirmação + justificativa
    
    **Retorna:**
    ```json
    {
        "success": true,
        "validacao_id": 789,
        "confianca": "ALTA",
        "pode_processar": true,
        "requer_confirmacao": false,
        "totais": {
            "pagamentos": 5000.00,
            "recebimentos": 5000.00
        },
        "diferencas": {
            "pagamentos_vs_recebimentos": 0.00,
            "percentual": 0.00
        },
        "alertas": []
    }
    ```
    """
    user, tenant_id = auth
    db = next(get_session())
    
    try:
        resultado = validar_importacao_cascata(
            db=db,
            importacao_pagamentos_id=request.importacao_pagamentos_id,
            importacao_recebimentos_id=request.importacao_recebimentos_id,
            data_referencia=request.data_referencia,
            adquirente=request.adquirente,
            tenant_id=str(tenant_id),
            user_id=user.id
        )
        
        if not resultado['success']:
            raise HTTPException(status_code=400, detail=resultado.get('error'))
        
        return JSONResponse(content=resultado, status_code=201)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao validar: {str(e)}")
    finally:
        db.close()


@router.get("/validacao/{validacao_id}")
async def get_validacao(
    validacao_id: int,
    auth = Depends(get_current_user_and_tenant)
):
    """
    **Retorna detalhes de uma validação.**
    
    Inclui:
    - Totais e diferenças
    - Confiança e status
    - Alertas gerados
    - Quantidades (parcelas confirmadas, órfãs)
    """
    user, tenant_id = auth
    db = next(get_session())
    
    try:
        validacao = db.query(ConciliacaoValidacao).filter(
            ConciliacaoValidacao.id == validacao_id,
            ConciliacaoValidacao.tenant_id == str(tenant_id)
        ).first()
        
        if not validacao:
            raise HTTPException(status_code=404, detail="Validação não encontrada")
        
        return JSONResponse(content=validacao.to_dict())
    
    finally:
        db.close()


# ==============================================================================
# ENDPOINTS - PROCESSAMENTO
# ==============================================================================

@router.post("/processar/{validacao_id}")
async def processar_validacao(
    validacao_id: int,
    request: ProcessarConciliacaoRequest,
    auth = Depends(get_current_user_and_tenant)
):
    """
    **Processa conciliação APÓS validação aprovada.**
    
    ⚠️ **CRÍTICO**: Aqui SIM pode alterar `status_conciliacao`.
    MAS SOMENTE se validação foi confirmada.
    
    **Requisitos:**
    - Validação com `pode_processar = True`
    - Se `requer_confirmacao = True`: `confirmacao_usuario = True` obrigatório
    - Se `confianca = BAIXA`: `justificativa` obrigatória
    
    **Retorna:**
    ```json
    {
        "success": true,
        "parcelas_liquidadas": 50,
        "valor_total_liquidado": 5000.00
    }
    ```
    """
    user, tenant_id = auth
    db = next(get_session())
    
    try:
        resultado = processar_conciliacao(
            db=db,
            validacao_id=validacao_id,
            tenant_id=str(tenant_id),
            user_id=user.id,
            confirmacao_usuario=request.confirmacao_usuario,
            justificativa=request.justificativa
        )
        
        if not resultado['success']:
            # Se requer confirmação, retornar 400 mas com flag
            if resultado.get('requer_confirmacao'):
                raise HTTPException(
                    status_code=400,
                    detail={
                        'error': resultado.get('error'),
                        'requer_confirmacao': True,
                        'confianca': resultado.get('confianca')
                    }
                )
            
            raise HTTPException(status_code=400, detail=resultado.get('error'))
        
        return JSONResponse(content=resultado)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar: {str(e)}")
    finally:
        db.close()


@router.post("/reverter/{validacao_id}")
async def reverter_validacao(
    validacao_id: int,
    request: ReverterConciliacaoRequest,
    auth = Depends(get_current_user_and_tenant)
):
    """
    **Reverte conciliação já processada.**
    
    PRINCÍPIO: Sempre permitir reversão.
    
    **Requer:**
    - Motivo da reversão (obrigatório)
    
    **Efeito:**
    - Parcelas voltam para `status_conciliacao = 'confirmada_operadora'`
    - Validação marcada como `status_validacao = 'divergente'`
    - Log completo criado com motivo
    - Versão incrementada
    
    **Retorna:**
    ```json
    {
        "success": true,
        "parcelas_revertidas": 50
    }
    ```
    """
    user, tenant_id = auth
    db = next(get_session())
    
    try:
        resultado = reverter_conciliacao(
            db=db,
            validacao_id=validacao_id,
            tenant_id=str(tenant_id),
            user_id=user.id,
            motivo=request.motivo
        )
        
        if not resultado['success']:
            raise HTTPException(status_code=400, detail=resultado.get('error'))
        
        return JSONResponse(content=resultado)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao reverter: {str(e)}")
    finally:
        db.close()


# ==============================================================================
# ENDPOINTS - CONSULTA
# ==============================================================================

@router.get("/validacoes")
async def listar_validacoes(
    data_inicio: Optional[date] = Query(None, description="Filtrar por data início"),
    data_fim: Optional[date] = Query(None, description="Filtrar por data fim"),
    adquirente: Optional[str] = Query(None, description="Filtrar por operadora"),
    status: Optional[str] = Query(None, description="Filtrar por status"),
    limit: int = Query(50, le=200, description="Limite de resultados"),
    offset: int = Query(0, description="Offset para paginação"),
    auth = Depends(get_current_user_and_tenant)
):
    """
    **Lista validações do tenant.**
    
    Suporta filtros por:
    - Data (início/fim)
    - Adquirente
    - Status
    
    Paginado (limit/offset).
    """
    user, tenant_id = auth
    db = next(get_session())
    
    try:
        query = db.query(ConciliacaoValidacao).filter(
            ConciliacaoValidacao.tenant_id == str(tenant_id)
        )
        
        # Aplicar filtros
        if data_inicio:
            query = query.filter(ConciliacaoValidacao.data_referencia >= data_inicio)
        
        if data_fim:
            query = query.filter(ConciliacaoValidacao.data_referencia <= data_fim)
        
        if adquirente:
            query = query.filter(ConciliacaoValidacao.adquirente == adquirente)
        
        if status:
            query = query.filter(ConciliacaoValidacao.status_validacao == status)
        
        # Total
        total = query.count()
        
        # Paginação
        validacoes = query.order_by(
            ConciliacaoValidacao.data_referencia.desc()
        ).limit(limit).offset(offset).all()
        
        return JSONResponse(content={
            'total': total,
            'limit': limit,
            'offset': offset,
            'validacoes': [v.to_dict() for v in validacoes]
        })
    
    finally:
        db.close()


@router.get("/validacao/{validacao_id}/historico")
async def get_historico_validacao(
    validacao_id: int,
    auth = Depends(get_current_user_and_tenant)
):
    """
    **Retorna histórico completo de uma validação.**
    
    Mostra todas as ações:
    - Criação
    - Processamentos
    - Reversões
    - Recálculos (se houver)
    
    Cada entrada mostra:
    - Versão
    - Data/hora
    - Usuário
    - Ação
    - Quantidades
    - Diferenças (snapshot antes/depois)
    - Motivo (para reversões)
    """
    user, tenant_id = auth
    db = next(get_session())
    
    try:
        # Verificar se validação existe
        validacao = db.query(ConciliacaoValidacao).filter(
            ConciliacaoValidacao.id == validacao_id,
            ConciliacaoValidacao.tenant_id == str(tenant_id)
        ).first()
        
        if not validacao:
            raise HTTPException(status_code=404, detail="Validação não encontrada")
        
        # Buscar logs
        logs = db.query(ConciliacaoLog).filter(
            ConciliacaoLog.conciliacao_validacao_id == validacao_id
        ).order_by(ConciliacaoLog.versao_conciliacao).all()
        
        return JSONResponse(content={
            'validacao_id': validacao_id,
            'versao_atual': validacao.parcelas_confirmadas or 1,
            'historico': [log.to_dict() for log in logs]
        })
    
    finally:
        db.close()


@router.get("/importacoes")
async def listar_importacoes(
    tipo: Optional[str] = Query(None, description="Filtrar por tipo"),
    status: Optional[str] = Query(None, description="Filtrar por status"),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    auth = Depends(get_current_user_and_tenant)
):
    """
    **Lista importações de arquivos.**
    
    Mostra:
    - Nome do arquivo
    - Tipo (recebimentos, pagamentos)
    - Status (processando, processada, erro)
    - Totais
    - Período
    """
    user, tenant_id = auth
    db = next(get_session())
    
    try:
        query = db.query(ConciliacaoImportacao).filter(
            ConciliacaoImportacao.tenant_id == str(tenant_id)
        )
        
        if tipo:
            query = query.filter(ConciliacaoImportacao.tipo_importacao == tipo)
        
        if status:
            query = query.filter(ConciliacaoImportacao.status_importacao == status)
        
        total = query.count()
        
        importacoes = query.order_by(
            ConciliacaoImportacao.criado_em.desc()
        ).limit(limit).offset(offset).all()
        
        return JSONResponse(content={
            'total': total,
            'limit': limit,
            'offset': offset,
            'importacoes': [imp.to_dict() for imp in importacoes]
        })
    
    finally:
        db.close()


# ==============================================================================
# ENDPOINTS - TEMPLATES
# ==============================================================================

@router.get("/templates")
async def listar_templates(
    ativo: Optional[bool] = Query(None, description="Filtrar por ativos"),
    auth = Depends(get_current_user_and_tenant)
):
    """
    **Lista templates de adquirentes disponíveis.**
    
    Templates definem como parsear CSVs de diferentes operadoras.
    """
    user, tenant_id = auth
    db = next(get_session())
    
    try:
        query = db.query(AdquirenteTemplate).filter(
            AdquirenteTemplate.tenant_id == str(tenant_id)
        )
        
        if ativo is not None:
            query = query.filter(AdquirenteTemplate.ativo == ativo)
        
        templates = query.order_by(AdquirenteTemplate.nome).all()
        
        return JSONResponse(content={
            'templates': [t.to_dict() for t in templates]
        })
    
    finally:
        db.close()


# ==============================================================================
# NOVA ARQUITETURA: ENDPOINTS 3 ABAS
# ==============================================================================

class ConciliarVendasRequest(BaseModel):
    """Schema para Aba 1: Conciliação de Vendas"""
    vendas_stone: List[dict] = Field(..., description="Dados da planilha Stone vendas")
    operadora_id: Optional[int] = Field(None, description="ID da operadora para filtrar vendas")


class ValidarRecebimentosRequest(BaseModel):
    """Schema para Aba 2: Validação de Recebimentos"""
    recebimentos_detalhados: List[dict] = Field(..., description="Recebimentos 1 a 1")
    recibo_lote: List[dict] = Field(..., description="Lotes agrupados")
    ofx_creditos: List[dict] = Field(..., description="Extratos bancários")
    operadora: Optional[str] = Field(None, description="Operadora selecionada (ex: Stone)")
    
    # Campos opcionais para histórico
    data_referencia: Optional[str] = Field(None, description="Data conciliada (YYYY-MM-DD)")
    arquivos_info: Optional[List[dict]] = Field(default=[], description="Metadados dos arquivos: [{nome, tamanho, tipo}]")
    historico_id: Optional[int] = Field(None, description="ID do histórico existente (se houver)")


def extrair_data_referencia_recebimentos(recebimentos: List[dict]) -> Optional[str]:
    """Extrai data mais comum dos recebimentos para usar como data de referência"""
    from collections import Counter
    from datetime import datetime
    
    datas = []
    for rec in recebimentos:
        # Tentar vários campos possíveis
        for campo in ['data', 'data_recebimento', 'data_pagamento', 'Data de Pagamento']:
            if campo in rec and rec[campo]:
                try:
                    # Tentar parsear string de data
                    if isinstance(rec[campo], str):
                        # Tentar vários formatos
                        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d']:
                            try:
                                dt = datetime.strptime(rec[campo], fmt)
                                datas.append(dt.date().isoformat())
                                break
                            except:
                                continue
                    break
                except:
                    continue
    
    if not datas:
        return None
    
    # Retornar data mais comum (moda)
    counter = Counter(datas)
    return counter.most_common(1)[0][0]


class AmarrarRecebimentosRequest(BaseModel):
    """Schema para Aba 3: Amarração"""
    data_recebimento: str = Field(..., description="Data dos recebimentos (YYYY-MM-DD)")
    operadora: Optional[str] = Field(None, description="Operadora selecionada (ex: Stone)")


@router.post("/aba1/conciliar-vendas")
async def conciliar_vendas_endpoint(
    request: ConciliarVendasRequest,
    auth = Depends(get_current_user_and_tenant)
):
    """
    **ABA 1: Conciliação de Vendas (PDV vs Stone)** - VERSÃO LEGACY
    
    ⚠️ Processamento em memória (não salva arquivo).
    Use /aba1/upload-e-conciliar para persistência completa.
    """
    from .conciliacao_services import conciliar_vendas_stone
    
    user, tenant_id = auth
    db = next(get_session())
    
    try:
        resultado = conciliar_vendas_stone(
            db=db,
            tenant_id=str(tenant_id),
            vendas_stone=request.vendas_stone,
            user_id=user.id,
            operadora_id=request.operadora_id
        )
        
        if not resultado['success']:
            raise HTTPException(status_code=400, detail=resultado.get('error'))
        
        return JSONResponse(content=resultado)
    
    finally:
        db.close()


@router.post("/aba1/upload-e-conciliar")
async def upload_conciliar_vendas(
    arquivo: UploadFile = File(..., description="CSV da operadora"),
    operadora_id: Optional[int] = Form(None),
    auth = Depends(get_current_user_and_tenant)
):
    """
    **ABA 1: Upload + Conciliação com Persistência**
    
    Fluxo completo:
    1. ✅ Salva arquivo (arquivos_evidencia)
    2. ✅ Cria importação (conciliacao_importacoes)  
    3. ✅ Processa conciliação
    4. ✅ Marca vendas conferidas
    5. ✅ Retorna histórico persistido
    
    Resultado salvo permanentemente no banco.
    """
    from .conciliacao_services import processar_upload_conciliacao_vendas
    from .conciliacao_helpers import serialize_for_json
    
    user, tenant_id = auth
    db = next(get_session())
    
    try:
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
        
        # Serializar datas e Decimals para JSON
        resultado_json = serialize_for_json(resultado)
        
        return JSONResponse(content=resultado_json)
    
    finally:
        db.close()


@router.get("/aba1/historico")
async def listar_historico_conciliacoes(
    operadora_id: Optional[int] = None,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    auth = Depends(get_current_user_and_tenant)
):
    """
    Lista histórico de importações de conciliação.
    
    Filtros:
    - operadora_id: Filtrar por operadora
    - data_inicio/data_fim: Período (YYYY-MM-DD)
    
    Retorna lista de importações anteriores com resumo.
    """
    from .conciliacao_models import ConciliacaoImportacao, ArquivoEvidencia
    from datetime import datetime as dt
    
    user, tenant_id = auth
    db = next(get_session())
    
    try:
        query = db.query(ConciliacaoImportacao).filter(
            ConciliacaoImportacao.tenant_id == tenant_id,
            ConciliacaoImportacao.tipo_importacao == 'vendas'
        )
        
        if data_inicio:
            query = query.filter(ConciliacaoImportacao.data_referencia >= dt.fromisoformat(data_inicio).date())
        if data_fim:
            query = query.filter(ConciliacaoImportacao.data_referencia <= dt.fromisoformat(data_fim).date())
        
        importacoes = query.order_by(ConciliacaoImportacao.criado_em.desc()).all()
        
        resultado = []
        for imp in importacoes:
            resultado.append({
                'id': imp.id,
                'arquivo': imp.arquivo.nome_original if imp.arquivo else None,
                'data_referencia': imp.data_referencia.isoformat() if imp.data_referencia else None,
                'total_registros': imp.total_registros,
                'status': imp.status_importacao,
                'resumo': imp.resumo,
                'criado_em': imp.criado_em.isoformat() if imp.criado_em else None
            })
        
        return JSONResponse(content={'success': True, 'importacoes': resultado})
    
    finally:
        db.close()


@router.get("/aba1/vendas-status")
async def listar_vendas_com_status(
    status: Optional[str] = Query(None, description="conferidas, pendentes, todas"),
    operadora_id: Optional[int] = None,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    auth = Depends(get_current_user_and_tenant)
):
    """
    Lista vendas com status de conciliação.
    
    Filtros:
    - status: conferidas (com NSU validado) | pendentes (sem NSU ou não validadas) | todas
    - operadora_id: Operadora específica
    - data_inicio/data_fim: Período
    
    Retorna vendas com indicador visual de status.
    """
    from .vendas_models import Venda, VendaPagamento
    from datetime import datetime as dt
    
    user, tenant_id = auth
    db = next(get_session())
    
    try:
        query = db.query(Venda).filter(
            Venda.tenant_id == tenant_id,
            Venda.status == 'finalizada'
        )
        
        if status == 'conferidas':
            query = query.filter(Venda.conciliado_vendas == True)
        elif status == 'pendentes':
            query = query.filter(
                (Venda.conciliado_vendas == False) | 
                (Venda.conciliado_vendas.is_(None))
            )
        
        if data_inicio:
            query = query.filter(Venda.data_venda >= dt.fromisoformat(data_inicio))
        if data_fim:
            query = query.filter(Venda.data_venda <= dt.fromisoformat(data_fim))
        
        vendas = query.order_by(Venda.data_venda.desc()).limit(100).all()
        
        resultado = []
        for venda in vendas:
            # Pegar NSU do primeiro pagamento com cartão
            nsu = None
            operadora = None
            for pag in venda.pagamentos:
                if pag.forma_pagamento in ['credito', 'debito'] and pag.nsu_cartao:
                    nsu = pag.nsu_cartao
                    operadora = pag.operadora_id
                    break
            
            resultado.append({
                'id': venda.id,
                'numero_venda': venda.numero_venda,
                'data_venda': venda.data_venda.isoformat() if venda.data_venda else None,
                'valor_total': float(venda.valor_total),
                'nsu': nsu,
                'operadora_id': operadora,
                'status_conciliacao': 'conferida' if venda.conciliado_vendas else 'pendente',
                'conciliado_em': venda.conciliado_vendas_em.isoformat() if venda.conciliado_vendas_em else None
            })
        
        return JSONResponse(content={'success': True, 'vendas': resultado})
    
    finally:
        db.close()


@router.post("/aba2/validar-recebimentos")
async def validar_recebimentos_endpoint(
    request: ValidarRecebimentosRequest,
    auth = Depends(get_current_user_and_tenant)
):
    """
    **ABA 2: Validação de Recebimentos (cascata 3 arquivos)**
    
    Valida que dinheiro entrou na conta:
    1. Soma recebimentos detalhados
    2. Confere com recibo_lote
    3. Confere com OFX
    
    **NÃO conhece vendas!**
    
    **HISTÓRICO AUTOMÁTICO:**
    - Detecta operadora automaticamente
    - Registra histórico de conciliação
    - Previne reprocessamento duplicado
    
    Retorna:
    - validado: True/False (se os 3 arquivos batem)
    - recebimentos_salvos: Quantos foram salvos
    - divergencias: Lista de diferenças encontradas
    - historico_id: ID do registro de histórico
    - operadora_detectada: Nome da operadora identificada
    - ja_conciliado: Se essa data/operadora já foi conciliada antes
    """
    from .conciliacao_services import validar_recebimentos_cascata_v2
    from .conciliacao_operadora_detector import detectar_operadora_automatico
    from .conciliacao_models import HistoricoConciliacao
    from datetime import datetime
    from sqlalchemy import and_
    
    user, tenant_id = auth
    db = next(get_session())
    
    try:
        # ========================================
        # 1. DETECTAR OPERADORA AUTOMATICAMENTE
        # ========================================
        operadora_detectada = "Stone"  # Default
        confianca_deteccao = 0.5
        
        # Tentar detectar pela estrutura dos dados
        if request.recebimentos_detalhados:
            primeiro_rec = request.recebimentos_detalhados[0]
            
            # Simular conteúdo CSV para detecção
            campos_str = ";".join(str(k) for k in primeiro_rec.keys())
            
            from .conciliacao_operadora_detector import detectar_operadora_csv
            deteccao = detectar_operadora_csv(campos_str)
            
            if deteccao:
                operadora_detectada = deteccao['operadora']
                confianca_deteccao = deteccao['confianca']
        
        # Se arquivos_info fornecido, usar nome do arquivo também
        if request.arquivos_info:
            for arq_info in request.arquivos_info:
                nome_arquivo = arq_info.get('nome', '')
                deteccao_arquivo = detectar_operadora_csv("", nome_arquivo)
                if deteccao_arquivo and deteccao_arquivo['confianca'] > confianca_deteccao:
                    operadora_detectada = deteccao_arquivo['operadora']
                    confianca_deteccao = deteccao_arquivo['confianca']
        
        # ========================================
        # 2. EXTRAIR DATA DE REFERÊNCIA
        # ========================================
        data_ref = request.data_referencia
        if not data_ref:
            # Tentar extrair dos recebimentos
            data_ref = extrair_data_referencia_recebimentos(request.recebimentos_detalhados)
        
        if not data_ref:
            raise HTTPException(
                status_code=400,
                detail="Não foi possível identificar a data de referência. Por favor, informe manualmente."
            )
        
        data_ref_obj = datetime.strptime(data_ref, '%Y-%m-%d').date()

        operadora_final = request.operadora or operadora_detectada
        
        # ========================================
        # 3. VERIFICAR SE JÁ FOI CONCILIADO
        # ========================================
        historico_existente = db.query(HistoricoConciliacao).filter(
            and_(
                HistoricoConciliacao.tenant_id == tenant_id,
                HistoricoConciliacao.data_referencia == data_ref_obj,
                HistoricoConciliacao.operadora == operadora_final,
                HistoricoConciliacao.status != 'cancelada'
            )
        ).first()
        
        ja_conciliado = False
        aviso_reprocessamento = None
        
        if historico_existente:
            if historico_existente.status == 'concluida' and historico_existente.aba2_concluida:
                ja_conciliado = True
                aviso_reprocessamento = {
                    'mensagem': f"⚠️ ATENÇÃO: Data {data_ref} da operadora {operadora_final} já foi conciliada em {historico_existente.aba2_concluida_em.strftime('%d/%m/%Y %H:%M')}. Você está reprocessando!",
                    'conciliada_em': historico_existente.aba2_concluida_em.isoformat(),
                    'usuario_anterior': historico_existente.usuario_responsavel,
                    'pode_continuar': True
                }
        
        # ========================================
        # 4. EXECUTAR VALIDAÇÃO
        # ========================================
        resultado = validar_recebimentos_cascata_v2(
            db=db,
            tenant_id=str(tenant_id),
            recebimentos_detalhados=request.recebimentos_detalhados,
            recibo_lote=request.recibo_lote,
            ofx_creditos=request.ofx_creditos,
            user_id=user.id,
            operadora=operadora_final
        )
        
        if not resultado['success']:
            raise HTTPException(status_code=400, detail=resultado.get('error'))
        
        # ========================================
        # 5. REGISTRAR/ATUALIZAR HISTÓRICO
        # ========================================
        if historico_existente:
            # Atualizar existente
            historico = historico_existente
            historico.aba2_concluida = True
            historico.aba2_concluida_em = datetime.now()
            historico.divergencias_encontradas = len(resultado.get('divergencias', []))
            historico.divergencias_aceitas = True  # Se chegou aqui, usuário aceitou
            
            # Atualizar totais
            if not historico.totais:
                historico.totais = {}
            historico.totais['recebimentos'] = {
                'valor_total': float(resultado.get('valor_total_recebimentos', 0)),
                'quantidade': resultado.get('recebimentos_salvos', 0)
            }
            
            # Atualizar arquivos se fornecido
            if request.arquivos_info:
                historico.arquivos_processados = request.arquivos_info
            
        else:
            # Criar novo registro
            usuario = user.email if hasattr(user, 'email') else user.username
            
            historico = HistoricoConciliacao(
                tenant_id=tenant_id,
                data_referencia=data_ref_obj,
                operadora=operadora_final,
                status='em_andamento',
                aba2_concluida=True,
                aba2_concluida_em=datetime.now(),
                divergencias_encontradas=len(resultado.get('divergencias', [])),
                divergencias_aceitas=True,
                arquivos_processados=request.arquivos_info or [],
                totais={
                    'recebimentos': {
                        'valor_total': float(resultado.get('valor_total_recebimentos', 0)),
                        'quantidade': resultado.get('recebimentos_salvos', 0)
                    }
                },
                usuario_responsavel=usuario
            )
            
            db.add(historico)
        
        db.commit()
        db.refresh(historico)
        
        # ========================================
        # 6. RETORNAR RESULTADO COMPLETO
        # ========================================
        resultado['historico_id'] = historico.id
        resultado['operadora_detectada'] = operadora_detectada
        resultado['operadora_utilizada'] = operadora_final
        resultado['confianca_deteccao'] = confianca_deteccao
        resultado['data_referencia'] = data_ref
        resultado['ja_conciliado'] = ja_conciliado
        
        if aviso_reprocessamento:
            resultado['aviso_reprocessamento'] = aviso_reprocessamento
        
        return JSONResponse(content=resultado)
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao processar validação: {str(e)}")
    finally:
        db.close()


@router.post("/aba3/amarrar-automatico")
async def amarrar_recebimentos_endpoint(
    request: AmarrarRecebimentosRequest,
    auth = Depends(get_current_user_and_tenant)
):
    """
    **ABA 3: Amarração Automática (Venda ↔ Recebimento)**
    
    Vincula recebimentos (validados Aba 2) às vendas (conferidas Aba 1)
    e BAIXA Contas a Receber.
    
    **98% automático** se Aba 1 foi bem feita!
    
    **IDEMPOTENTE:** Se rodar 2x, não duplica baixa.
    
    **TRANSPARENTE:** Mostra quantas parcelas serão baixadas.
    
    Retorna:
    - amarrados: Quantidade amarrada automaticamente
    - orfaos: Recebimentos sem venda (precisa resolver na Aba 1)
    - parcelas_liquidadas: Quantas parcelas foram baixadas
    - valor_total_liquidado: Valor total baixado
    - taxa_amarracao_automatica: % de sucesso (98% = saudável)
    - alerta_saude: OK ou CRÍTICO (< 90%)
    """
    from .conciliacao_services import amarrar_recebimentos_vendas
    from datetime import datetime
    
    user, tenant_id = auth
    db = next(get_session())
    
    try:
        # Converter string para date
        data_rec = datetime.strptime(request.data_recebimento, '%Y-%m-%d').date()
        
        resultado = amarrar_recebimentos_vendas(
            db=db,
            tenant_id=str(tenant_id),
            data_recebimento=data_rec,
            user_id=user.id,
            operadora=request.operadora
        )
        
        if not resultado['success']:
            raise HTTPException(status_code=400, detail=resultado.get('error'))
        
        return JSONResponse(content=resultado)
    
    finally:
        db.close()


@router.get("/aba3/preview-amarracao")
async def preview_amarracao_endpoint(
    data_recebimento: str = Query(..., description="Data dos recebimentos (YYYY-MM-DD)"),
    operadora: Optional[str] = Query(None, description="Operadora selecionada (ex: Stone)"),
    auth = Depends(get_current_user_and_tenant)
):
    """
    **ABA 3: Preview de Amarração (antes de processar)**
    
    Mostra quantas parcelas serão liquidadas ANTES de executar.
    
    **TRANSPARÊNCIA:** Usuário vê o que vai acontecer.
    
    Retorna:
    - recebimentos_validados: Quantos recebimentos prontos
    - parcelas_a_baixar: Quantas parcelas serão baixadas
    - valor_total: Valor total que será liquidado
    """
    from .conciliacao_models import ConciliacaoRecebimento
    from .vendas_models import Venda
    from .financeiro_models import ContaReceber
    from datetime import datetime
    
    user, tenant_id = auth
    db = next(get_session())
    
    try:
        data_rec = datetime.strptime(data_recebimento, '%Y-%m-%d').date()
        
        # Buscar recebimentos validados e não amarrados
        recebimentos_query = db.query(ConciliacaoRecebimento).filter(
            ConciliacaoRecebimento.tenant_id == str(tenant_id),
            ConciliacaoRecebimento.data_recebimento == data_rec,
            ConciliacaoRecebimento.validado == True,
            ConciliacaoRecebimento.amarrado == False
        )

        if operadora:
            recebimentos_query = recebimentos_query.filter(
                ConciliacaoRecebimento.adquirente == operadora
            )

        recebimentos = recebimentos_query.all()
        
        # Simular amarração (contar parcelas)
        parcelas_count = 0
        valor_total = 0
        
        for rec in recebimentos:
            from .vendas_models import VendaPagamento
            venda_pagamento = db.query(VendaPagamento).filter(
                VendaPagamento.nsu_cartao == rec.nsu
            ).first()
            
            if not venda_pagamento:
                continue
                
            venda = db.query(Venda).filter(
                Venda.tenant_id == str(tenant_id),
                Venda.id == venda_pagamento.venda_id,
                Venda.conciliado_vendas == True
            ).first()
            
            if venda:
                if rec.tipo_recebimento == 'antecipacao':
                    parcelas = db.query(ContaReceber).filter(
                        ContaReceber.tenant_id == str(tenant_id),
                        ContaReceber.venda_id == venda.id,
                        ContaReceber.status != 'recebido',
                        ContaReceber.conciliacao_recebimento_id.is_(None)
                    ).count()
                    parcelas_count += parcelas
                else:
                    parcela = db.query(ContaReceber).filter(
                        ContaReceber.tenant_id == str(tenant_id),
                        ContaReceber.venda_id == venda.id,
                        ContaReceber.numero_parcela == rec.parcela_numero,
                        ContaReceber.status != 'recebido',
                        ContaReceber.conciliacao_recebimento_id.is_(None)
                    ).first()
                    if parcela:
                        parcelas_count += 1
                        valor_total += float(parcela.valor_original)
        
        return JSONResponse(content={
            'recebimentos_validados': len(recebimentos),
            'parcelas_a_baixar': parcelas_count,
            'valor_total': valor_total
        })
    
    finally:
        db.close()
