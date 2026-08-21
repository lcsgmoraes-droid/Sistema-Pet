"""
Schemas Pydantic para ConfiguracaoEntrega
Sprint 1 - Módulo de Entregas
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field, model_validator
from uuid import UUID


class FaixaDistanciaFrete(BaseModel):
    """Preco fechado para uma rota de ate determinada distancia."""

    ate_km: float = Field(gt=0)
    valor: float = Field(ge=0)


class ConfiguracaoEntregaBase(BaseModel):
    """Campos base da configuração de entrega"""

    entregador_padrao_id: Optional[int] = None
    # Endereço completo do ponto inicial
    logradouro: Optional[str] = None
    cep: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    # Método de registro de KM ao marcar entrega
    # Valores: "auto_rota" | "gps" | "manual"
    metodo_km_entrega: Optional[str] = "auto_rota"
    entrega_ativa: bool = True
    retirada_ativa: bool = True
    modalidade_cobranca: Literal["fixa", "por_km", "por_faixa"] = "fixa"
    taxa_fixa: float = Field(default=0, ge=0)
    valor_por_km_cobrado: Optional[float] = Field(default=None, ge=0)
    taxa_minima: float = Field(default=0, ge=0)
    faixas_distancia: list[FaixaDistanciaFrete] = Field(
        default_factory=list, max_length=50
    )
    valor_km_excedente: Optional[float] = Field(default=None, ge=0)
    distancia_maxima_entrega_km: Optional[float] = Field(default=None, gt=0)
    frete_gratis_acima: Optional[float] = Field(default=None, gt=0)
    distancia_maxima_frete_gratis_km: Optional[float] = Field(default=None, gt=0)
    pedido_minimo: float = Field(default=0, ge=0)
    prazo_entrega_texto: Optional[str] = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def validar_cobranca_por_km(self):
        if self.modalidade_cobranca == "por_km" and not self.valor_por_km_cobrado:
            raise ValueError("Informe um valor por km maior que zero")
        if self.modalidade_cobranca == "por_faixa":
            if not self.faixas_distancia:
                raise ValueError("Cadastre ao menos uma faixa de distancia")
            limites = [faixa.ate_km for faixa in self.faixas_distancia]
            if limites != sorted(set(limites)):
                raise ValueError(
                    "As faixas de distancia devem estar em ordem crescente e sem repeticao"
                )
        return self


class ConfiguracaoEntregaUpdate(ConfiguracaoEntregaBase):
    """Schema para atualização de configuração"""

    pass


class ConfiguracaoEntregaResponse(ConfiguracaoEntregaBase):
    """Schema de resposta da configuração"""

    id: int
    tenant_id: UUID

    class Config:
        from_attributes = True  # Pydantic v2
