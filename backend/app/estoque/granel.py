from __future__ import annotations

from datetime import datetime
import json
import logging
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.produtos_models import (
    EstoqueMovimentacao,
    GranelConversao,
    Produto,
    ProdutoGranelVinculo,
    ProdutoHistoricoPreco,
)


logger = logging.getLogger(__name__)


def _calcular_margem_preco(preco_venda: float, preco_custo: float) -> float:
    if preco_venda <= 0:
        return 0
    return ((preco_venda - preco_custo) / preco_venda) * 100


def _alterar_preco_venda_granel_com_historico(
    db: Session,
    tenant_id,
    current_user,
    produto_granel: Produto,
    preco_venda_anterior: float,
    preco_custo_anterior: float,
    preco_venda_novo: float,
    conversao_id: int,
) -> bool:
    preco_venda_novo = round(float(preco_venda_novo), 2)
    if round(preco_venda_anterior, 2) == preco_venda_novo:
        return False

    preco_custo_novo = float(produto_granel.preco_custo or 0)
    variacao_custo = (
        ((preco_custo_novo - preco_custo_anterior) / preco_custo_anterior) * 100
        if preco_custo_anterior > 0
        else 0
    )
    variacao_venda = (
        ((preco_venda_novo - preco_venda_anterior) / preco_venda_anterior) * 100
        if preco_venda_anterior > 0
        else 0
    )

    produto_granel.preco_venda = preco_venda_novo
    db.add(
        ProdutoHistoricoPreco(
            produto_id=produto_granel.id,
            preco_custo_anterior=preco_custo_anterior,
            preco_custo_novo=preco_custo_novo,
            preco_venda_anterior=preco_venda_anterior,
            preco_venda_novo=preco_venda_novo,
            margem_anterior=_calcular_margem_preco(
                preco_venda_anterior, preco_custo_anterior
            ),
            margem_nova=_calcular_margem_preco(preco_venda_novo, preco_custo_novo),
            variacao_custo_percentual=variacao_custo,
            variacao_venda_percentual=variacao_venda,
            motivo="conversao_granel",
            referencia=f"Conversao granel #{conversao_id}",
            observacoes=(
                "Preco de venda alterado por escolha explicita no lancamento de "
                f"granel, de R$ {preco_venda_anterior:.2f} para R$ {preco_venda_novo:.2f}."
            ),
            user_id=current_user.id,
            tenant_id=tenant_id,
        )
    )
    return True


def _produto_e_granel(produto: Produto | None) -> bool:
    if not produto:
        return False
    return (
        bool(getattr(produto, "e_granel", False))
        or "granel" in str(produto.nome or "").lower()
    )


def _normalizar_produto_granel(produto_granel: Produto) -> None:
    produto_granel.e_granel = True
    produto_granel.unidade = "KG"
    if produto_granel.tipo_produto == "KIT":
        produto_granel.tipo_produto = "SIMPLES"
    produto_granel.tipo_kit = None


def _validar_produto_origem_granel(produto_origem: Produto | None) -> float:
    if not produto_origem:
        raise HTTPException(status_code=404, detail="Produto de origem nao encontrado")
    if _produto_e_granel(produto_origem):
        raise HTTPException(
            status_code=400, detail="Produto de origem nao pode ser outro granel"
        )
    if produto_origem.tipo_produto == "PAI":
        raise HTTPException(
            status_code=400,
            detail="Este item e um agrupador de variacoes e nao possui estoque para fracionar",
        )

    peso_pacote_kg = float(produto_origem.peso_embalagem or 0)
    if peso_pacote_kg <= 0:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Produto '{produto_origem.nome}' nao tem peso_embalagem em kg. "
                "Preencha a aba Racao antes de lancar no granel."
            ),
        )
    return peso_pacote_kg


def _serializar_vinculo_granel(vinculo: ProdutoGranelVinculo) -> dict:
    origem = vinculo.produto_origem
    granel = vinculo.produto_granel
    peso = float(getattr(origem, "peso_embalagem", 0) or 0)
    custo_pacote = float(getattr(origem, "preco_custo", 0) or 0)
    return {
        "id": vinculo.id,
        "ativo": bool(vinculo.ativo),
        "produto_origem_id": vinculo.produto_origem_id,
        "produto_origem_nome": getattr(origem, "nome", None),
        "produto_origem_codigo": getattr(origem, "codigo", None),
        "produto_origem_estoque": float(getattr(origem, "estoque_atual", 0) or 0),
        "produto_origem_preco_venda": float(getattr(origem, "preco_venda", 0) or 0),
        "peso_por_unidade_kg": peso,
        "custo_por_unidade": custo_pacote,
        "custo_por_kg": custo_pacote / peso if peso > 0 else 0,
        "produto_granel_id": vinculo.produto_granel_id,
        "produto_granel_nome": getattr(granel, "nome", None),
        "produto_granel_codigo": getattr(granel, "codigo", None),
        "produto_granel_estoque": float(getattr(granel, "estoque_atual", 0) or 0),
        "produto_granel_preco_venda": float(getattr(granel, "preco_venda", 0) or 0),
        "observacao": vinculo.observacao,
        "created_at": vinculo.created_at,
        "updated_at": vinculo.updated_at,
    }


def _obter_ou_criar_vinculo_granel(
    db: Session,
    tenant_id,
    current_user,
    produto_origem: Produto,
    produto_granel: Produto,
    observacao: str | None = None,
) -> ProdutoGranelVinculo:
    if produto_origem.id == produto_granel.id:
        raise HTTPException(
            status_code=400, detail="Produto de origem e granel nao podem ser o mesmo"
        )

    vinculo = (
        db.query(ProdutoGranelVinculo)
        .filter(
            ProdutoGranelVinculo.tenant_id == tenant_id,
            ProdutoGranelVinculo.produto_origem_id == produto_origem.id,
            ProdutoGranelVinculo.produto_granel_id == produto_granel.id,
        )
        .first()
    )

    if vinculo:
        vinculo.ativo = True
        if observacao is not None:
            vinculo.observacao = observacao
        vinculo.updated_at = datetime.utcnow()
        return vinculo

    vinculo = ProdutoGranelVinculo(
        produto_origem_id=produto_origem.id,
        produto_granel_id=produto_granel.id,
        ativo=True,
        observacao=observacao,
        user_id=getattr(current_user, "id", None),
        tenant_id=tenant_id,
    )
    db.add(vinculo)
    db.flush()
    return vinculo


def _resolver_origem_por_payload_granel(
    db: Session, tenant_id, payload: Any
) -> Produto:
    if payload.produto_origem_id:
        produto_origem = (
            db.query(Produto)
            .filter(
                Produto.id == payload.produto_origem_id,
                Produto.tenant_id == tenant_id,
            )
            .first()
        )
        _validar_produto_origem_granel(produto_origem)
        return produto_origem

    vinculos = (
        db.query(ProdutoGranelVinculo)
        .filter(
            ProdutoGranelVinculo.tenant_id == tenant_id,
            ProdutoGranelVinculo.produto_granel_id == payload.produto_granel_id,
            ProdutoGranelVinculo.ativo.is_(True),
        )
        .all()
    )
    if len(vinculos) != 1:
        raise HTTPException(
            status_code=400,
            detail="Informe o produto de origem para lancar no granel.",
        )
    produto_origem = vinculos[0].produto_origem
    _validar_produto_origem_granel(produto_origem)
    return produto_origem


def _produto_corresponde_barcode_granel(produto: Produto, barcode: str | None) -> bool:
    codigo = str(barcode or "").strip()
    if not codigo:
        return False
    candidatos = {
        str(getattr(produto, campo, "") or "").strip()
        for campo in ("codigo", "codigo_barras", "gtin_ean", "gtin_ean_tributario")
    }
    alternativos = getattr(produto, "codigos_barras_alternativos", None)
    if isinstance(alternativos, str) and alternativos.strip():
        try:
            alternativos = json.loads(alternativos)
        except (TypeError, ValueError):
            alternativos = [item.strip() for item in alternativos.split(",")]
    if isinstance(alternativos, (list, tuple, set)):
        candidatos.update(str(item or "").strip() for item in alternativos)
    return codigo in candidatos


def executar_conversao_granel(
    db: Session,
    tenant_id,
    current_user,
    payload: Any,
    exigir_bipagem: bool = False,
) -> dict:
    """Executa a conversao compartilhada pelo ERP e pelo app do funcionario."""

    produto_base = _resolver_origem_por_payload_granel(db, tenant_id, payload)
    produto_granel = (
        db.query(Produto)
        .filter(
            Produto.id == payload.produto_granel_id,
            Produto.tenant_id == tenant_id,
        )
        .first()
    )
    if not produto_granel:
        raise HTTPException(status_code=404, detail="Produto a granel nao encontrado")
    if not _produto_e_granel(produto_granel):
        raise HTTPException(
            status_code=400, detail="Produto informado nao esta marcado como granel"
        )

    if exigir_bipagem:
        if not _produto_corresponde_barcode_granel(
            produto_base, getattr(payload, "produto_origem_barcode", None)
        ):
            raise HTTPException(
                status_code=400,
                detail="O codigo bipado nao corresponde ao produto fechado selecionado.",
            )
        if not _produto_corresponde_barcode_granel(
            produto_granel, getattr(payload, "produto_granel_barcode", None)
        ):
            raise HTTPException(
                status_code=400,
                detail="O produto a granel nao corresponde ao produto bipado.",
            )

    vinculo_existente = (
        db.query(ProdutoGranelVinculo)
        .filter(
            ProdutoGranelVinculo.tenant_id == tenant_id,
            ProdutoGranelVinculo.produto_origem_id == produto_base.id,
            ProdutoGranelVinculo.produto_granel_id == produto_granel.id,
            ProdutoGranelVinculo.ativo.is_(True),
        )
        .first()
    )
    if exigir_bipagem and not vinculo_existente:
        raise HTTPException(
            status_code=400,
            detail="O produto a granel nao corresponde ao produto fechado selecionado.",
        )

    peso_pacote_kg = _validar_produto_origem_granel(produto_base)
    _normalizar_produto_granel(produto_granel)
    vinculo = vinculo_existente or _obter_ou_criar_vinculo_granel(
        db,
        tenant_id,
        current_user,
        produto_base,
        produto_granel,
        None,
    )

    quantidade_pacotes = float(payload.quantidade_pacotes or 0)
    estoque_base_anterior = float(produto_base.estoque_atual or 0)
    if estoque_base_anterior < quantidade_pacotes:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Estoque insuficiente do produto base '{produto_base.nome}'. "
                f"Disponivel: {estoque_base_anterior}, solicitado: {quantidade_pacotes} pacote(s)."
            ),
        )

    quantidade_kg = quantidade_pacotes * peso_pacote_kg
    estoque_granel_anterior = float(produto_granel.estoque_atual or 0)
    custo_pacote = float(produto_base.preco_custo or 0)
    custo_kg = custo_pacote / peso_pacote_kg if peso_pacote_kg > 0 else 0
    custo_granel_anterior = float(produto_granel.preco_custo or 0)
    preco_venda_granel_anterior = float(produto_granel.preco_venda or 0)
    deve_atualizar_preco_venda_granel = bool(
        getattr(payload, "atualizar_preco_venda_granel", False)
        and getattr(payload, "preco_venda_granel", None) is not None
    )
    preco_venda_granel_atualizado = False

    produto_base.estoque_atual = estoque_base_anterior - quantidade_pacotes
    produto_granel.estoque_atual = estoque_granel_anterior + quantidade_kg
    if produto_granel.estoque_atual > 0:
        produto_granel.preco_custo = (
            (estoque_granel_anterior * custo_granel_anterior)
            + (quantidade_kg * custo_kg)
        ) / produto_granel.estoque_atual
    documento = getattr(payload, "documento", None)
    observacao = getattr(payload, "observacao", None)
    conversao = GranelConversao(
        produto_granel_id=produto_granel.id,
        produto_origem_id=produto_base.id,
        quantidade_origem=quantidade_pacotes,
        peso_por_unidade_kg=peso_pacote_kg,
        quantidade_granel_kg=quantidade_kg,
        estoque_origem_anterior=estoque_base_anterior,
        estoque_origem_novo=produto_base.estoque_atual,
        estoque_granel_anterior=estoque_granel_anterior,
        estoque_granel_novo=produto_granel.estoque_atual,
        documento=documento,
        observacao=observacao,
        user_id=current_user.id,
        tenant_id=tenant_id,
    )
    db.add(conversao)
    db.flush()

    if deve_atualizar_preco_venda_granel:
        preco_venda_granel_atualizado = _alterar_preco_venda_granel_com_historico(
            db=db,
            tenant_id=tenant_id,
            current_user=current_user,
            produto_granel=produto_granel,
            preco_venda_anterior=preco_venda_granel_anterior,
            preco_custo_anterior=custo_granel_anterior,
            preco_venda_novo=float(payload.preco_venda_granel),
            conversao_id=conversao.id,
        )

    mov_saida_base = EstoqueMovimentacao(
        produto_id=produto_base.id,
        tipo="saida",
        motivo="conversao_granel",
        quantidade=quantidade_pacotes,
        quantidade_anterior=estoque_base_anterior,
        quantidade_nova=produto_base.estoque_atual,
        custo_unitario=custo_pacote,
        valor_total=quantidade_pacotes * custo_pacote,
        documento=documento,
        referencia_id=conversao.id,
        referencia_tipo="conversao_granel",
        observacao=f"Conversao para granel '{produto_granel.nome}' ({quantidade_kg:.3f} kg)",
        user_id=current_user.id,
        tenant_id=tenant_id,
    )
    mov_entrada_granel = EstoqueMovimentacao(
        produto_id=produto_granel.id,
        tipo="entrada",
        motivo="conversao_granel",
        quantidade=quantidade_kg,
        quantidade_anterior=estoque_granel_anterior,
        quantidade_nova=produto_granel.estoque_atual,
        custo_unitario=custo_kg,
        valor_total=quantidade_kg * custo_kg,
        documento=documento,
        referencia_id=conversao.id,
        referencia_tipo="conversao_granel",
        observacao=observacao
        or f"Entrada granel a partir de {quantidade_pacotes:g} pacote(s) de '{produto_base.nome}'",
        user_id=current_user.id,
        tenant_id=tenant_id,
    )
    db.add(mov_saida_base)
    db.add(mov_entrada_granel)
    db.commit()

    try:
        from app.bling_estoque_sync import sincronizar_bling_background

        sincronizar_bling_background(
            produto_base.id, produto_base.estoque_atual, "conversao_granel_saida"
        )
        sincronizar_bling_background(
            produto_granel.id,
            produto_granel.estoque_atual,
            "conversao_granel_entrada",
        )
    except Exception as exc:
        logger.warning("[BLING-SYNC] Erro ao agendar sync (conversao granel): %s", exc)

    return {
        "id": conversao.id,
        "produto_granel_id": produto_granel.id,
        "produto_granel_nome": produto_granel.nome,
        "produto_origem_id": produto_base.id,
        "produto_origem_nome": produto_base.nome,
        "vinculo_id": vinculo.id,
        "quantidade_pacotes": quantidade_pacotes,
        "peso_por_unidade_kg": peso_pacote_kg,
        "quantidade_granel_kg": quantidade_kg,
        "custo_por_kg": custo_kg,
        "preco_venda_granel_anterior": preco_venda_granel_anterior,
        "preco_venda_granel_novo": float(produto_granel.preco_venda or 0),
        "preco_venda_granel_atualizado": preco_venda_granel_atualizado,
        "estoque_origem_anterior": estoque_base_anterior,
        "estoque_origem_novo": float(produto_base.estoque_atual or 0),
        "estoque_granel_anterior": estoque_granel_anterior,
        "estoque_granel_novo": float(produto_granel.estoque_atual or 0),
        "movimentacoes": {
            "saida_origem_id": mov_saida_base.id,
            "entrada_granel_id": mov_entrada_granel.id,
        },
    }
