"""Contratos de entrada do registro rápido de não venda."""

from decimal import Decimal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.nao_venda_constants import MOTIVOS_NAO_VENDA


class NaoVendaItemCreate(BaseModel):
    produto_id: int | None = Field(default=None, gt=0)
    produto_nome: str | None = Field(default=None, max_length=200)
    sku: str | None = Field(default=None, max_length=50)
    marca_id: int | None = Field(default=None, gt=0)
    marca_nome: str | None = Field(default=None, max_length=100)
    fornecedor_id: int | None = Field(default=None, gt=0)
    fornecedor_nome: str | None = Field(default=None, max_length=255)
    quantidade: Decimal = Field(default=Decimal("1"), gt=0, le=1_000_000)
    valor_unitario_estimado: Decimal | None = Field(
        default=None, ge=0, le=1_000_000_000
    )

    @field_validator(
        "produto_nome",
        "sku",
        "marca_nome",
        "fornecedor_nome",
        mode="before",
    )
    @classmethod
    def limpar_texto(cls, valor):
        if valor is None:
            return None
        texto = str(valor).strip()
        return texto or None

    @model_validator(mode="after")
    def exigir_produto(self):
        if not self.produto_id and not self.produto_nome:
            raise ValueError("Informe ou selecione o produto procurado")
        return self


class NaoVendaCreate(BaseModel):
    cliente_id: int | None = Field(default=None, gt=0)
    cliente_nome: str | None = Field(default=None, max_length=255)
    cliente_telefone: str | None = Field(default=None, max_length=50)
    motivo: str = Field(max_length=40)
    observacoes: str | None = Field(default=None, max_length=2000)
    itens: list[NaoVendaItemCreate] = Field(default_factory=list, max_length=20)
    adicionar_lista_espera: bool = False

    @field_validator("cliente_nome", "cliente_telefone", "observacoes", mode="before")
    @classmethod
    def limpar_texto(cls, valor):
        if valor is None:
            return None
        texto = str(valor).strip()
        return texto or None

    @field_validator("motivo")
    @classmethod
    def validar_motivo(cls, valor: str) -> str:
        if valor not in MOTIVOS_NAO_VENDA:
            raise ValueError("Motivo de não venda inválido")
        return valor
