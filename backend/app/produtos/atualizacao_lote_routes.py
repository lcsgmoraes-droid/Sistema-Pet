"""Rotas de atualizacao em lote de produtos."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.produtos.core import _aplicar_status_ativo_produto
from app.produtos.fornecedores import (
    OPERACOES_FORNECEDOR_LOTE,
    _aplicar_fornecedor_produto_lote,
    _validar_fornecedor_produto_lote,
)
from app.produtos.racao import _normalizar_classificacao_racao
from app.produtos.schemas import AtualizacaoLoteRequest
from app.produtos.validators import (
    _validar_pode_inativar_produto,
    _validar_tenant_e_obter_usuario,
)
from app.produtos_models import Produto

router = APIRouter()
logger = logging.getLogger(__name__)


@router.patch("/atualizar-lote")
def atualizar_produtos_lote(
    dados: AtualizacaoLoteRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Atualiza dados comerciais e operacionais de mÃºltiplos produtos."""
    _, tenant_id = _validar_tenant_e_obter_usuario(user_and_tenant)

    logger.info(f"ðŸ“¦ Atualizando {len(dados.produto_ids)} produtos em lote")

    # Buscar produtos
    produtos = (
        db.query(Produto)
        .filter(Produto.id.in_(dados.produto_ids), Produto.tenant_id == tenant_id)
        .all()
    )

    if not produtos:
        raise HTTPException(status_code=404, detail="Nenhum produto encontrado")

    # Validar se todos os produtos pertencem ao usuÃ¡rio
    if len(produtos) != len(dados.produto_ids):
        raise HTTPException(
            status_code=400,
            detail="Alguns produtos nÃ£o foram encontrados ou nÃ£o pertencem ao usuÃ¡rio",
        )

    if dados.fornecedor_operacao:
        if dados.fornecedor_operacao not in OPERACOES_FORNECEDOR_LOTE:
            raise HTTPException(
                status_code=400,
                detail="Operacao de fornecedor invalida",
            )
        if (
            dados.fornecedor_operacao in {"adicionar", "definir_principal"}
            and dados.fornecedor_id is None
        ):
            raise HTTPException(
                status_code=400,
                detail="Informe o fornecedor para aplicar a operacao em lote",
            )
        if dados.fornecedor_id is not None:
            _validar_fornecedor_produto_lote(db, dados.fornecedor_id, tenant_id)
    elif dados.fornecedor_id is not None:
        raise HTTPException(
            status_code=400,
            detail="Informe a operacao do fornecedor para atualizar em lote",
        )

    linha_racao_selecionada = None
    if dados.linha_racao_id is not None:
        from .opcoes_racao_models import LinhaRacao

        linha_racao_selecionada = (
            db.query(LinhaRacao)
            .filter(
                LinhaRacao.id == dados.linha_racao_id,
                LinhaRacao.tenant_id == tenant_id,
            )
            .first()
        )

    # Atualizar campos fornecidos
    atualizado = 0
    for produto in produtos:
        if dados.ativo is not None:
            if not dados.ativo:
                _validar_pode_inativar_produto(db, produto, tenant_id)
            if (
                bool(produto.ativo) != dados.ativo
                or bool(produto.situacao) != dados.ativo
            ):
                atualizado += 1
            _aplicar_status_ativo_produto(produto, dados.ativo)
        if dados.marca_id is not None:
            produto.marca_id = dados.marca_id
            atualizado += 1
        if dados.eh_racao is not None:
            produto.tipo = "ração" if dados.eh_racao else "produto"
            atualizado += 1
            if not dados.eh_racao:
                produto.classificacao_racao = None
                produto.peso_embalagem = None
                produto.categoria_racao = None
                produto.especies_indicadas = None
                produto.linha_racao_id = None
                produto.porte_animal_id = None
                produto.fase_publico_id = None
                produto.tipo_tratamento_id = None
                produto.sabor_proteina_id = None
                produto.apresentacao_peso_id = None
        if dados.classificacao_racao is not None and dados.eh_racao is not False:
            produto.classificacao_racao = _normalizar_classificacao_racao(
                dados.classificacao_racao
            )
            if produto.classificacao_racao:
                produto.tipo = "ração"
            atualizado += 1
        if dados.categoria_id is not None:
            produto.categoria_id = dados.categoria_id
            atualizado += 1
        if dados.departamento_id is not None:
            produto.departamento_id = dados.departamento_id
            atualizado += 1
        if dados.fornecedor_operacao:
            if _aplicar_fornecedor_produto_lote(
                db,
                produto,
                dados.fornecedor_id,
                dados.fornecedor_operacao,
                tenant_id,
                remover_outros=bool(dados.fornecedor_remover_outros),
            ):
                atualizado += 1
        if dados.linha_racao_id is not None:
            produto.linha_racao_id = dados.linha_racao_id
            if dados.eh_racao is not False and linha_racao_selecionada:
                produto.classificacao_racao = _normalizar_classificacao_racao(
                    linha_racao_selecionada.nome
                )
                produto.tipo = "ração"
            atualizado += 1
        if dados.porte_animal_id is not None:
            produto.porte_animal_id = dados.porte_animal_id
            atualizado += 1
        if dados.fase_publico_id is not None:
            produto.fase_publico_id = dados.fase_publico_id
            atualizado += 1
        if dados.tipo_tratamento_id is not None:
            produto.tipo_tratamento_id = dados.tipo_tratamento_id
            atualizado += 1
        if dados.sabor_proteina_id is not None:
            produto.sabor_proteina_id = dados.sabor_proteina_id
            atualizado += 1
        if dados.apresentacao_peso_id is not None:
            produto.apresentacao_peso_id = dados.apresentacao_peso_id
            atualizado += 1
        if dados.categoria_racao is not None:
            produto.categoria_racao = dados.categoria_racao
            atualizado += 1
        if dados.especies_indicadas is not None:
            produto.especies_indicadas = dados.especies_indicadas
            atualizado += 1
        if dados.controle_lote is not None:
            produto.controle_lote = dados.controle_lote
            atualizado += 1
        if dados.estoque_minimo is not None:
            produto.estoque_minimo = dados.estoque_minimo
            atualizado += 1
        if dados.estoque_maximo is not None:
            produto.estoque_maximo = dados.estoque_maximo
            atualizado += 1

        produto_ativo_loja = bool(getattr(produto, "ativo", True)) and bool(
            getattr(produto, "situacao", True)
        )
        if not produto_ativo_loja:
            if bool(getattr(produto, "anunciar_ecommerce", False)):
                atualizado += 1
            if bool(getattr(produto, "anunciar_app", False)):
                atualizado += 1
            produto.anunciar_ecommerce = False
            produto.anunciar_app = False
        else:
            if dados.anunciar_ecommerce is not None:
                if produto.anunciar_ecommerce != dados.anunciar_ecommerce:
                    atualizado += 1
                produto.anunciar_ecommerce = dados.anunciar_ecommerce
            if dados.anunciar_app is not None:
                if produto.anunciar_app != dados.anunciar_app:
                    atualizado += 1
                produto.anunciar_app = dados.anunciar_app

        produto.updated_at = datetime.utcnow()

    db.commit()

    logger.info(f"âœ… {len(produtos)} produtos atualizados em lote")

    return {
        "produtos_atualizados": len(produtos),
        "campos_atualizados": atualizado,
        "ativo": dados.ativo,
        "eh_racao": dados.eh_racao,
        "classificacao_racao": dados.classificacao_racao,
        "marca_id": dados.marca_id,
        "categoria_id": dados.categoria_id,
        "departamento_id": dados.departamento_id,
        "fornecedor_id": dados.fornecedor_id,
        "fornecedor_operacao": dados.fornecedor_operacao,
        "fornecedor_remover_outros": dados.fornecedor_remover_outros,
        "linha_racao_id": dados.linha_racao_id,
        "porte_animal_id": dados.porte_animal_id,
        "fase_publico_id": dados.fase_publico_id,
        "tipo_tratamento_id": dados.tipo_tratamento_id,
        "sabor_proteina_id": dados.sabor_proteina_id,
        "apresentacao_peso_id": dados.apresentacao_peso_id,
        "categoria_racao": dados.categoria_racao,
        "especies_indicadas": dados.especies_indicadas,
        "controle_lote": dados.controle_lote,
        "estoque_minimo": dados.estoque_minimo,
        "estoque_maximo": dados.estoque_maximo,
        "anunciar_ecommerce": dados.anunciar_ecommerce,
        "anunciar_app": dados.anunciar_app,
    }
