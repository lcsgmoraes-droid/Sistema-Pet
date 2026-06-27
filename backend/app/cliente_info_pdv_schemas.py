"""Schemas compartilhados pelos endpoints de apoio ao PDV do cliente."""

from typing import List, Optional

from pydantic import BaseModel


class ItemCarrinhoIA(BaseModel):
    produto_id: Optional[int] = None
    produto_nome: str
    quantidade: float
    preco_unitario: float


class AlertasCarrinhoRequest(BaseModel):
    itens: List[ItemCarrinhoIA]


class ChatPDVRequest(BaseModel):
    mensagem: str
    carrinho: Optional[List[ItemCarrinhoIA]] = None
