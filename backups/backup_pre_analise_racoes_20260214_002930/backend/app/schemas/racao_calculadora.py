"""
Schemas Pydantic para Calculadora de Ração
===========================================
Validação de entrada e saída para cálculos de consumo de ração.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional


class RacaoCalculadoraInput(BaseModel):
    """
    Schema de entrada para cálculo de consumo de ração.
    
    Validações:
    - Pesos devem ser maiores que zero
    - Preço não pode ser negativo
    - Enums restritos aos valores permitidos
    """
    
    # NOVO: Produto opcional (se fornecido, busca dados do produto)
    produto_id: Optional[int] = Field(
        None,
        description="ID do produto (ração). Se fornecido, dados da ração são buscados do cadastro"
    )
    
    especie: Literal["cao", "gato"] = Field(
        ...,
        description="Espécie do animal"
    )
    
    peso_kg: float = Field(
        ...,
        gt=0,
        description="Peso do animal em kg (deve ser maior que 0)"
    )
    
    idade_meses: Optional[int] = Field(
        None,
        description="Idade do animal em meses (obrigatório para filhotes com tabela de consumo)"
    )
    
    fase: Literal["filhote", "adulto", "idoso"] = Field(
        ...,
        description="Fase de vida do animal"
    )
    
    porte: Literal["mini", "pequeno", "medio", "grande"] = Field(
        ...,
        description="Porte do animal"
    )
    
    tipo_racao: Literal["standard", "premium", "super_premium"] = Field(
        ...,
        description="Tipo/qualidade da ração"
    )
    
    peso_pacote_kg: Optional[float] = Field(
        None,
        gt=0,
        description="Peso do pacote de ração em kg. Opcional se produto_id fornecido"
    )
    
    preco_pacote: Optional[float] = Field(
        None,
        ge=0,
        description="Preço do pacote de ração. Opcional se produto_id fornecido"
    )
    
    @field_validator('peso_kg')
    @classmethod
    def validar_peso_animal(cls, v: float) -> float:
        """Valida se o peso do animal está dentro de limites razoáveis"""
        if v > 100:
            raise ValueError("Peso do animal parece muito alto (máximo 100kg)")
        return v
    
    @field_validator('peso_pacote_kg')
    @classmethod
    def validar_peso_pacote(cls, v: float) -> float:
        """Valida se o peso do pacote está dentro de limites razoáveis"""
        if v > 50:
            raise ValueError("Peso do pacote parece muito alto (máximo 50kg)")
        return v
    
    @field_validator('preco_pacote')
    @classmethod
    def validar_preco(cls, v: float) -> float:
        """Valida se o preço não é absurdamente alto"""
        if v > 10000:
            raise ValueError("Preço do pacote parece muito alto (máximo R$ 10.000)")
        return v


class RacaoCalculadoraOutput(BaseModel):
    """
    Schema de saída com resultados dos cálculos de ração.
    
    Inclui:
    - Consumo diário e durabilidade do pacote
    - Custos diário e mensal
    - Observações e recomendações
    - Contexto preparado para futura integração com IA
    """
    
    consumo_diario_gramas: float = Field(
        ...,
        description="Quantidade diária de ração em gramas"
    )
    
    duracao_pacote_dias: float = Field(
        ...,
        description="Quantos dias o pacote vai durar"
    )
    
    custo_diario: float = Field(
        ...,
        description="Custo diário de alimentação em reais"
    )
    
    custo_mensal: float = Field(
        ...,
        description="Custo mensal estimado em reais (30 dias)"
    )
    
    observacoes: str = Field(
        ...,
        description="Observações e recomendações sobre o cálculo"
    )
    
    # Preparado para futura integração com IA
    contexto_ia: dict = Field(
        default_factory=dict,
        description="Contexto estruturado para futura integração com IA"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "consumo_diario_gramas": 150.0,
                "duracao_pacote_dias": 33.33,
                "custo_diario": 1.50,
                "custo_mensal": 45.00,
                "observacoes": "Cão de porte médio, adulto. Recomenda-se dividir em 2 refeições.",
                "contexto_ia": {
                    "resumo_textual": "Um cão adulto de 15kg consome 150g/dia de ração premium...",
                    "dados_estruturados": {
                        "peso_kg": 15,
                        "especie": "cao",
                        "consumo_diario_gramas": 150
                    }
                }
            }
        }
