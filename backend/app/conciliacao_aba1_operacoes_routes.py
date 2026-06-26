# ruff: noqa: F401
"""
API Routes para ABA 1: Conciliação de Vendas (PDV vs Stone)

Arquitetura de Duas Colunas:
- Esquerda: Vendas PDV com cartão (sempre carregadas)
- Direita: NSUs da planilha Stone importada
- Match automático + confirmação manual
"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy import or_
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
import logging

from .db import get_session
from .auth.dependencies import get_current_user_and_tenant
from .vendas_models import Venda, VendaPagamento
from .conciliacao_models import ConciliacaoImportacao
from .conciliacao_helpers import serialize_for_json
from app.operadoras_models import OperadoraCartao

from .conciliacao_aba1_schemas import AtualizarOperadoraRequest, ConfirmarMatchRequest

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/historico")
async def listar_historico(
    operadora_id: Optional[int] = None,  # FILTRO por operadora
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    auth=Depends(get_current_user_and_tenant),
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
            ConciliacaoImportacao.tipo_importacao == "vendas",
            ConciliacaoImportacao.status_importacao == "processada",
            ConciliacaoImportacao.resumo["matches_confirmados"].isnot(None),
        ]

        # FILTRO POR OPERADORA (opcional)
        if operadora_id:
            query_filtros.append(
                ConciliacaoImportacao.resumo["operadora_id"].astext == str(operadora_id)
            )

        query = (
            db.query(ConciliacaoImportacao)
            .filter(*query_filtros)
            .order_by(ConciliacaoImportacao.criado_em.desc())
        )

        total = query.count()
        importacoes = query.offset((page - 1) * limit).limit(limit).all()

        # Formatar histórico
        historico = []
        for imp in importacoes:
            matches_confirmados = imp.resumo.get("matches_confirmados", [])
            historico.append(
                {
                    "id": imp.id,
                    "data_importacao": imp.criado_em.isoformat()
                    if imp.criado_em
                    else None,
                    "operadora_id": imp.resumo.get("operadora_id"),
                    "total_matches": len(matches_confirmados),
                    "conferidas": imp.resumo.get("conferidas", 0),
                    "matches": matches_confirmados,  # Detalhes completos
                }
            )

        return JSONResponse(
            content=serialize_for_json(
                {
                    "success": True,
                    "historico": historico,
                    "total": total,
                    "page": page,
                    "limit": limit,
                    "total_pages": (total + limit - 1) // limit if total > 0 else 0,
                }
            )
        )

    except Exception as e:
        logger.error(f"Erro ao listar histórico: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        db.close()


@router.post("/confirmar-match")
async def confirmar_match(
    request: ConfirmarMatchRequest, auth=Depends(get_current_user_and_tenant)
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
        venda = (
            db.query(Venda)
            .filter(Venda.id == request.venda_id, Venda.tenant_id == tenant_id)
            .first()
        )

        if not venda:
            raise HTTPException(status_code=404, detail="Venda não encontrada")

        # Buscar pagamento cartão da venda
        pagamento = next(
            (p for p in venda.pagamentos if p.forma_pagamento in ["debito", "credito"]),
            None,
        )

        if not pagamento:
            raise HTTPException(
                status_code=400, detail="Venda não possui pagamento em cartão"
            )

        # Vincular NSU
        pagamento.nsu_cartao = request.nsu_stone

        # Marcar como conciliada
        venda.conciliado_vendas = True
        venda.conciliado_vendas_em = datetime.utcnow()

        db.commit()

        return JSONResponse(
            content=serialize_for_json(
                {
                    "success": True,
                    "venda_id": venda.id,
                    "numero_venda": venda.numero_venda,
                    "nsu": request.nsu_stone,
                    "conciliado": True,
                }
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao confirmar match: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        db.close()


@router.post("/upload-stone")
async def upload_planilha_stone(
    arquivo: UploadFile = File(...),
    operadora_id: Optional[int] = Form(None),
    auth=Depends(get_current_user_and_tenant),
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
            user_id=user.id,
        )

        if not resultado["success"]:
            raise HTTPException(status_code=400, detail=resultado.get("error"))

        return JSONResponse(content=serialize_for_json(resultado))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao upload Stone: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        db.close()


@router.put("/atualizar-operadora")
async def atualizar_operadora(
    request: AtualizarOperadoraRequest, auth=Depends(get_current_user_and_tenant)
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
        pagamento = (
            db.query(VendaPagamento)
            .filter(
                VendaPagamento.id == request.pagamento_id,
                VendaPagamento.tenant_id == tenant_id,
            )
            .first()
        )

        if not pagamento:
            raise HTTPException(status_code=404, detail="Pagamento não encontrado")

        # Verificar se operadora existe
        operadora = (
            db.query(OperadoraCartao)
            .filter(
                OperadoraCartao.id == request.operadora_id,
                OperadoraCartao.tenant_id == tenant_id,
            )
            .first()
        )

        if not operadora:
            raise HTTPException(status_code=404, detail="Operadora não encontrada")

        # Atualizar operadora
        pagamento.operadora_id = request.operadora_id
        db.commit()

        logger.info(
            f"[Atualizar Operadora] Pagamento #{pagamento.id} atualizado para operadora {operadora.nome}"
        )

        return JSONResponse(
            content=serialize_for_json(
                {
                    "success": True,
                    "message": f"Operadora atualizada para {operadora.nome}",
                    "pagamento_id": pagamento.id,
                    "operadora_id": operadora.id,
                    "operadora_nome": operadora.nome,
                }
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao atualizar operadora: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        db.close()
