"""Schemas das rotas de pedidos de compra."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from .exportacao import PEDIDO_EXPORT_COLUNAS_DEFAULT
from .quantidades import UNIDADE_COMPRA_PADRAO


class PedidoCompraItemRequest(BaseModel):
    """Schema para item do pedido"""

    produto_id: int
    quantidade_pedida: float = Field(gt=0)
    unidade_compra: str = Field(default=UNIDADE_COMPRA_PADRAO, max_length=10)
    quantidade_por_embalagem: float = Field(default=1, gt=0)
    preco_unitario: float = Field(ge=0)
    desconto_item: float = Field(default=0, ge=0)

    # IA (futuro)
    sugestao_ia: bool = False
    motivo_ia: Optional[str] = None


class PedidoCompraRequest(BaseModel):
    """Schema para criar/editar pedido"""

    fornecedor_id: int
    data_prevista_entrega: Optional[datetime] = None
    valor_frete: float = Field(default=0, ge=0)
    valor_desconto: float = Field(default=0, ge=0)
    observacoes: Optional[str] = None
    itens: List[PedidoCompraItemRequest]

    # IA (futuro)
    sugestao_ia: bool = False
    confianca_ia: Optional[float] = None
    dados_ia: Optional[str] = None


class RecebimentoItemRequest(BaseModel):
    """Schema para receber item"""

    item_id: int
    quantidade_recebida: float = Field(gt=0)


class RecebimentoPedidoRequest(BaseModel):
    """Schema para recebimento de pedido"""

    itens: List[RecebimentoItemRequest]
    data_recebimento: Optional[datetime] = None


class PedidoCompraResponse(BaseModel):
    """Schema de resposta do pedido"""

    id: int
    numero_pedido: str
    fornecedor_id: int
    status: str
    valor_total: float
    valor_frete: float
    valor_desconto: float
    valor_final: float
    data_pedido: datetime
    data_prevista_entrega: Optional[datetime]
    observacoes: Optional[str]
    itens_count: int

    model_config = {"from_attributes": True}


class PedidoCompraEnvioFormatos(BaseModel):
    pdf: bool = True
    excel: bool = False


class PedidoCompraEnviarRequest(BaseModel):
    email: Optional[str] = None
    whatsapp: Optional[str] = None
    formatos: PedidoCompraEnvioFormatos = Field(
        default_factory=PedidoCompraEnvioFormatos
    )
    colunas_exportacao: List[str] = Field(
        default_factory=lambda: PEDIDO_EXPORT_COLUNAS_DEFAULT.copy()
    )
    envio_manual: bool = False
