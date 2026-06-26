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

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional
from datetime import date
from pydantic import BaseModel, Field

from .db import get_session
from .auth.dependencies import get_current_user_and_tenant
from .conciliacao_services import (
    importar_arquivo_operadora,
    validar_importacao_cascata,
    processar_conciliacao,
    reverter_conciliacao,
)
from .conciliacao_models import (
    AdquirenteTemplate,
    ConciliacaoValidacao,
    ConciliacaoLog,
    ConciliacaoImportacao,
)
from .conciliacao_abas_routes import router as conciliacao_abas_router


router = APIRouter(prefix="/conciliacao-vendas", tags=["Conciliação de Cartões"])


# ==============================================================================
# SCHEMAS PYDANTIC
# ==============================================================================


class ImportarArquivoRequest(BaseModel):
    """Schema para importação de arquivo"""

    adquirente_template_id: int = Field(
        ..., description="ID do template para parsear arquivo"
    )
    tipo_importacao: str = Field(
        default="recebimentos_detalhados",
        description="Tipo: recebimentos_detalhados ou pagamentos_lotes",
    )


class ValidarCascataRequest(BaseModel):
    """Schema para validação em cascata"""

    importacao_pagamentos_id: Optional[int] = Field(
        None, description="ID da importação de pagamentos"
    )
    importacao_recebimentos_id: Optional[int] = Field(
        None, description="ID da importação de recebimentos"
    )
    data_referencia: date = Field(..., description="Data para validar (AAAA-MM-DD)")
    adquirente: str = Field(..., description="Nome da operadora (Stone, Cielo, etc)")


class ProcessarConciliacaoRequest(BaseModel):
    """Schema para processar conciliação"""

    confirmacao_usuario: bool = Field(
        default=False,
        description="Se True, usuário confirma explicitamente (requerido para confiança MEDIA/BAIXA)",
    )
    justificativa: Optional[str] = Field(
        None, description="Justificativa (obrigatória para confiança BAIXA)"
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
        default="recebimentos_detalhados", description="Tipo de importação"
    ),
    auth=Depends(get_current_user_and_tenant),
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
            tipo_importacao=tipo_importacao,
        )

        if not resultado["success"]:
            raise HTTPException(status_code=400, detail=resultado.get("error"))

        return JSONResponse(content=resultado, status_code=201)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro ao processar arquivo: {str(e)}"
        )
    finally:
        db.close()


# ==============================================================================
# ENDPOINTS - VALIDAÇÃO
# ==============================================================================


@router.post("/validar")
async def validar_cascata(
    request: ValidarCascataRequest, auth=Depends(get_current_user_and_tenant)
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
            user_id=user.id,
        )

        if not resultado["success"]:
            raise HTTPException(status_code=400, detail=resultado.get("error"))

        return JSONResponse(content=resultado, status_code=201)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao validar: {str(e)}")
    finally:
        db.close()


@router.get("/validacao/{validacao_id}")
async def get_validacao(validacao_id: int, auth=Depends(get_current_user_and_tenant)):
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
        validacao = (
            db.query(ConciliacaoValidacao)
            .filter(
                ConciliacaoValidacao.id == validacao_id,
                ConciliacaoValidacao.tenant_id == str(tenant_id),
            )
            .first()
        )

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
    auth=Depends(get_current_user_and_tenant),
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
            justificativa=request.justificativa,
        )

        if not resultado["success"]:
            # Se requer confirmação, retornar 400 mas com flag
            if resultado.get("requer_confirmacao"):
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": resultado.get("error"),
                        "requer_confirmacao": True,
                        "confianca": resultado.get("confianca"),
                    },
                )

            raise HTTPException(status_code=400, detail=resultado.get("error"))

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
    auth=Depends(get_current_user_and_tenant),
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
            motivo=request.motivo,
        )

        if not resultado["success"]:
            raise HTTPException(status_code=400, detail=resultado.get("error"))

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
    auth=Depends(get_current_user_and_tenant),
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
        validacoes = (
            query.order_by(ConciliacaoValidacao.data_referencia.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

        return JSONResponse(
            content={
                "total": total,
                "limit": limit,
                "offset": offset,
                "validacoes": [v.to_dict() for v in validacoes],
            }
        )

    finally:
        db.close()


@router.get("/validacao/{validacao_id}/historico")
async def get_historico_validacao(
    validacao_id: int, auth=Depends(get_current_user_and_tenant)
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
        validacao = (
            db.query(ConciliacaoValidacao)
            .filter(
                ConciliacaoValidacao.id == validacao_id,
                ConciliacaoValidacao.tenant_id == str(tenant_id),
            )
            .first()
        )

        if not validacao:
            raise HTTPException(status_code=404, detail="Validação não encontrada")

        # Buscar logs
        logs = (
            db.query(ConciliacaoLog)
            .filter(ConciliacaoLog.conciliacao_validacao_id == validacao_id)
            .order_by(ConciliacaoLog.versao_conciliacao)
            .all()
        )

        return JSONResponse(
            content={
                "validacao_id": validacao_id,
                "versao_atual": validacao.parcelas_confirmadas or 1,
                "historico": [log.to_dict() for log in logs],
            }
        )

    finally:
        db.close()


@router.get("/importacoes")
async def listar_importacoes(
    tipo: Optional[str] = Query(None, description="Filtrar por tipo"),
    status: Optional[str] = Query(None, description="Filtrar por status"),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    auth=Depends(get_current_user_and_tenant),
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

        importacoes = (
            query.order_by(ConciliacaoImportacao.criado_em.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

        return JSONResponse(
            content={
                "total": total,
                "limit": limit,
                "offset": offset,
                "importacoes": [imp.to_dict() for imp in importacoes],
            }
        )

    finally:
        db.close()


# ==============================================================================
# ENDPOINTS - TEMPLATES
# ==============================================================================


@router.get("/templates")
async def listar_templates(
    ativo: Optional[bool] = Query(None, description="Filtrar por ativos"),
    auth=Depends(get_current_user_and_tenant),
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

        return JSONResponse(content={"templates": [t.to_dict() for t in templates]})

    finally:
        db.close()


router.include_router(conciliacao_abas_router)
