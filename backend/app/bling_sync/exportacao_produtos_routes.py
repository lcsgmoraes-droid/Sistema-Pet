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
from app.bling_sync.routes_common import (
    PRODUTO_NAO_ENCONTRADO,
    _buscar_item_bling_por_codigos_com_retry,
    _upsert_sync_vinculo,
)
from app.bling_sync.schemas import (
    ExportarProdutoLocalBlingRequest,
    ExportarProdutosLocaisBlingLoteRequest,
)
from app.db import get_session
from app.produtos_models import Produto, ProdutoBlingSync
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


def _texto(valor: Any, max_length: Optional[int] = None) -> str:
    texto = str(valor or "").strip()
    if max_length and len(texto) > max_length:
        return texto[:max_length].rstrip()
    return texto


def _float_or_none(valor: Any) -> Optional[float]:
    if valor is None or valor == "":
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _float_or_zero(valor: Any) -> float:
    return _float_or_none(valor) or 0.0


def _digits(valor: Any, allowed_lengths: Optional[set[int]] = None) -> str:
    texto = "".join(ch for ch in str(valor or "") if ch.isdigit())
    if allowed_lengths and len(texto) not in allowed_lengths:
        return ""
    return texto


def _origem_fiscal(valor: Any) -> Optional[int]:
    texto = _texto(valor)
    if texto.isdigit():
        origem = int(texto)
        if 0 <= origem <= 8:
            return origem
    return None


def _tipo_bling(produto: Produto) -> str:
    tipo = _texto(getattr(produto, "tipo", "")).lower()
    return "S" if tipo in {"servico", "servico_produto"} else "P"


def _montar_payload_produto_bling(produto: Produto) -> dict[str, Any]:
    nome = _texto(produto.nome, 120) or _texto(produto.codigo, 120)
    payload: dict[str, Any] = {
        "nome": nome,
        "codigo": _texto(produto.codigo, 80),
        "preco": _float_or_zero(produto.preco_venda),
        "tipo": _tipo_bling(produto),
        "situacao": "A" if bool(produto.situacao) else "I",
        "formato": "S",
        "unidade": _texto(produto.unidade, 10) or "UN",
    }

    descricao_curta = _texto(produto.descricao_curta, 500)
    descricao_completa = _texto(produto.descricao_completa, 4000)
    if descricao_curta:
        payload["descricaoCurta"] = descricao_curta
    if descricao_completa:
        payload["descricaoComplementar"] = descricao_completa

    gtin = _digits(produto.gtin_ean or produto.codigo_barras, {8, 12, 13, 14})
    gtin_embalagem = _digits(produto.gtin_ean_tributario, {8, 12, 13})
    if gtin:
        payload["gtin"] = gtin
    if gtin_embalagem:
        payload["gtinEmbalagem"] = gtin_embalagem

    marca_nome = _texto(getattr(getattr(produto, "marca", None), "nome", ""), 120)
    if marca_nome:
        payload["marca"] = marca_nome

    peso_liquido = _float_or_none(produto.peso_liquido)
    peso_bruto = _float_or_none(produto.peso_bruto)
    if peso_liquido and peso_liquido > 0:
        payload["pesoLiquido"] = peso_liquido
    if peso_bruto and peso_bruto > 0:
        payload["pesoBruto"] = peso_bruto

    estoque: dict[str, Any] = {}
    estoque_minimo = _float_or_none(produto.estoque_minimo)
    estoque_maximo = _float_or_none(produto.estoque_maximo)
    localizacao = _texto(getattr(produto, "localizacao", ""), 80)
    crossdocking = getattr(produto, "crossdocking_dias", None)
    if estoque_minimo is not None:
        estoque["minimo"] = estoque_minimo
    if estoque_maximo is not None and estoque_maximo > 0:
        estoque["maximo"] = estoque_maximo
    if localizacao:
        estoque["localizacao"] = localizacao
    if isinstance(crossdocking, int) and crossdocking > 0:
        estoque["crossdocking"] = crossdocking
    if estoque:
        payload["estoque"] = estoque

    tributacao: dict[str, Any] = {}
    ncm = _digits(produto.ncm, {8})
    cest = _digits(produto.cest, {7})
    origem = _origem_fiscal(produto.origem)
    dados_adicionais = _texto(getattr(produto, "informacoes_adicionais_nf", ""), 500)
    if ncm:
        tributacao["ncm"] = ncm
    if cest:
        tributacao["cest"] = cest
    if origem is not None:
        tributacao["origem"] = origem
    if dados_adicionais:
        tributacao["dadosAdicionais"] = dados_adicionais
    if tributacao:
        payload["tributacao"] = tributacao

    dimensoes: dict[str, Any] = {}
    for origem_attr, destino_attr in [
        ("largura", "largura"),
        ("altura", "altura"),
        ("profundidade", "profundidade"),
    ]:
        valor = _float_or_none(getattr(produto, origem_attr, None))
        if valor and valor > 0:
            dimensoes[destino_attr] = valor
    if dimensoes:
        dimensoes["unidadeMedida"] = 1
        payload["dimensoes"] = dimensoes

    return payload


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
        .options(joinedload(Produto.marca))
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
) -> dict[str, Any]:
    mensagens = {
        "criado": "Produto cadastrado no Bling e vinculado ao CorePet.",
        "vinculado_existente": "Produto ja existia no Bling; criamos apenas o vinculo.",
        "ja_vinculado": "Produto ja estava vinculado ao Bling.",
    }
    estoque_resultado = estoque_resultado or {}
    return {
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
    }


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
        estoque_resultado = _registrar_vinculo_e_enfileirar_estoque(
            db,
            tenant_id,
            produto,
            _texto(sync_vinculado.bling_produto_id),
            enviar_estoque,
        )
        db.commit()
        return _montar_resultado(
            produto,
            _texto(sync_vinculado.bling_produto_id),
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

    if item_existente and _texto(item_existente.get("id")):
        bling_produto_id = _texto(item_existente.get("id"))
        estoque_resultado = _registrar_vinculo_e_enfileirar_estoque(
            db, tenant_id, produto, bling_produto_id, enviar_estoque
        )
        db.commit()
        return _montar_resultado(
            produto,
            bling_produto_id,
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
    estoque_resultado = _registrar_vinculo_e_enfileirar_estoque(
        db, tenant_id, produto, bling_produto_id, enviar_estoque
    )
    db.commit()
    return _montar_resultado(produto, bling_produto_id, "criado", estoque_resultado)


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
