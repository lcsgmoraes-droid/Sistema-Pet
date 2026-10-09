"""Identificação dos lotes que compõem o estoque já existente."""

import time
from datetime import date, datetime, time as hora

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.produtos.schemas import LoteResponse
from app.produtos.validators import (
    _resolver_tenant_produto_catalogo,
    _validar_tenant_e_obter_usuario,
)
from app.produtos_models import Produto, ProdutoLote

router = APIRouter()


class LoteValidadeRequest(BaseModel):
    lote_id: int | None = None
    nome_lote: str = Field(min_length=1, max_length=50)
    quantidade: float = Field(ge=0, allow_inf_nan=False)
    data_validade: date
    data_fabricacao: date | None = None

    @field_validator("nome_lote")
    @classmethod
    def validar_nome(cls, valor):
        valor = valor.strip()
        if not valor:
            raise ValueError("Informe o número do lote")
        return valor


@router.put("/{produto_id}/lotes-validade", response_model=LoteResponse)
def informar_lote_validade(
    produto_id: int,
    dados: LoteValidadeRequest,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Define a quantidade do lote, sem entrada, saída ou ajuste do saldo."""
    _, tenant_solicitante_id = _validar_tenant_e_obter_usuario(user_and_tenant)
    tenant_id, _ = _resolver_tenant_produto_catalogo(
        db, tenant_solicitante_id, produto_id
    )
    # O lock serializa cadastros concorrentes de lotes do produto.
    produto = (
        db.query(Produto)
        .filter(Produto.id == produto_id, Produto.tenant_id == tenant_id)
        .with_for_update()
        .first()
    )
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    if (
        not getattr(produto, "controlar_estoque", True)
        or produto.is_parent
        or (produto.tipo_produto == "KIT" and produto.tipo_kit == "VIRTUAL")
    ):
        raise HTTPException(
            status_code=400,
            detail="Este cadastro não possui estoque próprio para identificar lotes",
        )
    if dados.data_fabricacao and dados.data_fabricacao > dados.data_validade:
        raise HTTPException(
            status_code=400, detail="A fabricação não pode ser posterior à validade"
        )

    lotes = (
        db.query(ProdutoLote)
        .filter(
            ProdutoLote.produto_id == produto_id,
            ProdutoLote.tenant_id == tenant_id,
            ProdutoLote.status != "excluido",
        )
        .with_for_update()
        .all()
    )
    lote = (
        next((item for item in lotes if item.id == dados.lote_id), None)
        if dados.lote_id
        else None
    )
    if dados.lote_id and lote is None:
        raise HTTPException(
            status_code=404, detail="Lote não encontrado para este produto"
        )
    mesmo_nome = next(
        (item for item in lotes if item.nome_lote == dados.nome_lote), None
    )
    if lote and mesmo_nome and mesmo_nome.id != lote.id:
        raise HTTPException(
            status_code=400, detail="Já existe outro lote com este número"
        )
    # Reenviar o mesmo número define sua quantidade; nunca soma outra vez.
    lote = lote or mesmo_nome
    if not lote and dados.quantidade <= 0:
        raise HTTPException(
            status_code=400,
            detail="Informe uma quantidade maior que zero para o novo lote",
        )
    if lote and dados.quantidade < float(lote.quantidade_reservada or 0):
        raise HTTPException(
            status_code=400,
            detail="A quantidade não pode ser menor que a reserva deste lote",
        )

    quantidade_outros = sum(
        max(0, float(item.quantidade_disponivel or 0))
        for item in lotes
        if item is not lote
    )
    total_identificado = quantidade_outros + dados.quantidade
    estoque_atual = max(0, float(produto.estoque_atual or 0))
    # Permite corrigir para baixo um cadastro antigo que já excedia o estoque.
    total_anterior = quantidade_outros + (
        float(lote.quantidade_disponivel or 0) if lote else 0
    )
    if (
        total_identificado > estoque_atual + 1e-6
        and total_identificado > total_anterior + 1e-6
    ):
        raise HTTPException(
            status_code=400,
            detail="As quantidades dos lotes excedem o estoque atual. Corrija os lotes existentes ou registre a entrada de estoque primeiro.",
        )

    if lote is None:
        lote = ProdutoLote(
            produto_id=produto_id,
            tenant_id=tenant_id,
            quantidade_inicial=dados.quantidade,
            quantidade_reservada=0,
            ordem_entrada=int(time.time()),
            # Identificação não cria um custo de entrada. Consumos usam o cadastro.
            custo_unitario=None,
            apenas_identificacao=True,
            status="ativo",
        )
        db.add(lote)
    else:
        quantidade_consumida = max(
            0,
            float(lote.quantidade_inicial or 0)
            - float(lote.quantidade_disponivel or 0),
        )
        lote.quantidade_inicial = quantidade_consumida + dados.quantidade

    lote.nome_lote = dados.nome_lote
    lote.quantidade_disponivel = dados.quantidade
    lote.data_validade = datetime.combine(dados.data_validade, hora.min)
    lote.data_fabricacao = (
        datetime.combine(dados.data_fabricacao, hora.min)
        if dados.data_fabricacao
        else None
    )
    # Uma correção de identificação não deve liberar um lote bloqueado/vencido.
    if lote.status in ("ativo", "esgotado"):
        lote.status = "ativo" if dados.quantidade > 0 else "esgotado"
    db.commit()
    db.refresh(lote)
    return lote
