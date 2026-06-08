"""Schemas Pydantic usados pelas rotas de notas de entrada."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class NotaEntradaResponse(BaseModel):
    id: int
    numero_nota: str
    serie: str
    chave_acesso: str
    fornecedor_nome: str
    fornecedor_cnpj: str
    fornecedor_id: Optional[int] = None
    data_emissao: datetime
    valor_total: float
    status: str
    produtos_vinculados: Optional[int] = 0
    produtos_nao_vinculados: Optional[int] = 0
    entrada_estoque_realizada: Optional[bool] = False
    conferencia_status: Optional[str] = "nao_iniciada"
    divergencias_count: Optional[int] = 0

    model_config = {"from_attributes": True}


class ConferenciaItemPayload(BaseModel):
    item_id: int
    quantidade_conferida: float
    quantidade_avariada: float = 0
    observacao_conferencia: Optional[str] = None
    acao_sugerida: Optional[str] = "sem_acao"


class ConferenciaNotaPayload(BaseModel):
    itens: List[ConferenciaItemPayload]
    observacao_geral: Optional[str] = None


class RateioNotaRequest(BaseModel):
    tipo_rateio: str


class RateioItemRequest(BaseModel):
    quantidade_online: float


class AtualizarPrecoRequest(BaseModel):
    produto_id: int
    preco_venda: float


class ProcessarConfig(BaseModel):
    multiplicadores_override: dict = Field(default_factory=dict)
    custos_override: dict = Field(default_factory=dict)


class CriarProdutoRequest(BaseModel):
    sku: str
    nome: str
    descricao: Optional[str] = None
    preco_custo: float
    preco_venda: float
    margem_lucro: Optional[float] = None
    categoria_id: Optional[int] = None
    marca_id: Optional[int] = None
    estoque_minimo: Optional[int] = 10
    estoque_maximo: Optional[int] = 100
