"""Schemas publicos da calculadora de racao."""

from typing import Any, List, Optional

from pydantic import BaseModel, Field


# ==================== SCHEMAS ====================


class CalculadoraRacaoRequest(BaseModel):
    """Request para calcular duração de ração"""

    produto_id: Optional[int] = None  # ID do produto (ração)
    peso_embalagem_kg: Optional[float] = (
        None  # Se não tiver produto_id, passar manualmente
    )
    preco: Optional[float] = None  # Preço manual

    # Dados do pet
    peso_pet_kg: float  # Peso do pet em kg
    idade_meses: Optional[int] = None  # Idade em meses (para ajustar quantidade)
    nivel_atividade: str = "normal"  # baixo, normal, alto

    # Opcional: usar tabela da embalagem ou quantidade personalizada
    quantidade_diaria_g: Optional[float] = (
        None  # Se já souber a quantidade, passar aqui
    )


class ResultadoCalculoRacao(BaseModel):
    """Resultado do cálculo"""

    # Dados do produto
    produto_id: Optional[int] = None
    produto_nome: Optional[str] = None
    classificacao: Optional[str] = None
    categoria_racao: Optional[str] = None  # filhote, adulto, senior
    peso_embalagem_kg: float
    preco: float

    # Resultados do cálculo
    quantidade_diaria_g: float  # Gramas por dia
    duracao_dias: float  # Quantos dias vai durar
    duracao_meses: float  # Quantos meses vai durar
    custo_por_kg: float  # R$ por kg
    custo_por_dia: float  # R$ por dia
    custo_mensal: float  # R$ por mês

    # Meta-info
    pet_peso_kg: float
    pet_nivel_atividade: str


class ComparativoRacoesResponse(BaseModel):
    """Comparativo entre múltiplas rações"""

    racoes: List[ResultadoCalculoRacao]
    melhor_custo_beneficio: Optional[int] = None  # produto_id
    maior_duracao: Optional[int] = None  # produto_id
    menor_custo_diario: Optional[int] = None  # produto_id


class RacaoCalculadoraOption(BaseModel):
    id: int
    nome: str
    codigo: Optional[str] = None
    sku: Optional[str] = None
    codigo_barras: Optional[str] = None
    categoria_nome: Optional[str] = None
    marca_nome: Optional[str] = None
    tipo: Optional[str] = None
    eh_racao: bool = True
    classificacao_racao: Optional[str] = None
    categoria_racao: Optional[str] = None
    especies_indicadas: Optional[str] = None
    peso_embalagem: Optional[float] = None
    preco_venda: Optional[float] = None
    linha_racao_id: Optional[int] = None
    porte_animal_id: Optional[int] = None
    fase_publico_id: Optional[int] = None
    tipo_tratamento_id: Optional[int] = None
    sabor_proteina_id: Optional[int] = None
    apresentacao_peso_id: Optional[int] = None
    porte_animal: Optional[Any] = None
    fase_publico: Optional[Any] = None
    tipo_tratamento: Optional[Any] = None
    sabor_proteina: Optional[str] = None
    tabela_consumo: Optional[str] = None
    tabela_nutricional: Optional[str] = None
    apta: bool = False
    faltantes: List[str] = Field(default_factory=list)


class RacoesCalculadoraOptionsResponse(BaseModel):
    items: List[RacaoCalculadoraOption]
    total: int
    page: int
    page_size: int
    aptas: int
    incompletas: int
