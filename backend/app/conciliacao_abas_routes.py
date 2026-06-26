"""Endpoints das tres abas da conciliacao de cartoes."""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List

from .auth.dependencies import get_current_user_and_tenant
from .db import get_session


router = APIRouter()


# ==============================================================================
# NOVA ARQUITETURA: ENDPOINTS 3 ABAS
# ==============================================================================


class ConciliarVendasRequest(BaseModel):
    """Schema para Aba 1: Conciliação de Vendas"""

    vendas_stone: List[dict] = Field(..., description="Dados da planilha Stone vendas")
    operadora_id: Optional[int] = Field(
        None, description="ID da operadora para filtrar vendas"
    )


class ValidarRecebimentosRequest(BaseModel):
    """Schema para Aba 2: Validação de Recebimentos"""

    recebimentos_detalhados: List[dict] = Field(..., description="Recebimentos 1 a 1")
    recibo_lote: List[dict] = Field(..., description="Lotes agrupados")
    ofx_creditos: List[dict] = Field(..., description="Extratos bancários")
    operadora: Optional[str] = Field(
        None, description="Operadora selecionada (ex: Stone)"
    )

    # Campos opcionais para histórico
    data_referencia: Optional[str] = Field(
        None, description="Data conciliada (YYYY-MM-DD)"
    )
    arquivos_info: Optional[List[dict]] = Field(
        default=[], description="Metadados dos arquivos: [{nome, tamanho, tipo}]"
    )
    historico_id: Optional[int] = Field(
        None, description="ID do histórico existente (se houver)"
    )


def extrair_data_referencia_recebimentos(recebimentos: List[dict]) -> Optional[str]:
    """Extrai data mais comum dos recebimentos para usar como data de referência"""
    from collections import Counter
    from datetime import datetime

    datas = []
    for rec in recebimentos:
        # Tentar vários campos possíveis
        for campo in [
            "data",
            "data_recebimento",
            "data_pagamento",
            "Data de Pagamento",
        ]:
            if campo in rec and rec[campo]:
                try:
                    # Tentar parsear string de data
                    if isinstance(rec[campo], str):
                        # Tentar vários formatos
                        for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"]:
                            try:
                                dt = datetime.strptime(rec[campo], fmt)
                                datas.append(dt.date().isoformat())
                                break
                            except Exception:
                                continue
                    break
                except Exception:
                    continue

    if not datas:
        return None

    # Retornar data mais comum (moda)
    counter = Counter(datas)
    return counter.most_common(1)[0][0]


class AmarrarRecebimentosRequest(BaseModel):
    """Schema para Aba 3: Amarração"""

    data_recebimento: str = Field(..., description="Data dos recebimentos (YYYY-MM-DD)")
    operadora: Optional[str] = Field(
        None, description="Operadora selecionada (ex: Stone)"
    )


@router.post("/aba1/conciliar-vendas")
async def conciliar_vendas_endpoint(
    request: ConciliarVendasRequest, auth=Depends(get_current_user_and_tenant)
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
            operadora_id=request.operadora_id,
        )

        if not resultado["success"]:
            raise HTTPException(status_code=400, detail=resultado.get("error"))

        return JSONResponse(content=resultado)

    finally:
        db.close()


@router.post("/aba1/upload-e-conciliar")
async def upload_conciliar_vendas(
    arquivo: UploadFile = File(..., description="CSV da operadora"),
    operadora_id: Optional[int] = Form(None),
    auth=Depends(get_current_user_and_tenant),
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
            user_id=user.id,
        )

        if not resultado["success"]:
            raise HTTPException(status_code=400, detail=resultado.get("error"))

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
    auth=Depends(get_current_user_and_tenant),
):
    """
    Lista histórico de importações de conciliação.

    Filtros:
    - operadora_id: Filtrar por operadora
    - data_inicio/data_fim: Período (YYYY-MM-DD)

    Retorna lista de importações anteriores com resumo.
    """
    from .conciliacao_models import ConciliacaoImportacao
    from datetime import datetime as dt

    user, tenant_id = auth
    db = next(get_session())

    try:
        query = db.query(ConciliacaoImportacao).filter(
            ConciliacaoImportacao.tenant_id == tenant_id,
            ConciliacaoImportacao.tipo_importacao == "vendas",
        )

        if data_inicio:
            query = query.filter(
                ConciliacaoImportacao.data_referencia
                >= dt.fromisoformat(data_inicio).date()
            )
        if data_fim:
            query = query.filter(
                ConciliacaoImportacao.data_referencia
                <= dt.fromisoformat(data_fim).date()
            )

        importacoes = query.order_by(ConciliacaoImportacao.criado_em.desc()).all()

        resultado = []
        for imp in importacoes:
            resultado.append(
                {
                    "id": imp.id,
                    "arquivo": imp.arquivo.nome_original if imp.arquivo else None,
                    "data_referencia": imp.data_referencia.isoformat()
                    if imp.data_referencia
                    else None,
                    "total_registros": imp.total_registros,
                    "status": imp.status_importacao,
                    "resumo": imp.resumo,
                    "criado_em": imp.criado_em.isoformat() if imp.criado_em else None,
                }
            )

        return JSONResponse(content={"success": True, "importacoes": resultado})

    finally:
        db.close()


@router.get("/aba1/vendas-status")
async def listar_vendas_com_status(
    status: Optional[str] = Query(None, description="conferidas, pendentes, todas"),
    operadora_id: Optional[int] = None,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    auth=Depends(get_current_user_and_tenant),
):
    """
    Lista vendas com status de conciliação.

    Filtros:
    - status: conferidas (com NSU validado) | pendentes (sem NSU ou não validadas) | todas
    - operadora_id: Operadora específica
    - data_inicio/data_fim: Período

    Retorna vendas com indicador visual de status.
    """
    from .vendas_models import Venda
    from datetime import datetime as dt

    user, tenant_id = auth
    db = next(get_session())

    try:
        query = db.query(Venda).filter(
            Venda.tenant_id == tenant_id, Venda.status == "finalizada"
        )

        if status == "conferidas":
            query = query.filter(Venda.conciliado_vendas.is_(True))
        elif status == "pendentes":
            query = query.filter(
                Venda.conciliado_vendas.is_(False) | (Venda.conciliado_vendas.is_(None))
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
                if pag.forma_pagamento in ["credito", "debito"] and pag.nsu_cartao:
                    nsu = pag.nsu_cartao
                    operadora = pag.operadora_id
                    break

            resultado.append(
                {
                    "id": venda.id,
                    "numero_venda": venda.numero_venda,
                    "data_venda": venda.data_venda.isoformat()
                    if venda.data_venda
                    else None,
                    "valor_total": float(venda.valor_total),
                    "nsu": nsu,
                    "operadora_id": operadora,
                    "status_conciliacao": "conferida"
                    if venda.conciliado_vendas
                    else "pendente",
                    "conciliado_em": venda.conciliado_vendas_em.isoformat()
                    if venda.conciliado_vendas_em
                    else None,
                }
            )

        return JSONResponse(content={"success": True, "vendas": resultado})

    finally:
        db.close()


@router.post("/aba2/validar-recebimentos")
async def validar_recebimentos_endpoint(
    request: ValidarRecebimentosRequest, auth=Depends(get_current_user_and_tenant)
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
                operadora_detectada = deteccao["operadora"]
                confianca_deteccao = deteccao["confianca"]

        # Se arquivos_info fornecido, usar nome do arquivo também
        if request.arquivos_info:
            for arq_info in request.arquivos_info:
                nome_arquivo = arq_info.get("nome", "")
                deteccao_arquivo = detectar_operadora_csv("", nome_arquivo)
                if (
                    deteccao_arquivo
                    and deteccao_arquivo["confianca"] > confianca_deteccao
                ):
                    operadora_detectada = deteccao_arquivo["operadora"]
                    confianca_deteccao = deteccao_arquivo["confianca"]

        # ========================================
        # 2. EXTRAIR DATA DE REFERÊNCIA
        # ========================================
        data_ref = request.data_referencia
        if not data_ref:
            # Tentar extrair dos recebimentos
            data_ref = extrair_data_referencia_recebimentos(
                request.recebimentos_detalhados
            )

        if not data_ref:
            raise HTTPException(
                status_code=400,
                detail="Não foi possível identificar a data de referência. Por favor, informe manualmente.",
            )

        data_ref_obj = datetime.strptime(data_ref, "%Y-%m-%d").date()

        operadora_final = request.operadora or operadora_detectada

        # ========================================
        # 3. VERIFICAR SE JÁ FOI CONCILIADO
        # ========================================
        historico_existente = (
            db.query(HistoricoConciliacao)
            .filter(
                and_(
                    HistoricoConciliacao.tenant_id == tenant_id,
                    HistoricoConciliacao.data_referencia == data_ref_obj,
                    HistoricoConciliacao.operadora == operadora_final,
                    HistoricoConciliacao.status != "cancelada",
                )
            )
            .first()
        )

        ja_conciliado = False
        aviso_reprocessamento = None

        if historico_existente:
            if (
                historico_existente.status == "concluida"
                and historico_existente.aba2_concluida
            ):
                ja_conciliado = True
                aviso_reprocessamento = {
                    "mensagem": f"⚠️ ATENÇÃO: Data {data_ref} da operadora {operadora_final} já foi conciliada em {historico_existente.aba2_concluida_em.strftime('%d/%m/%Y %H:%M')}. Você está reprocessando!",
                    "conciliada_em": historico_existente.aba2_concluida_em.isoformat(),
                    "usuario_anterior": historico_existente.usuario_responsavel,
                    "pode_continuar": True,
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
            operadora=operadora_final,
        )

        if not resultado["success"]:
            raise HTTPException(status_code=400, detail=resultado.get("error"))

        # ========================================
        # 5. REGISTRAR/ATUALIZAR HISTÓRICO
        # ========================================
        if historico_existente:
            # Atualizar existente
            historico = historico_existente
            historico.aba2_concluida = True
            historico.aba2_concluida_em = datetime.now()
            historico.divergencias_encontradas = len(resultado.get("divergencias", []))
            historico.divergencias_aceitas = True  # Se chegou aqui, usuário aceitou

            # Atualizar totais
            if not historico.totais:
                historico.totais = {}
            historico.totais["recebimentos"] = {
                "valor_total": float(resultado.get("valor_total_recebimentos", 0)),
                "quantidade": resultado.get("recebimentos_salvos", 0),
            }

            # Atualizar arquivos se fornecido
            if request.arquivos_info:
                historico.arquivos_processados = request.arquivos_info

        else:
            # Criar novo registro
            usuario = user.email if hasattr(user, "email") else user.username

            historico = HistoricoConciliacao(
                tenant_id=tenant_id,
                data_referencia=data_ref_obj,
                operadora=operadora_final,
                status="em_andamento",
                aba2_concluida=True,
                aba2_concluida_em=datetime.now(),
                divergencias_encontradas=len(resultado.get("divergencias", [])),
                divergencias_aceitas=True,
                arquivos_processados=request.arquivos_info or [],
                totais={
                    "recebimentos": {
                        "valor_total": float(
                            resultado.get("valor_total_recebimentos", 0)
                        ),
                        "quantidade": resultado.get("recebimentos_salvos", 0),
                    }
                },
                usuario_responsavel=usuario,
            )

            db.add(historico)

        db.commit()
        db.refresh(historico)

        # ========================================
        # 6. RETORNAR RESULTADO COMPLETO
        # ========================================
        resultado["historico_id"] = historico.id
        resultado["operadora_detectada"] = operadora_detectada
        resultado["operadora_utilizada"] = operadora_final
        resultado["confianca_deteccao"] = confianca_deteccao
        resultado["data_referencia"] = data_ref
        resultado["ja_conciliado"] = ja_conciliado

        if aviso_reprocessamento:
            resultado["aviso_reprocessamento"] = aviso_reprocessamento

        return JSONResponse(content=resultado)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Erro ao processar validação: {str(e)}"
        )
    finally:
        db.close()


@router.post("/aba3/amarrar-automatico")
async def amarrar_recebimentos_endpoint(
    request: AmarrarRecebimentosRequest, auth=Depends(get_current_user_and_tenant)
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
        data_rec = datetime.strptime(request.data_recebimento, "%Y-%m-%d").date()

        resultado = amarrar_recebimentos_vendas(
            db=db,
            tenant_id=str(tenant_id),
            data_recebimento=data_rec,
            user_id=user.id,
            operadora=request.operadora,
        )

        if not resultado["success"]:
            raise HTTPException(status_code=400, detail=resultado.get("error"))

        return JSONResponse(content=resultado)

    finally:
        db.close()


@router.get("/aba3/preview-amarracao")
async def preview_amarracao_endpoint(
    data_recebimento: str = Query(
        ..., description="Data dos recebimentos (YYYY-MM-DD)"
    ),
    operadora: Optional[str] = Query(
        None, description="Operadora selecionada (ex: Stone)"
    ),
    auth=Depends(get_current_user_and_tenant),
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
        data_rec = datetime.strptime(data_recebimento, "%Y-%m-%d").date()

        # Buscar recebimentos validados e não amarrados
        recebimentos_query = db.query(ConciliacaoRecebimento).filter(
            ConciliacaoRecebimento.tenant_id == str(tenant_id),
            ConciliacaoRecebimento.data_recebimento == data_rec,
            ConciliacaoRecebimento.validado.is_(True),
            ConciliacaoRecebimento.amarrado.is_(False),
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

            venda_pagamento = (
                db.query(VendaPagamento)
                .filter(VendaPagamento.nsu_cartao == rec.nsu)
                .first()
            )

            if not venda_pagamento:
                continue

            venda = (
                db.query(Venda)
                .filter(
                    Venda.tenant_id == str(tenant_id),
                    Venda.id == venda_pagamento.venda_id,
                    Venda.conciliado_vendas.is_(True),
                )
                .first()
            )

            if venda:
                if rec.tipo_recebimento == "antecipacao":
                    parcelas = (
                        db.query(ContaReceber)
                        .filter(
                            ContaReceber.tenant_id == str(tenant_id),
                            ContaReceber.venda_id == venda.id,
                            ContaReceber.status != "recebido",
                            ContaReceber.conciliacao_recebimento_id.is_(None),
                        )
                        .count()
                    )
                    parcelas_count += parcelas
                else:
                    parcela = (
                        db.query(ContaReceber)
                        .filter(
                            ContaReceber.tenant_id == str(tenant_id),
                            ContaReceber.venda_id == venda.id,
                            ContaReceber.numero_parcela == rec.parcela_numero,
                            ContaReceber.status != "recebido",
                            ContaReceber.conciliacao_recebimento_id.is_(None),
                        )
                        .first()
                    )
                    if parcela:
                        parcelas_count += 1
                        valor_total += float(parcela.valor_original)

        return JSONResponse(
            content={
                "recebimentos_validados": len(recebimentos),
                "parcelas_a_baixar": parcelas_count,
                "valor_total": valor_total,
            }
        )

    finally:
        db.close()
