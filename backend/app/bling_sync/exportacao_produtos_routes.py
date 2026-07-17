"""Rotas para cadastrar produtos locais no Bling."""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user_and_tenant
from app.bling_integration import BlingAPI
from app.bling_sync.catalog_snapshots import _invalidate_bling_snapshots
from app.bling_sync.product_matching import _produto_eh_pai, _produto_sincroniza_estoque
from app.bling_sync.product_export_enrichment import (
    _detalhe_bling_confirma_produto,
    _enviar_fornecedores_produto_bling,
    _erro_bling_nao_encontrado,
    _limpar_vinculo_bling_inexistente,
    _montar_payload_produto_bling,
    _texto,
)
from app.bling_sync.routes_common import (
    PRODUTO_NAO_ENCONTRADO,
    _buscar_item_bling_por_codigos_com_retry,
    _upsert_sync_vinculo,
    utc_now,
)
from app.bling_sync.schemas import (
    ExportarProdutoLocalBlingRequest,
    ExportarProdutosLocaisBlingLoteRequest,
)
from app.db import get_session
from app.produtos_models import Produto, ProdutoBlingSync, ProdutoFornecedor
from app.security.permissions_decorator import require_any_permission
from app.services.bling_sync_service import BlingSyncService

logger = logging.getLogger(__name__)
router = APIRouter()

PERMISSOES_EXPORTACAO_BLING = ("compras.sincronizacao_bling", "produtos.editar")


def _detalhe_publico_erro_bling(error: Exception, *, operacao: str) -> tuple[int, str]:
    mensagem = str(error).upper()
    if "429" in mensagem or "TOO_MANY_REQUESTS" in mensagem:
        return (
            429,
            "O Bling atingiu o limite temporario de requisicoes. Aguarde alguns segundos e tente novamente.",
        )

    if any(
        marcador in mensagem
        for marcador in ("400", "422", "BAD REQUEST", "UNPROCESSABLE")
    ):
        return (
            422,
            "O Bling recusou os dados do produto. Revise SKU, EAN, unidade e dados fiscais.",
        )

    return (
        502,
        f"Nao foi possivel {operacao} no Bling agora. Tente novamente em alguns instantes.",
    )


def _extrair_bling_produto_id(resposta: dict[str, Any]) -> str:
    data = resposta.get("data") if isinstance(resposta, dict) else {}
    candidatos = [
        data.get("id") if isinstance(data, dict) else None,
        resposta.get("id") if isinstance(resposta, dict) else None,
    ]
    for candidato in candidatos:
        texto = _texto(candidato)
        if texto:
            return texto
    raise HTTPException(
        status_code=502,
        detail="O Bling criou o produto, mas a resposta nao trouxe o ID do cadastro.",
    )


def _buscar_produto(db: Session, tenant_id, produto_id: int) -> Produto:
    produto = (
        db.query(Produto)
        .options(
            joinedload(Produto.marca),
            joinedload(Produto.imagens),
            joinedload(Produto.fornecedor),
            joinedload(Produto.fornecedores_alternativos).joinedload(
                ProdutoFornecedor.fornecedor
            ),
        )
        .filter(Produto.id == produto_id, Produto.tenant_id == tenant_id)
        .first()
    )
    if not produto:
        raise HTTPException(status_code=404, detail=PRODUTO_NAO_ENCONTRADO)
    return produto


def _obter_sync_vinculado(
    db: Session, tenant_id, produto_id: int
) -> Optional[ProdutoBlingSync]:
    return (
        db.query(ProdutoBlingSync)
        .filter(
            ProdutoBlingSync.tenant_id == tenant_id,
            ProdutoBlingSync.produto_id == produto_id,
            ProdutoBlingSync.bling_produto_id.isnot(None),
            ProdutoBlingSync.bling_produto_id != "",
        )
        .first()
    )


def _registrar_vinculo_e_enfileirar_estoque(
    db: Session,
    tenant_id,
    produto: Produto,
    bling_produto_id: str,
    enviar_estoque: bool,
) -> dict[str, Any]:
    _upsert_sync_vinculo(db, tenant_id, produto, bling_produto_id)
    db.flush()

    if not enviar_estoque or not _produto_sincroniza_estoque(produto):
        return {"ok": True, "estoque_enfileirado": False}

    resultado_fila = BlingSyncService.queue_product_sync(
        db=db,
        produto_id=produto.id,
        motivo="cadastro_produto_bling",
        origem="exportacao_bling",
        force=True,
    )
    return {
        "ok": bool(resultado_fila.get("ok")),
        "estoque_enfileirado": bool(resultado_fila.get("ok")),
        "queue_id": resultado_fila.get("queue_id"),
        "estoque_enviado": resultado_fila.get("estoque_enfileirado"),
        "detail": resultado_fila.get("detail"),
    }


def _montar_resultado(
    produto: Produto,
    bling_produto_id: str,
    status: str,
    estoque_resultado: Optional[dict[str, Any]] = None,
    enriquecimento: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    mensagens = {
        "criado": "Produto cadastrado no Bling e vinculado ao CorePet.",
        "vinculado_existente": "Produto ja existia no Bling; criamos apenas o vinculo.",
        "ja_vinculado": "Produto ja estava vinculado ao Bling.",
    }
    estoque_resultado = estoque_resultado or {}
    enriquecimento = enriquecimento or {}
    resultado = {
        "ok": True,
        "status": status,
        "message": mensagens.get(status, "Exportacao concluida."),
        "produto_id": produto.id,
        "produto_codigo": produto.codigo,
        "produto_nome": produto.nome,
        "bling_produto_id": bling_produto_id,
        "sincronizar_estoque": _produto_sincroniza_estoque(produto),
        "estoque_enfileirado": bool(estoque_resultado.get("estoque_enfileirado")),
        "queue_id": estoque_resultado.get("queue_id"),
        "estoque_enviado": estoque_resultado.get("estoque_enviado"),
        "estoque_detail": estoque_resultado.get("detail"),
        "imagens_enviadas": int(enriquecimento.get("imagens_enviadas") or 0),
        "fornecedores_enviados": int(enriquecimento.get("fornecedores_enviados") or 0),
        "fornecedores_nao_localizados": int(
            enriquecimento.get("fornecedores_nao_localizados") or 0
        ),
        "fornecedores_erros": int(enriquecimento.get("fornecedores_erros") or 0),
        "fornecedores_detail": enriquecimento.get("fornecedores_detail"),
    }
    return resultado


def _exportar_produto_local_para_bling(
    db: Session,
    tenant_id,
    bling: BlingAPI,
    produto_id: int,
    enviar_estoque: bool,
) -> dict[str, Any]:
    produto = _buscar_produto(db, tenant_id, produto_id)

    if _produto_eh_pai(produto):
        raise HTTPException(
            status_code=400,
            detail="Produto PAI/agrupador nao deve ser cadastrado no Bling por esta acao.",
        )

    codigo = _texto(produto.codigo)
    if not codigo:
        raise HTTPException(
            status_code=400,
            detail="Produto sem SKU/codigo local. Preencha o codigo antes de enviar ao Bling.",
        )

    sync_vinculado = _obter_sync_vinculado(db, tenant_id, produto.id)
    if sync_vinculado:
        bling_produto_id_atual = _texto(sync_vinculado.bling_produto_id)
        vinculo_inexistente = False
        try:
            detalhe_bling = bling.consultar_produto(bling_produto_id_atual)
        except Exception as error:
            if _erro_bling_nao_encontrado(error):
                vinculo_inexistente = True
            else:
                db.rollback()
                status_code, detail = _detalhe_publico_erro_bling(
                    error, operacao="conferir o vinculo do produto"
                )
                raise HTTPException(status_code=status_code, detail=detail) from error
        else:
            vinculo_inexistente = not _detalhe_bling_confirma_produto(
                detalhe_bling, bling_produto_id_atual
            )

        if vinculo_inexistente:
            _limpar_vinculo_bling_inexistente(sync_vinculado)
            db.commit()
            _invalidate_bling_snapshots(tenant_id)
        else:
            sync_vinculado.ultima_conferencia_bling = utc_now()
            estoque_resultado = _registrar_vinculo_e_enfileirar_estoque(
                db,
                tenant_id,
                produto,
                bling_produto_id_atual,
                enviar_estoque,
            )
            db.commit()
            return _montar_resultado(
                produto,
                bling_produto_id_atual,
                "ja_vinculado",
                estoque_resultado,
            )

    codigos_extras = [
        _texto(produto.codigo_barras),
        _texto(produto.gtin_ean),
        _texto(produto.gtin_ean_tributario),
    ]
    try:
        item_existente = _buscar_item_bling_por_codigos_com_retry(
            bling,
            codigo,
            codigos_extras=codigos_extras,
        )
    except Exception as error:
        db.rollback()
        logger.warning(
            "Falha ao consultar produto no Bling antes da exportacao; produto_id=%s error_type=%s",
            produto.id,
            type(error).__name__,
        )
        status_code, detail = _detalhe_publico_erro_bling(
            error, operacao="consultar o produto"
        )
        raise HTTPException(
            status_code=status_code,
            detail=detail,
        ) from error

    bling_produto_id_existente = (
        _texto(item_existente.get("id")) if item_existente else ""
    )
    if bling_produto_id_existente:
        try:
            detalhe_existente = bling.consultar_produto(bling_produto_id_existente)
        except Exception as error:
            if not _erro_bling_nao_encontrado(error):
                db.rollback()
                status_code, detail = _detalhe_publico_erro_bling(
                    error, operacao="confirmar o produto encontrado"
                )
                raise HTTPException(status_code=status_code, detail=detail) from error
        else:
            if _detalhe_bling_confirma_produto(
                detalhe_existente, bling_produto_id_existente
            ):
                estoque_resultado = _registrar_vinculo_e_enfileirar_estoque(
                    db,
                    tenant_id,
                    produto,
                    bling_produto_id_existente,
                    enviar_estoque,
                )
                db.commit()
                return _montar_resultado(
                    produto,
                    bling_produto_id_existente,
                    "vinculado_existente",
                    estoque_resultado,
                )

    payload = _montar_payload_produto_bling(produto)
    try:
        resposta = bling.criar_produto(payload)
    except Exception as error:
        db.rollback()
        logger.warning(
            "Falha ao criar produto no Bling; produto_id=%s error_type=%s",
            produto.id,
            type(error).__name__,
        )
        status_code, detail = _detalhe_publico_erro_bling(
            error, operacao="criar o produto"
        )
        raise HTTPException(
            status_code=status_code,
            detail=detail,
        ) from error

    bling_produto_id = _extrair_bling_produto_id(resposta)
    enriquecimento = {
        "imagens_enviadas": len(
            payload.get("midia", {}).get("imagens", {}).get("imagensURL", [])
        )
    }
    enriquecimento.update(
        _enviar_fornecedores_produto_bling(bling, produto, bling_produto_id)
    )
    estoque_resultado = _registrar_vinculo_e_enfileirar_estoque(
        db, tenant_id, produto, bling_produto_id, enviar_estoque
    )
    db.commit()
    return _montar_resultado(
        produto,
        bling_produto_id,
        "criado",
        estoque_resultado,
        enriquecimento,
    )


@router.post("/produtos-bling/validar-vinculo/{produto_id}")
@require_any_permission(PERMISSOES_EXPORTACAO_BLING)
def validar_vinculo_produto_bling(
    produto_id: int,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Confere se o ID salvo ainda existe no Bling e limpa vinculos obsoletos."""
    _current_user, tenant_id = user_and_tenant
    produto = _buscar_produto(db, tenant_id, produto_id)
    sync = _obter_sync_vinculado(db, tenant_id, produto_id)
    if not sync:
        return {
            "ok": True,
            "status": "sem_vinculo",
            "existe": False,
            "produto_id": produto.id,
            "bling_produto_id": None,
            "message": "Este produto nao possui vinculo ativo com o Bling.",
        }

    bling_produto_id = _texto(sync.bling_produto_id)
    try:
        detalhe_bling = BlingAPI().consultar_produto(bling_produto_id)
    except Exception as error:
        if not _erro_bling_nao_encontrado(error):
            db.rollback()
            status_code, detail = _detalhe_publico_erro_bling(
                error, operacao="conferir o produto"
            )
            raise HTTPException(status_code=status_code, detail=detail) from error

        _limpar_vinculo_bling_inexistente(sync)
        db.commit()
        _invalidate_bling_snapshots(tenant_id)
        return {
            "ok": True,
            "status": "removido_no_bling",
            "existe": False,
            "produto_id": produto.id,
            "bling_produto_id": None,
            "message": (
                "O produto nao existe mais no Bling. O vinculo antigo foi removido "
                "e o cadastro pode ser criado novamente."
            ),
        }

    if not _detalhe_bling_confirma_produto(detalhe_bling, bling_produto_id):
        _limpar_vinculo_bling_inexistente(sync)
        db.commit()
        _invalidate_bling_snapshots(tenant_id)
        return {
            "ok": True,
            "status": "removido_no_bling",
            "existe": False,
            "produto_id": produto.id,
            "bling_produto_id": None,
            "message": (
                "O produto nao existe mais no Bling. O vinculo antigo foi removido "
                "e o cadastro pode ser criado novamente."
            ),
        }

    sync.ultima_conferencia_bling = utc_now()
    sync.updated_at = utc_now()
    db.commit()
    return {
        "ok": True,
        "status": "confirmado",
        "existe": True,
        "produto_id": produto.id,
        "bling_produto_id": bling_produto_id,
        "bling_nome": _texto(detalhe_bling.get("nome"))
        if isinstance(detalhe_bling, dict)
        else None,
        "bling_situacao": _texto(detalhe_bling.get("situacao"))
        if isinstance(detalhe_bling, dict)
        else None,
        "message": "Cadastro confirmado no Bling.",
    }


@router.post("/produtos-bling/exportar")
@require_any_permission(PERMISSOES_EXPORTACAO_BLING)
def exportar_produto_local_para_bling(
    body: ExportarProdutoLocalBlingRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Cadastra um produto local no Bling ou vincula caso o SKU ja exista la."""
    _current_user, tenant_id = user_and_tenant
    try:
        bling = BlingAPI()
        resultado = _exportar_produto_local_para_bling(
            db,
            tenant_id,
            bling,
            produto_id=body.produto_id,
            enviar_estoque=body.enviar_estoque,
        )
        _invalidate_bling_snapshots(tenant_id)
        return resultado
    except HTTPException:
        raise
    except Exception as error:
        db.rollback()
        logger.error(
            "Erro inesperado ao exportar produto local para o Bling; error_type=%s",
            type(error).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail="Nao foi possivel concluir o cadastro no Bling.",
        ) from error


@router.post("/produtos-bling/exportar-lote")
@require_any_permission(PERMISSOES_EXPORTACAO_BLING)
def exportar_produtos_locais_para_bling_lote(
    body: ExportarProdutosLocaisBlingLoteRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Cadastra no Bling os produtos locais selecionados na central."""
    _current_user, tenant_id = user_and_tenant
    produto_ids = list(
        dict.fromkeys(int(produto_id) for produto_id in body.produto_ids)
    )

    try:
        bling = BlingAPI()
    except Exception as error:
        logger.error(
            "Erro ao iniciar integracao Bling para exportacao em lote; error_type=%s",
            type(error).__name__,
        )
        raise HTTPException(
            status_code=503,
            detail="A integracao com o Bling esta indisponivel no momento.",
        ) from error

    items: list[dict[str, Any]] = []
    for produto_id in produto_ids:
        try:
            items.append(
                _exportar_produto_local_para_bling(
                    db,
                    tenant_id,
                    bling,
                    produto_id=produto_id,
                    enviar_estoque=body.enviar_estoque,
                )
            )
        except HTTPException as error:
            db.rollback()
            items.append(
                {
                    "ok": False,
                    "status": "erro",
                    "produto_id": produto_id,
                    "detail": error.detail,
                }
            )
        except Exception as error:
            db.rollback()
            logger.error(
                "Erro inesperado ao exportar produto em lote; produto_id=%s error_type=%s",
                produto_id,
                type(error).__name__,
            )
            items.append(
                {
                    "ok": False,
                    "status": "erro",
                    "produto_id": produto_id,
                    "detail": "Nao foi possivel concluir este cadastro no Bling.",
                }
            )

    criados = sum(1 for item in items if item.get("status") == "criado")
    vinculados_existentes = sum(
        1 for item in items if item.get("status") == "vinculado_existente"
    )
    ja_vinculados = sum(1 for item in items if item.get("status") == "ja_vinculado")
    erros = sum(1 for item in items if not item.get("ok"))
    estoque_enfileirado = sum(1 for item in items if item.get("estoque_enfileirado"))

    if criados or vinculados_existentes or ja_vinculados:
        _invalidate_bling_snapshots(tenant_id)

    return {
        "ok": erros == 0,
        "message": (
            "Lote enviado ao Bling."
            if erros == 0
            else "Lote concluido com alguns itens pendentes."
        ),
        "total_solicitados": len(produto_ids),
        "criados": criados,
        "vinculados_existentes": vinculados_existentes,
        "ja_vinculados": ja_vinculados,
        "estoque_enfileirado": estoque_enfileirado,
        "erros": erros,
        "items": items,
    }
