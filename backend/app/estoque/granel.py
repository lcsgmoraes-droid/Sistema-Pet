from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.produtos_models import Produto, ProdutoGranelVinculo


def _produto_e_granel(produto: Produto | None) -> bool:
    if not produto:
        return False
    return bool(getattr(produto, "e_granel", False)) or "granel" in str(produto.nome or "").lower()


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
        raise HTTPException(status_code=400, detail="Produto de origem nao pode ser outro granel")
    if produto_origem.tipo_produto == "PAI":
        raise HTTPException(status_code=400, detail="Produto pai/agrupador nao possui estoque para fracionar")

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
        raise HTTPException(status_code=400, detail="Produto de origem e granel nao podem ser o mesmo")

    vinculo = db.query(ProdutoGranelVinculo).filter(
        ProdutoGranelVinculo.tenant_id == tenant_id,
        ProdutoGranelVinculo.produto_origem_id == produto_origem.id,
        ProdutoGranelVinculo.produto_granel_id == produto_granel.id,
    ).first()

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


def _resolver_origem_por_payload_granel(db: Session, tenant_id, payload: Any) -> Produto:
    if payload.produto_origem_id:
        produto_origem = db.query(Produto).filter(
            Produto.id == payload.produto_origem_id,
            Produto.tenant_id == tenant_id,
        ).first()
        _validar_produto_origem_granel(produto_origem)
        return produto_origem

    vinculos = db.query(ProdutoGranelVinculo).filter(
        ProdutoGranelVinculo.tenant_id == tenant_id,
        ProdutoGranelVinculo.produto_granel_id == payload.produto_granel_id,
        ProdutoGranelVinculo.ativo.is_(True),
    ).all()
    if len(vinculos) != 1:
        raise HTTPException(
            status_code=400,
            detail="Informe o produto de origem para lancar no granel.",
        )
    produto_origem = vinculos[0].produto_origem
    _validar_produto_origem_granel(produto_origem)
    return produto_origem
