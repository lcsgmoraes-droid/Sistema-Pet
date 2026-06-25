"""Schemas do PDV do funcionario no App Mobile."""

from typing import Optional

from pydantic import BaseModel, Field


class FuncionarioPdvProdutoResponse(BaseModel):
    id: int
    nome: str
    codigo: Optional[str] = None
    codigo_barras: Optional[str] = None
    unidade: str = "UN"
    preco_venda: float = 0
    estoque_atual: float = 0
    imagem_url: Optional[str] = None
    tipo_produto: Optional[str] = None
    tipo_kit: Optional[str] = None
    vendavel: bool = True
    aviso: Optional[str] = None


class FuncionarioPdvClienteResponse(BaseModel):
    id: int
    codigo: Optional[str] = None
    nome: str
    telefone: Optional[str] = None
    celular: Optional[str] = None
    documento: Optional[str] = None
    tipo_cadastro: Optional[str] = None
    email: Optional[str] = None
    endereco: Optional[str] = None
    credito: float = 0
    fidelidade: Optional[dict] = None
    cupons_disponiveis: list[dict] = Field(default_factory=list)


class FuncionarioPdvCaixaResponse(BaseModel):
    aberto: bool
    caixa_id: Optional[int] = None
    numero_caixa: Optional[int] = None
    mensagem: str


class FuncionarioPdvItemRequest(BaseModel):
    produto_id: int
    quantidade: float = Field(gt=0)
    preco_unitario: float = Field(ge=0)


class FuncionarioPdvPagamentoRequest(BaseModel):
    forma_pagamento: str
    valor: float = Field(ge=0)
    valor_recebido: Optional[float] = None
    troco: Optional[float] = None
    numero_parcelas: int = Field(default=1, ge=1)
    forma_pagamento_id: Optional[int] = None
    bandeira: Optional[str] = None
    operadora: Optional[str] = None
    nsu_cartao: Optional[str] = None


class FuncionarioPdvFinalizarRequest(BaseModel):
    cliente_id: Optional[int] = None
    itens: list[FuncionarioPdvItemRequest]
    pagamento: FuncionarioPdvPagamentoRequest
    observacoes: Optional[str] = None
    cupom_codigo: Optional[str] = None
    desconto_cupom: Optional[float] = Field(default=0, ge=0)
    cashback_valor: Optional[float] = Field(default=0, ge=0)


class FuncionarioPdvSalvarRequest(BaseModel):
    cliente_id: Optional[int] = None
    itens: list[FuncionarioPdvItemRequest]
    observacoes: Optional[str] = None
    cupom_codigo: Optional[str] = None
    desconto_cupom: Optional[float] = Field(default=0, ge=0)
    cashback_valor: Optional[float] = Field(default=0, ge=0)


class FuncionarioPdvFormaPagamentoResponse(BaseModel):
    id: int
    nome: str
    tipo: str
    key: str
    taxa_percentual: float = 0
    permite_parcelamento: bool = False
    numero_parcelas: int = 1
    max_parcelas: int = 1
    parcelas_maximas: int = 1
    operadora: Optional[str] = None
    requer_nsu: bool = False
    tipo_cartao: Optional[str] = None
    bandeira: Optional[str] = None
    split_parcelas: bool = False


class FuncionarioPdvBeneficioCupomResponse(BaseModel):
    code: str
    coupon_type: str
    discount_value: Optional[float] = None
    discount_percent: Optional[float] = None
    discount_applied: float = 0
    min_purchase_value: Optional[float] = None
    valid_until: Optional[str] = None


class FuncionarioPdvBeneficiosPreviewRequest(BaseModel):
    cliente_id: Optional[int] = None
    itens: list[FuncionarioPdvItemRequest]
    cupom_codigo: Optional[str] = None
    cashback_valor: Optional[float] = Field(default=0, ge=0)


class FuncionarioPdvBeneficiosPreviewResponse(BaseModel):
    subtotal: float
    desconto_cupom: float
    cupom_code: Optional[str] = None
    cashback_disponivel: float
    cashback_valor: float
    total_venda: float
    valor_pagamento: float
    cupons_disponiveis: list[FuncionarioPdvBeneficioCupomResponse] = Field(
        default_factory=list
    )
    beneficios_gerados: list[dict] = Field(default_factory=list)
    mensagens: list[str] = Field(default_factory=list)


class FuncionarioPdvFinalizarResponse(BaseModel):
    status: str
    venda_id: int
    numero_venda: str
    total: float
    total_pago: float
    forma_pagamento: str
    mensagem: str


class FuncionarioPdvSalvarResponse(BaseModel):
    status: str
    venda_id: int
    numero_venda: str
    total: float
    mensagem: str


# ─────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────
